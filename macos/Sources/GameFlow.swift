import Foundation

extension StartupMachine {
    func beginGame() { gameRunning = true; keyboard = 0xC1 }
    func sendKey(_ key: UInt8) { keyboard = key | 0x80 }

    func gameLoader(execute: Bool) throws {
        let argument = popWord() + 1
        var end = argument
        while end < argument + 32 && memory[end] != 0 { end += 1 }
        let name = String(bytes: memory[argument..<end], encoding: .ascii) ?? ""
        if pc == 0xB733 {
            setFilename(name)
            a = nz(0); setFlag(1, false); pc = end+1; return
        }
        let address: Int
        switch name {
        case "MI.U1": address = 0x7000; engineLoaded = true
        case "STUPH": address = 0x0800
        case "GEN", "OUT", "TWN", "CAS", "DNG", "SPA", "TM": address = 0x8956; overlay = name
        case "NIF": address = 0x4000
        case "TCMAPS": address = 0x4000
        case "MAPCHARS": address = 0x0800
        default: throw StartupFailure.unsupported("Module not yet translated: \(name)")
        }
        try load(name, at: address)
        a = nz(0); setFlag(1, false)
        if execute { pushWord(end); pc = address } else { pc = end + 1 }
    }

    func nextGameFrame(budget: Int) throws -> Bool {
        for _ in 0..<budget {
            // Only reference captures freeze at this boundary. Interactive runs
            // execute the original cursor, polling and normalization loops.
            if captureInputBoundaries && engineLoaded && (pc == 0x15BF || (overlay == "OUT" && pc == 0x8A6C) || (overlay == "TWN" && pc == 0x8A1E) || (overlay == "CAS" && pc == 0x8A27) || (overlay == "DNG" && pc == 0x8DDA) || (overlay == "SPA" && [0x8A5F, 0x9361, 0x9175].contains(pc)) || (overlay == "TM" && [0x9815, 0x9132].contains(pc))) && keyboard & 0x80 == 0 && memory[0x78] == 0 {
                awaitingInput = true
                return true
            }
            awaitingInput = false
            if engineLoaded && [0xB721, 0xB71E, 0xB736].contains(pc) {
                try hostFileService(); continue
            }
            if engineLoaded && pc == 0xB724 {
                let args = popWord() + 1
                let source = Int(memory[args]) | Int(memory[args+1]) << 8
                let length = Int(memory[args+2]) | Int(memory[args+3]) << 8
                let directory = playerDirectory
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                try Data(memory[source..<source+length]).write(to: directory.appendingPathComponent("U1.VARS"), options: .atomic)
                a = nz(0); setFlag(1, false); pc = args + 6; saves += 1
                continue
            }
            if pc == 0xB70C && gameRunning { try gameLoader(execute: true); continue }
            if engineLoaded && (pc == 0xB703 || pc == 0xB733) { try gameLoader(execute: false); continue }
            // Apple monitor HOME clears the text page; the game itself draws HGR.
            if engineLoaded && pc == 0xFC58 {
                for address in 0x400..<0x800 { memory[address] = 0xA0 }
                memory[0x24] = 0; memory[0x25] = 0; rts(); continue
            }
            visited.insert(pc); instructions += 1
            speaker.clockInstruction(self)
            if engineLoaded {
                if pc >= 0x8956 && !overlay.isEmpty {
                    switch overlay {
                    case "GEN": try stepGEN()
                    case "OUT": try stepOUT()
                    case "TWN": try stepTWN()
                    case "CAS": try stepCAS()
                    case "DNG": try stepDNG()
                    case "SPA": try stepSPA()
                    case "TM": try stepTM()
                    default: throw StartupFailure.unsupported("Untranslated overlay: \(overlay)")
                    }
                }
                else if pc >= 0x7000 && pc < 0x89BD { try stepMIU1() }
                else if pc >= 0x1583 && pc < 0x2000 { try stepSTUPH() }
                else { throw StartupFailure.untranslated(pc) }
            } else {
                try translatedStep()
            }
        }
        return true
    }
}
