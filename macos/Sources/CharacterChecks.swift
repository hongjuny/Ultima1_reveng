import Foundation

func checkCharacterCreation(resources: URL, output: URL) throws {
    func require(_ condition: Bool, _ message: String) throws {
        if !condition { throw StartupFailure.unsupported(message) }
    }
    let session = try CharacterSession(resources: resources)
    try require(session.remaining == 30 && session.allocation == Array(repeating: 10, count: 6), "Initial GEN attributes")
    try require(!session.adjust(0, by: -1), "Minimum must be 10")
    for _ in 0..<15 { try require(session.adjust(0, by: 1), "Allocate Strength") }
    try require(!session.adjust(0, by: 1), "Maximum must be 25")
    for _ in 0..<15 { try require(session.adjust(1, by: 1), "Allocate Agility") }
    try require(session.remaining == 0 && !session.adjust(2, by: 1), "Point pool must not underflow")
    let raceBonuses = [[0,0,0,0,0,5], [0,5,0,0,0,0], [5,0,0,0,0,0], [-5,0,0,0,10,0]]
    let classBonuses = [[10,10,0,0,0,0], [0,0,0,0,10,0], [0,0,0,0,0,10], [0,10,0,0,0,0]]
    session.stage = .confirmation
    var combinations = [[String: Any]]()
    for race in 0..<4 {
        for profession in 0..<4 {
            session.race = race; session.profession = profession
            let expected = (0..<6).map { session.allocation[$0]+raceBonuses[race][$0]+classBonuses[profession][$0] }
            let actual = try session.values()
            try require(actual == expected, "Ghidra bonus mismatch")
            try require(try session.values() == expected, "Bonuses must not accumulate on redraw")
            combinations.append(["race": race+1, "class": profession+1, "attributes": actual])
        }
    }
    try require(CharacterSession.normalizeName("AVATAR OF BRITANNIA") == "Avatar Of Bri", "GEN name capitalization/length")
    try require(CharacterSession.normalizeName("123! aVATAR") == "Avatar", "GEN first letter")
    session.race = 0; session.profession = 0; session.name = "A"
    try session.save(to: output)
    let record = try Data(contentsOf: output.appendingPathComponent("U1.VARS"))
    try require(record.count == 458 && record[0] == 0xCA && record[1] == 1, "GEN save record header")
    try require(record[0x4B] == 65 && record[0x69] == 1 && record[0x6B] == 1, "GEN identity offsets")
    try JSONSerialization.data(withJSONObject: ["combinations": combinations, "record_length": record.count,
        "checks": "limits, pool, 16 bonuses, redraw, name, record"], options: [.prettyPrinted, .sortedKeys])
        .write(to: output.appendingPathComponent("character-checks.json"))
    print("Character creation checks passed: 16 race/class combinations; 458-byte record saved")
}
