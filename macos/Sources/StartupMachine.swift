import Foundation

enum StartupFailure: Error, CustomStringConvertible {
    case untranslated(Int)
    case modifiedInstruction(Int, UInt8, UInt8)
    case unsupported(String)
    var description: String {
        switch self {
        case .untranslated(let pc): return String(format: "Untranslated startup address $%04X", pc)
        case .modifiedInstruction(let pc, let expected, let actual):
            return String(format: "Instruction changed at $%04X: %02X → %02X", pc, expected, actual)
        case .unsupported(let message): return message
        }
    }
}

// Ghidra-generated Swift blocks retain the original address, operands and flow.
// The host replaces ProDOS file loading; all screen writes come from translated code.
final class StartupMachine {
    var memory = [UInt8](repeating: 0, count: 65536)
    var a: UInt8 = 0, x: UInt8 = 0, y: UInt8 = 0, sp: UInt8 = 0xFB
    var p: UInt8 = 0x24
    var pc: Int = 0x0800
    var page = 0x2000
    var hires = false
    var text = true
    var mixed = false
    var keyboard: UInt8 = 0
    var instructions = 0
    var visited = Set<Int>()
    var soundEdges = 0
    var splashPresented = false
    var introFrames = 0
    var titleReady = false
    var gameRunning = false
    var engineLoaded = false
    var overlay = ""
    var awaitingInput = false
    var captureInputBoundaries = false
    var saves = 0
    var saveDirectory: URL?
    var loaderReturn = 0
    let resources: URL

    init(resources: URL) throws {
        self.resources = resources
        // U1.SYSTEM $21D6 / low-memory handoff: load U1.INTRO at $0800.
        try load("U1.INTRO", at: 0x0800)
    }

    func load(_ name: String, at address: Int) throws {
        let bytes = [UInt8](try Data(contentsOf: resources.appendingPathComponent(name)))
        guard address + bytes.count <= memory.count else {
            throw StartupFailure.unsupported("Resource exceeds memory: \(name)")
        }
        memory.replaceSubrange(address..<(address + bytes.count), with: bytes)
    }

