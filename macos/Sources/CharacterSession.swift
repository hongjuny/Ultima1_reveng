import Foundation

/// Native input adapter for GEN. Race/class arithmetic executes generated 6502 blocks.
final class CharacterSession {
    static let attributes = ["Strength", "Agility", "Stamina", "Charisma", "Wisdom", "Intelligence"]
    static let races = ["Human", "Elf", "Dwarf", "Bobbit"]
    static let classes = ["Fighter", "Cleric", "Wizard", "Thief"]
    enum Stage: Int { case attributes, race, sex, profession, name, confirmation, saved }
    var stage = Stage.attributes
    var allocation = [Int](repeating: 10, count: 6)
    var race = 0, sex = 0, profession = 0
    var name = ""
    private let cpu: StartupMachine
    private var template: [UInt8]
    private let spaceSeed = [UInt8.random(in: 0...255), UInt8.random(in: 0...255)]
    var remaining: Int { 90 - allocation.reduce(0, +) }

    init(resources: URL) throws {
        cpu = try StartupMachine(resources: resources)
        try cpu.load("MI.U1", at: 0x7000)
        try cpu.load("GEN", at: 0x8956)
        // GEN $8AEA-$8B24: copy $904F-$90D6 to $7E6F-$7EF6.
        template = Array(cpu.memory[0x904F..<0x90D7])
    }
    @discardableResult func adjust(_ index: Int, by delta: Int) -> Bool {
        guard stage == .attributes, allocation.indices.contains(index), abs(delta) == 1,
              (10...25).contains(allocation[index] + delta), delta < 0 || remaining > 0 else { return false }
        allocation[index] += delta; return true
    }
    func values() throws -> [Int] {
        cpu.memory.replaceSubrange(0x7E6F..<0x7EF7, with: template)
        for i in 0..<6 { cpu.memory[0x7EC8+i*2] = UInt8(allocation[i]) }
        cpu.memory[0x7ED6] = UInt8(race+1)
        cpu.memory[0x7ED8] = UInt8(profession+1)
        // GEN $8CFA-$8D3B and $8E12-$8E53; halt at each original join.
        if stage.rawValue > Stage.race.rawValue { try run(from: 0x8CFA, to: 0x8D3C) }
        if stage.rawValue > Stage.profession.rawValue { try run(from: 0x8E12, to: 0x8E54) }
        return (0..<6).map { Int(cpu.memory[0x7EC8+$0*2]) }
    }
    private func run(from start: Int, to end: Int) throws {
        cpu.pc = start; cpu.p = 0x20
        for _ in 0..<100 {
            if cpu.pc == end { return }
            try cpu.characterBonusStep()
        }
        throw StartupFailure.unsupported("GEN bonus did not reach its join")
    }
    /// GEN $8E83-$8EEB: first letter A-Z; subsequent printable ASCII, 13 bytes.
    static func normalizeName(_ input: String) -> String {
        var result = [UInt8]()
        for byte in input.utf8 {
            guard result.count < 13 else { break }
            var c = byte
            if result.isEmpty {
                if (97...122).contains(c) { c -= 32 }
                guard (65...90).contains(c) else { continue }
            } else {
                guard (32...126).contains(c) else { continue }
                if (65...90).contains(c), result.last != 32 { c += 32 }
            }
            result.append(c)
        }
        return String(bytes: result, encoding: .ascii)!
    }
    func record() throws -> Data {
        _ = try values()
        cpu.memory[0x7E6D] = 0xCA; cpu.memory[0x7E6E] = 1
        // GEN $8E57/$8E5D call random-byte service $15B9 for these fields.
        cpu.memory[0x7EEF] = spaceSeed[0]; cpu.memory[0x7EF0] = spaceSeed[1]
        cpu.memory[0x7EB7] = UInt8(sex)
        for i in 0..<13 { cpu.memory[0x7EB8+i] = 0 }
        for (i,c) in name.utf8.enumerated() where i < 13 { cpu.memory[0x7EB8+i] = c }
        return Data(cpu.memory[0x7E6D..<0x8037])
    }
    func save(to directory: URL) throws {
        guard stage == .confirmation, remaining == 0, !name.isEmpty else {
            throw StartupFailure.unsupported("Character creation is incomplete")
        }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try record().write(to: directory.appendingPathComponent("U1.VARS"), options: .atomic)
        stage = .saved
    }
}
