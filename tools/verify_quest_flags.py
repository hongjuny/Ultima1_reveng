#!/usr/bin/env python3
"""Check the four castle gem-award writes and the outdoor TM gate."""

from disassemble import ROOT


AWARDS = ((0x95DE, 0x963A, 0x7E75, b"red gem"),
          (0x963E, 0x9697, 0x7E76, b"green gem"),
          (0x969B, 0x96F0, 0x7E77, b"blue gem"),
          (0x96F4, 0x9755, 0x7E78, b"white gem"))


def main():
    castle = (ROOT / "extracted/CAS").read_bytes()
    outdoor = (ROOT / "extracted/OUT").read_bytes()
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
    print("CAS four gem-award writes and OUT four-flag TM gate match local extraction")


if __name__ == "__main__":
    main()