    @inline(__always) func flag(_ mask: UInt8) -> Bool { p & mask != 0 }
    @inline(__always) func setFlag(_ mask: UInt8, _ value: Bool) {
        p = value ? p | mask : p & ~mask
    }
    @inline(__always) func nz(_ value: UInt8) -> UInt8 {
        setFlag(2, value == 0); setFlag(0x80, value & 0x80 != 0)
        return value
    }
    @inline(__always) func read(_ address: Int) -> UInt8 {
        let addr = address & 0xFFFF
        if addr < 0xC000 || addr >= 0xD000 { return memory[addr] }
        switch addr {
        case 0xC000: return keyboard
        case 0xC010: keyboard &= 0x7F
        case 0xC030: soundEdges += 1
        case 0xC050: text = false
        case 0xC051: text = true
        case 0xC052: mixed = false
        case 0xC053: mixed = true
        case 0xC054: page = 0x2000
        case 0xC055: page = 0x4000
        case 0xC056: hires = false
        case 0xC057: hires = true
        default: break // Disk motor reads are inert after native resource loading.
        }
        return 0
    }
    @inline(__always) func write(_ address: Int, _ value: UInt8) {
        let addr = address & 0xFFFF
        if (0xC000..<0xD000).contains(addr) { _ = read(addr) }
        else { memory[addr] = value }
    }
    @inline(__always) func byteOperand() -> UInt8 { memory[(pc + 1) & 0xFFFF] }
    @inline(__always) func wordOperand() -> Int {
        Int(memory[(pc + 1) & 0xFFFF]) | Int(memory[(pc + 2) & 0xFFFF]) << 8
    }
    @inline(__always) func zpWord(_ address: UInt8) -> Int {
        Int(memory[Int(address)]) | Int(memory[Int(address &+ 1)]) << 8
    }
    @inline(__always) func push(_ value: UInt8) {
        memory[0x100 + Int(sp)] = value; sp &-= 1
    }
    @inline(__always) func pop() -> UInt8 {
        sp &+= 1; return memory[0x100 + Int(sp)]
    }
    func pushWord(_ value: Int) {
        push(UInt8(truncatingIfNeeded: value >> 8)); push(UInt8(truncatingIfNeeded: value))
    }
    func popWord() -> Int { let low = Int(pop()); return low | Int(pop()) << 8 }
    func rts() { pc = (popWord() + 1) & 0xFFFF }
    func jsr() { let target = wordOperand(); pushWord(pc + 2); pc = target }
    func branch(_ taken: Bool) {
        let delta = Int(Int8(bitPattern: byteOperand()))
        pc = (pc + 2 + (taken ? delta : 0)) & 0xFFFF
    }
    func compare(_ left: UInt8, _ right: UInt8) {
        setFlag(1, left >= right); _ = nz(left &- right)
    }
    func adc(_ value: UInt8) {
        let old = a
        let carry = flag(1) ? 1 : 0
        let sum = UInt16(a) + UInt16(value) + UInt16(carry)
        setFlag(1, sum > 255)
        let result = UInt8(truncatingIfNeeded: sum)
        setFlag(0x40, (~(old ^ value) & (old ^ result) & 0x80) != 0)
        if flag(8) {
            var low = Int(old & 15) + Int(value & 15) + carry
            var high = Int(old >> 4) + Int(value >> 4)
            if low > 9 { low += 6; high += 1 }
            let intermediate = UInt8(truncatingIfNeeded: high << 4 | low & 15)
            setFlag(0x40, (~(old ^ value) & (old ^ intermediate) & 0x80) != 0)
            if high > 9 { high += 6; setFlag(1, true) }
            a = nz(UInt8(truncatingIfNeeded: high << 4 | low & 15))
        } else { a = nz(result) }
    }
    func sbc(_ value: UInt8) {
        guard flag(8) else { adc(~value); return }
        let old = a, borrow = flag(1) ? 0 : 1
        let difference = Int(old) - Int(value) - borrow
        let binary = UInt8(truncatingIfNeeded: difference)
        setFlag(0x40, ((old ^ value) & (old ^ binary) & 0x80) != 0)
        var adjusted = difference
        if Int(old & 15) < Int(value & 15) + borrow { adjusted -= 6 }
        if difference < 0 { adjusted -= 0x60 }
        setFlag(1, difference >= 0)
        a = nz(UInt8(truncatingIfNeeded: adjusted))
    }
    func bit(_ value: UInt8) {
        setFlag(2, a & value == 0)
        setFlag(0x80, value & 0x80 != 0); setFlag(0x40, value & 0x40 != 0)
    }
    func shift(_ value: UInt8, kind: Int) -> UInt8 {
        let incoming: UInt8 = flag(1) ? 1 : 0
        let result: UInt8
        switch kind {
        case 0: setFlag(1, value & 0x80 != 0); result = value &<< 1 // ASL
        case 1: setFlag(1, value & 1 != 0); result = value >> 1 // LSR
        case 2: setFlag(1, value & 0x80 != 0); result = (value &<< 1) | incoming // ROL
        default: setFlag(1, value & 1 != 0); result = (value >> 1) | (incoming << 7) // ROR
        }
        return nz(result)
    }

    // B70C's inline filename and execute-on-load contract, without ProDOS emulation.
    func hostLoader() throws {
        let argument = popWord() + 1
        var end = argument
        while memory[end] != 0 && end < argument + 32 { end += 1 }
        let name = String(bytes: memory[argument..<end], encoding: .ascii) ?? ""
        guard name == "MAKE.INDATA" else {
            throw StartupFailure.unsupported("Next startup module is \(name)")
        }
        try load(name, at: 0x1E00)
        loaderReturn = end + 1
        pushWord(0xB70E) // Return through the host loader's carry-clear epilogue.
        setFlag(1, false)
        pc = 0x1E00
    }

    // Returns at actual display boundaries. Busy waits are translated into a
    // native scheduler delay while retaining the original register exit state.
    func nextFrame(budget: Int = 8_000_000) throws -> Bool {
        if gameRunning { return try nextGameFrame(budget: budget) }
        for _ in 0..<budget {
            if pc == 0x1F46 && !splashPresented {
                splashPresented = true
                return true
            }
            if pc == 0x1F46 {
                a = nz(0); x = nz(0); setFlag(1, true); setFlag(0x40, false)
                pc = 0x1F5B
            }
            if pc == 0x0E23 {
                a = nz(0); setFlag(1, true); setFlag(0x40, false); rts()
            }
            if pc == 0xB70C { try hostLoader() }
            if pc == 0xB70F {
                setFlag(1, false)
                pc = loaderReturn
            }
            visited.insert(pc)
            instructions += 1
            try translatedStep()
            // $0C69-$0D0B completes the type-4 reveal when $09DF reaches $88.
            if pc == 0x0B23 {
                if memory[0x09DD] == 4 && memory[0x09DF] == 0x88 { titleReady = true }
                introFrames += 1
                return true
            }
        }
        return false
    }
}
