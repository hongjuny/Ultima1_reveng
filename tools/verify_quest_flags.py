#!/usr/bin/env python3
"""Check quest completion, castle rewards, vehicle creation, and TM gate."""

from disassemble import ROOT


AWARDS = ((0x95DE, 0x963A, 0x7E75, b"red gem"),
          (0x963E, 0x9697, 0x7E76, b"green gem"),
          (0x969B, 0x96F0, 0x7E77, b"blue gem"),
          (0x96F4, 0x9755, 0x7E78, b"white gem"))


def main():
    castle = (ROOT / "extracted/CAS").read_bytes()
    space = (ROOT / "extracted/SPA").read_bytes()
    outdoor = (ROOT / "extracted/OUT").read_bytes()
    dungeon = (ROOT / "extracted/DNG").read_bytes()

    def has(payload, base, start, end, sequence):
        assert sequence in payload[start-base:end-base], f"missing opcode at ${start:04X}"

    # Castle's local index is derived from the world location ($7EED) and
    # world group ($7E6F). Odd indices give gems; even indices give strength.
    has(castle, 0x8956, 0x8969, 0x898D, b"\xAD\xED\x7E\xC9\x15")
    has(castle, 0x8956, 0x8975, 0x898D, b"\x6D\x6F\x7E\x6D\x6F\x7E\x8D\x3B\x9E")
    has(castle, 0x8956, 0x8975, 0x898D, b"\xA9\x06\x38\xED\x3B\x9E\x8D\x3B\x9E")
    assert castle[0x92CC-0x8956:0x92D7-0x8956] == bytes.fromhex(
        "ae 3b 9e bd a9 7e 10 03 4c e7 94")
    has(castle, 0x8956, 0x9437, 0x9447, b"\xFE\xA9\x7E")
    has(castle, 0x8956, 0x94E7, 0x94F4, b"\xA9\x00\x9D\xA9\x7E")
    # Landmark visits can complete only the even numbered castle quests.
    ids = outdoor[0x9D9C-0x8956:0x9DA4-0x8956]
    targets = outdoor[0x9DAC-0x8956:0x9DB4-0x8956]
    assert ids == bytes((0x42, 0x41, 0x2D, 0x2C, 0x18, 0x17, 0x03, 0x02))
    assert targets == bytes((0xFF, 6, 0xFF, 4, 0xFF, 2, 0xFF, 0))
    has(outdoor, 0x8956, 0x90F0, 0x9172, b"\xBC\xAC\x9D\x30")
    has(outdoor, 0x8956, 0x9151, 0x9172, b"\xB9\xA9\x7E\xF0")
    has(outdoor, 0x8956, 0x9151, 0x9172, b"\xA9\xFF\x99\xA9\x7E")
    # Dungeon monster type five, at depths 3+ in pairs, completes odd quests.
    assert dungeon[0x94A7-0x8956:0x94C9-0x8956] == bytes.fromhex(
        "ad 2e a5 c9 05 d0 32 ad 06 a5 38 e9 01 4a f0 29 0a aa ca "
        "bd a9 7e f0 21 30 1f a9 ff 9d a9 7e 20 19 81")
    assert [((depth - 1) >> 1) * 2 - 1 for depth in (3, 5, 7, 9)] == [1, 3, 5, 7]
    assert castle[0x95BC-0x8956:0x95C0-0x8956] == b"\xAD\x6F\x7E\x0A"
    for slot, (entry, pc, flag, color) in enumerate(AWARDS):
        pointer_at = 0x95D6 + slot * 2 - 0x8956
        assert int.from_bytes(castle[pointer_at:pointer_at+2], "little") == entry
        offset = pc - 0x8956
        assert castle[offset:offset+3] == bytes((0xEE, flag & 0xFF, flag >> 8))
        intro = castle.rfind(bytes((0x20, 0x19, 0x81)), max(0, offset - 110), offset)
        assert intro >= 0, f"no inline text call before ${pc:04X}"
        payload = castle[intro+3:offset].split(b"\x00", 1)[0]
        normalized = bytes(byte & 0x7F for byte in payload).lower()
        assert color in normalized, f"expected gem description before ${pc:04X}"
    gate = outdoor[0x8D73-0x8956:0x8D8B-0x8956]
    for flag in range(0x75, 0x79):
        assert bytes((0xAD, flag, 0x7E)) in gate
    assert outdoor[0x8D87-0x8956:0x8D89-0x8956] == b"\xA9\x18"
    # Castle rescue exit arms a one-shot world rebuild that plants code $0F
    # (raw map byte $1E), the craft admitted to TM after the four-gem gate.
    has(castle, 0x8956, 0x8B59, 0x8B7B, b"\xAD\xB6\x7E\xC9\x14")
    has(castle, 0x8956, 0x8B59, 0x8B7B, b"\xAD\xE7\x7E\xC9\x58\xAD\xE8\x7E\xE9\x1B")
    has(castle, 0x8956, 0x8BF4, 0x8C00, b"\xA9\x01\x8D\xB5\x7E")
    # The space hit path awards 100 experience and increments the same byte
    # consumed by CAS; it saturates at 255 and singles out count 20.
    has(space, 0x8956, 0x9700, 0x9732, b"\xAD\xE7\x7E\x69\x64\x8D\xE7\x7E")
    has(space, 0x8956, 0x9732, 0x9740, b"\xEE\xB6\x7E\xD0\x03\xCE\xB6\x7E\xAD\xB6\x7E\xC9\x14")
    has(outdoor, 0x8956, 0x9565, 0x9597, b"\xAD\xB5\x7E\xF0")
    has(outdoor, 0x8956, 0x956C, 0x9597, b"\xAD\xA8\x7E\xC9\x07\xB0")
    has(outdoor, 0x8956, 0x958C, 0x9597, b"\xA9\x0F\x20\x27\x99")
    has(outdoor, 0x8956, 0x958C, 0x9597, b"\xA9\x00\x8D\xB5\x7E")
    has(outdoor, 0x8956, 0x9927, 0x9959, b"\x0A\x9D\x97\x7F")
    has(outdoor, 0x8956, 0x9927, 0x9959, b"\x68\x91\x72\xEE\xF6\x7E")
    print("Quest producer → castle reward → TM gate and rescue → craft producer match extraction")


if __name__ == "__main__":
    main()
