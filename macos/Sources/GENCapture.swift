import Foundation

func captureGEN(resources: URL, output: URL, enterOut: Bool = false, resumeOnly: Bool = false, enterTown: Bool = false, enterCastle: Bool = false, enterDungeon: Bool = false, enterSpace: Bool = false) throws {
    try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
    let machine = try StartupMachine(resources: resources)
    // Valid packed-decimal inputs cover the number formatter's arithmetic.
    func bcd(_ n: Int) -> UInt8 { UInt8((n / 10) << 4 | n % 10) }
    for left in 0..<100 {
        for right in 0..<100 {
            for carry in 0...1 {
                machine.a = bcd(left); machine.p = 0x28 | UInt8(carry)
                machine.adc(bcd(right))
                let sum = left + right + carry
                guard machine.a == bcd(sum % 100), machine.flag(1) == (sum >= 100) else {
                    throw StartupFailure.unsupported("Decimal ADC mismatch")
                }
                machine.a = bcd(left); machine.p = 0x28 | UInt8(carry)
                machine.sbc(bcd(right))
                let difference = left - right - (1-carry)
                guard machine.a == bcd((difference+100)%100), machine.flag(1) == (difference >= 0) else {
                    throw StartupFailure.unsupported("Decimal SBC mismatch")
                }
            }
        }
    }
    machine.a = 0; machine.p = 0x24
    print("Decimal arithmetic: 40,000 valid ADC/SBC cases passed")
    machine.saveDirectory = output
    machine.captureInputBoundaries = true
    while !machine.titleReady { _ = try machine.nextFrame() }
    machine.beginGame()
    func waitForInput() throws {
        for _ in 0..<1000 {
            _ = try machine.nextFrame(budget: 250_000)
            if machine.awaitingInput { return }
        }
        throw StartupFailure.unsupported("GEN input not reached")
    }
    func key(_ c: UInt8) throws { machine.sendKey(c); try waitForInput() }
    func capture(_ name: String) throws {
        try HGRRenderer.save(HGRRenderer.image(memory: machine.memory, page: machine.page), to: output.appendingPathComponent(name+".png"))
        try Data(machine.memory).write(to: output.appendingPathComponent(name+".ram"))
        try HGRRenderer.pixels(memory: machine.memory, page: machine.page).write(to: output.appendingPathComponent(name+".rgba"))
        try JSONSerialization.data(withJSONObject: ["pc": machine.pc, "page": machine.page,
            "overlay": machine.overlay, "coordinates": [Int(machine.memory[0]), Int(machine.memory[1])]],
            options: [.prettyPrinted, .sortedKeys]).write(to: output.appendingPathComponent(name+".json"))
        print(String(format:"%@ %@: $%04X, page $%04X", machine.overlay, name, machine.pc, machine.page))
    }
    try waitForInput(); try capture("menu")
    if resumeOnly {
        try key(66); try capture("out-resumed")
        guard machine.overlay == "OUT" else { throw StartupFailure.unsupported("Saved game did not resume OUT") }
        let saved = try Data(contentsOf: output.appendingPathComponent("U1.VARS"))
        guard Data(machine.memory[0x7E6D..<0x8037]) == saved else {
            throw StartupFailure.unsupported("Resumed player state differs from saved record")
        }
        return
    }
    try key(65); try capture("attributes")
    for _ in 0..<15 { try key(21) }
    try key(47)
    for _ in 0..<15 { try key(21) }
    try key(32); try capture("race")
    try key(65); try capture("sex")
    try key(65); try capture("class")
    try key(65); try capture("name")
    try key(65); try key(13); try capture("confirmation")
    try key(89); try capture("saved-menu")
    guard machine.saves == 1 else { throw StartupFailure.unsupported("GEN did not save") }
    if enterOut {
        try key(66); try capture("out-first-input")
        guard machine.overlay == "OUT" else { throw StartupFailure.unsupported("OUT not loaded") }
        if enterSpace {
            // Controlled test fixture only: supply a shuttle on the current tile.
            // The interactive application still requires original acquisition rules.
            let tile = 0x6000 + Int(machine.memory[1])*64 + Int(machine.memory[0])
            machine.memory[0x7E7C] = 0
            machine.memory[tile] = 0x1C
            try capture("space-board-fixture")
            try key(66); try capture("space-first-input")
            guard machine.overlay == "SPA" else { throw StartupFailure.unsupported("SPA not entered") }
            let origin = machine.memory
            let cpu = (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page)
            for direction: UInt8 in [11,10,21,8] {
                machine.memory = origin
                (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
                try key(direction); try capture(String(format:"space-direction-%02x", direction))
            }
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            try key(86); try capture("space-view")
            try key(70); try capture("space-fire-message")
            if machine.pc == 0x15BF { try key(32) }
            try capture("space-fire")
            try key(86)
            for _ in 0..<3 where machine.pc == 0x15BF { try key(32) }
            try capture("space-view-exit")
            guard machine.pc == 0x8A5F else { throw StartupFailure.unsupported("V did not leave space view") }
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            machine.captureInputBoundaries = false
            machine.sendKey(21)
            for _ in 0..<120 { _ = try machine.nextFrame(budget: 6_000) }
            guard machine.overlay == "SPA", machine.memory[0x923F] == 0,
                  machine.word(at: 0x7EE9) == 998 else {
                throw StartupFailure.unsupported("Live space polling did not accept Right")
            }
            try capture("space-live")
            machine.captureInputBoundaries = true
            // Controlled approach fixture: move the native ship to an existing
            // planet; retain the original drawing, collision and landing code.
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            machine.memory[0x6E] = machine.memory[0x926C]
            machine.memory[0x6F] = machine.memory[0x9276]
            try capture("space-landing-fixture")
            try key(32); try capture("space-landed")
            guard machine.overlay == "OUT" else { throw StartupFailure.unsupported("Planet landing did not restore OUT") }
            return
        }
        if enterDungeon {
            for c: UInt8 in [11,11] + Array(repeating: 8, count: 9) { try key(c) }
            let route: [UInt8] = Array(repeating: 11, count: 9) + [21,21,21,11,21]
                + Array(repeating: 11, count: 5) + Array(repeating: 21, count: 9) + [11]
            for c in route { try key(c) }
            try capture("dungeon-tile")
            try key(69); try capture("dungeon-first-input")
            guard machine.overlay == "DNG" else { throw StartupFailure.unsupported("Dungeon overlay not entered") }
            let origin = machine.memory
            let cpu = (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page)
            for direction: UInt8 in [11, 10, 21, 8] {
                machine.memory = origin
                (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
                try key(direction); try capture(String(format:"dungeon-direction-%02x", direction))
            }
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            let savedBefore = machine.saves
            try key(81); try capture("dungeon-save-denied")
            guard machine.saves == savedBefore else { throw StartupFailure.unsupported("Dungeon Q unexpectedly saved") }
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            machine.captureInputBoundaries = false
            machine.sendKey(11)
            for _ in 0..<120 { _ = try machine.nextFrame(budget: 6_000) }
            guard machine.overlay == "DNG", machine.memory[0xA4E8] == 1, machine.memory[0xA4E9] == 2 else {
                throw StartupFailure.unsupported("Live dungeon polling did not accept Up")
            }
            try capture("dungeon-live")
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            machine.captureInputBoundaries = true
            try key(11); try capture("dungeon-up")
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            try key(75); try capture("dungeon-exit")
            guard machine.overlay == "OUT" else { throw StartupFailure.unsupported("Dungeon exit did not restore OUT") }
            return
        }
        if enterCastle {
            for c: UInt8 in [11,11] + Array(repeating: 8, count: 9) { try key(c) }
            try capture("castle-tile")
            try key(69); try capture("castle-first-input")
            guard machine.overlay == "CAS" else { throw StartupFailure.unsupported("Castle overlay not entered") }
            let origin = machine.memory
            let cpu = (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page)
            try key(21); try capture("castle-right")
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            let kingRoute: [UInt8] = Array(repeating: 21, count: 5) + Array(repeating: 11, count: 3)
                + Array(repeating: 21, count: 9) + Array(repeating: 10, count: 2)
                + Array(repeating: 21, count: 17) + Array(repeating: 11, count: 2)
            for c in kingRoute { try key(c) }
            try capture("castle-king")
            guard machine.memory[0] == 31, machine.memory[1] == 6 else {
                throw StartupFailure.unsupported("Walking route did not reach king")
            }
            try key(84); try capture("castle-talk")
            try key(83); try capture("castle-service")
            guard machine.memory[0x7EAF] == 1 else { throw StartupFailure.unsupported("King service did not assign quest") }
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = cpu
            try key(8); try capture("castle-exit")
            guard machine.overlay == "OUT" else { throw StartupFailure.unsupported("Castle exit did not restore OUT") }
            return
        }
        if enterTown {
            let route: [UInt8] = [11,11] + Array(repeating: 8, count: 10) + [10]
            for c in route { try key(c) }
            try capture("town-tile")
            try key(69); try capture("town-first-input")
            guard machine.overlay == "TWN" else { throw StartupFailure.unsupported("Town overlay not entered") }
            let townOrigin = machine.memory
            let townCPU = (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page)
            machine.captureInputBoundaries = false
            machine.sendKey(11)
            for _ in 0..<120 { _ = try machine.nextFrame(budget: 6_000) }
            guard machine.overlay == "TWN", machine.memory[0] == 19, machine.memory[1] == 16 else {
                throw StartupFailure.unsupported("Live town polling did not accept Up")
            }
            try capture("town-live")
            machine.memory = townOrigin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = townCPU
            machine.captureInputBoundaries = true
            try key(11); try capture("town-up")
            try key(10); try key(10); try capture("town-exit")
            guard machine.overlay == "OUT" else { throw StartupFailure.unsupported("Town exit did not restore OUT") }
            return
        }
        let origin = machine.memory
        let registers = (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page)
        func restoreOutdoorInput() {
            machine.memory = origin
            (machine.a, machine.x, machine.y, machine.sp, machine.p, machine.pc, machine.page) = registers
        }
        for direction: UInt8 in [11, 10, 21, 8] {
            restoreOutdoorInput()
            try key(direction); try capture(String(format:"out-direction-%02x", direction))
        }
        restoreOutdoorInput()
        try key(11); try capture("out-up")
        try key(32); try capture("out-pass")
        try key(81); try capture("out-save")
        guard machine.saves == 2 else { throw StartupFailure.unsupported("Outdoor Q did not save") }
        restoreOutdoorInput()
        machine.captureInputBoundaries = false
        machine.sendKey(11)
        for _ in 0..<120 { _ = try machine.nextFrame(budget: 6_000) }
        guard machine.memory[0] == 39, machine.memory[1] == 32 else {
            throw StartupFailure.unsupported("Live outdoor input did not move north")
        }
        try HGRRenderer.save(HGRRenderer.image(memory: machine.memory, page: machine.page), to: output.appendingPathComponent("out-live.png"))
        print("Live Sosaria polling and rendering accepted Up")
        return
    }
    // Exercise the actual timer-driven polling path with capture stops disabled.
    machine.captureInputBoundaries = false
    machine.sendKey(65)
    for _ in 0..<20 { _ = try machine.nextFrame(budget: 150_000) }
    guard machine.memory[0x903F] == 30, machine.memory[0x7EC8] == 10 else {
        throw StartupFailure.unsupported("Live GEN polling did not enter allocation")
    }
    machine.sendKey(21)
    for _ in 0..<20 { _ = try machine.nextFrame(budget: 150_000) }
    guard machine.memory[0x903F] == 29, machine.memory[0x7EC8] == 11 else {
        throw StartupFailure.unsupported("Live GEN polling did not accept Right")
    }
    try HGRRenderer.save(HGRRenderer.image(memory: machine.memory, page: machine.page), to: output.appendingPathComponent("live-input.png"))
    print("Original live keyboard/cursor polling accepted A and Right")
}
