import Foundation

/// Explicit diagnostic session. All files go to a unique temporary directory;
/// the player's real Application Support save is never read or overwritten.
func makeTestSession(resources: URL, overlay: String, directory: URL? = nil) throws -> StartupMachine {
    guard ["SPA", "TM"].contains(overlay) else { throw StartupFailure.unsupported("Unknown test session") }
    let cpu = try StartupMachine(resources: resources)
    cpu.saveDirectory = directory ?? FileManager.default.temporaryDirectory
        .appendingPathComponent("UltimaI-Test-\(UUID().uuidString)")
    cpu.captureInputBoundaries = true
    while !cpu.titleReady { _ = try cpu.nextFrame() }
    cpu.beginGame()
    func waitForInput() throws {
        for _ in 0..<1000 {
            _ = try cpu.nextFrame(budget: 250_000)
            if cpu.awaitingInput { return }
        }
        throw StartupFailure.unsupported("Test session input not reached")
    }
    func key(_ c: UInt8) throws { cpu.sendKey(c); try waitForInput() }
    try waitForInput()
    try key(65)
    for _ in 0..<15 { try key(21) }
    try key(47)
    for _ in 0..<15 { try key(21) }
    try key(32)
    for _ in 0..<3 { try key(65) } // Human, male, fighter.
    for c in "Tester".uppercased().utf8 { try key(c) }
    try key(13); try key(89); try key(66)
    guard cpu.overlay == "OUT" else { throw StartupFailure.unsupported("Test character did not enter Sosaria") }
    let tile = 0x6000 + Int(cpu.memory[1])*64 + Int(cpu.memory[0])
    cpu.memory[0x7E7C] = 0
    if overlay == "SPA" { cpu.memory[tile] = 0x1C }
    else {
        cpu.memory[tile] = 0x1E
        for address in 0x7E75...0x7E78 { cpu.memory[address] = 1 }
    }
    try key(66) // Original B command selects/loads the overlay.
    guard cpu.overlay == overlay else { throw StartupFailure.unsupported("Test overlay was not selected") }
    cpu.captureInputBoundaries = false
    return cpu
}

func captureTestSessions(resources: URL, output: URL) throws {
    try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
    let realSave = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("UltimaI/Characters/U1.VARS")
    let before = try? Data(contentsOf: realSave)
    for overlay in ["SPA", "TM"] {
        let cpu = try makeTestSession(resources: resources, overlay: overlay,
                                     directory: output.appendingPathComponent(overlay))
        guard cpu.saveDirectory != realSave.deletingLastPathComponent() else {
            throw StartupFailure.unsupported("Test save is not isolated")
        }
        try HGRRenderer.save(HGRRenderer.image(memory: cpu.memory, page: cpu.page),
                             to: output.appendingPathComponent(overlay+"-test.png"))
        try Data(cpu.memory).write(to: output.appendingPathComponent(overlay+"-test.ram"))
        if overlay == "SPA" {
            cpu.sendKey(21)
            for _ in 0..<120 { _ = try cpu.nextFrame(budget: 6_000) }
            guard cpu.memory[0x923F] == 0, cpu.word(at: 0x7EE9) == 998 else {
                throw StartupFailure.unsupported("Space test did not accept Right")
            }
        } else {
            cpu.captureInputBoundaries = true
            for page in 1...4 {
                cpu.sendKey(32)
                for _ in 0..<1000 {
                    _ = try cpu.nextFrame(budget: 250_000)
                    if cpu.awaitingInput { break }
                }
                try HGRRenderer.save(HGRRenderer.image(memory: cpu.memory, page: cpu.page),
                                     to: output.appendingPathComponent("TM-page-\(page).png"))
            }
            guard cpu.pc == 0x9815 else { throw StartupFailure.unsupported("TM main loop not reached") }
            try Data(cpu.memory).write(to: output.appendingPathComponent("TM-main.ram"))
            cpu.sendKey(21)
            for _ in 0..<1000 {
                _ = try cpu.nextFrame(budget: 250_000)
                if cpu.awaitingInput { break }
            }
            try Data(cpu.memory).write(to: output.appendingPathComponent("TM-right.ram"))
            // Automated ending probe only, not the interactive test character:
            // survive the short approach and reduce Mondain to one hit.
            cpu.memory[0x7EC6] = 0xB8; cpu.memory[0x7EC7] = 0x0B
            func advanceKey(_ key: UInt8) throws {
                cpu.sendKey(key)
                for _ in 0..<1000 {
                    _ = try cpu.nextFrame(budget: 250_000)
                    if cpu.awaitingInput { return }
                }
                throw StartupFailure.unsupported("TM test input not reached")
            }
            for _ in 0..<9 { try advanceKey(21) }
            guard cpu.memory[0] == 14, cpu.memory[1] == 5 else {
                throw StartupFailure.unsupported("TM gem approach failed")
            }
            try advanceKey(71)
            guard cpu.memory[0x95AB] == 1 else { throw StartupFailure.unsupported("TM gem was not destroyed") }
            cpu.memory[0x7EF4] = 1; cpu.memory[0x7EF5] = 0
            for _ in 0..<8 {
                try advanceKey(65); try advanceKey(21)
                if cpu.pc == 0x9132 { break }
            }
            guard cpu.pc == 0x9132 else { throw StartupFailure.unsupported("TM ending was not reached") }
            try Data(cpu.memory).write(to: output.appendingPathComponent("TM-ending.ram"))
            try HGRRenderer.save(HGRRenderer.image(memory: cpu.memory, page: cpu.page),
                                 to: output.appendingPathComponent("TM-ending.png"))
            print("TM controlled one-hit victory loaded and rendered NIF")
        }
        print("\(overlay) temporary test session initialized and accepted input")
    }
    guard before == (try? Data(contentsOf: realSave)) else {
        throw StartupFailure.unsupported("Real player save changed during test session")
    }
    print("Real save unchanged")
}
