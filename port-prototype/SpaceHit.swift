// First address-preserving Swift transcription from Ghidra's SPA listing.
// Scope: SPA $9700-$9741, entered after a confirmed hit with Y as ship-cell index.
// Other SPA code, renderer, and sound remain outside this routine.

public enum SpaceAceBranch: String {
    case belowTwenty
    case exactlyTwenty
    case aboveTwenty
}

public struct SpaceHitExit {
    public let accumulator: UInt8
    public let carry: Bool
    public let zero: Bool
    public let negative: Bool
    public let branch: SpaceAceBranch
}

public enum SpaceHitPort {
    public static func apply(memory: inout [UInt8], y: UInt8) -> SpaceHitExit {
        precondition(memory.count == 65536, "requires the Apple II 64 KiB address space")
        let shipAddress = 0xB099 + Int(y)

        // SPA $9700-$9708: remove one ship from the selected packed sector byte.
        memory[shipAddress] = memory[shipAddress] &- 0x40

        // SPA $9709-$9731: add 100 to 16-bit experience, then cap at 9999.
        let oldExperience = UInt16(memory[0x7EE7]) |
            (UInt16(memory[0x7EE8]) << 8)
        let addedExperience = oldExperience &+ 100
        let experience = min(addedExperience, UInt16(9999))
        memory[0x7EE7] = UInt8(truncatingIfNeeded: experience)
        memory[0x7EE8] = UInt8(truncatingIfNeeded: experience >> 8)

        // SPA $9732-$9739: INC, then undo wrap at zero; count saturates at 255.
        let incremented = memory[0x7EB6] &+ 1
        memory[0x7EB6] = incremented == 0 ? 255 : incremented

        // SPA $973A-$9741: LDA count; CMP #$14; branch on C and Z.
        let accumulator = memory[0x7EB6]
        let difference = accumulator &- 20
        let carry = accumulator >= 20
        let zero = accumulator == 20
        let branch: SpaceAceBranch = accumulator < 20 ? .belowTwenty :
            (zero ? .exactlyTwenty : .aboveTwenty)
        return SpaceHitExit(accumulator: accumulator, carry: carry,
                            zero: zero, negative: difference & 0x80 != 0,
                            branch: branch)
    }
}
