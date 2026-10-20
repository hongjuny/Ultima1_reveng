#!/usr/bin/env python3
"""Reassemble reviewed code fragments and compare against local extraction."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = (
    ("MI.U1-selector.s", "MI.U1", 0x7000, 0x88F8, 0x893F),
    ("U1.INTRO-entry.s", "U1.INTRO", 0x0800, 0x0800, 0x0806),
    ("U1.INTRO-key-loop.s", "U1.INTRO", 0x0800, 0x1039, 0x1057),
    ("U1.INTRO-load-mi.s", "U1.INTRO", 0x0800, 0x0B50, 0x0B6A),
    ("U1.INTRO-animation-key.s", "U1.INTRO", 0x0800, 0x0B23, 0x0B50),
    ("U1.INTRO-load-support.s", "U1.INTRO", 0x0800, 0x0F23, 0x0F41),
    ("MAKE.INDATA-copy-init.s", "MAKE.INDATA", 0x1E00, 0x1EFD, 0x1F42),
    ("GEN-menu.s", "GEN", 0x8956, 0x89FD, 0x8A10),
    ("GEN-load-player.s", "GEN", 0x8956, 0x8A10, 0x8A2C),
    ("GEN-reload-copy.s", "GEN", 0x8956, 0x8A5B, 0x8A7F),
    ("GEN-initialize-state.s", "GEN", 0x8956, 0x8AEA, 0x8B25),
    ("GEN-attribute-input.s", "GEN", 0x8956, 0x8C00, 0x8C81),
    ("GEN-race-choice.s", "GEN", 0x8956, 0x8CD0, 0x8CE1),
    ("GEN-race-bonus.s", "GEN", 0x8956, 0x8CFA, 0x8D3C),
    ("GEN-sex-choice.s", "GEN", 0x8956, 0x8D72, 0x8D83),
    ("GEN-class-choice.s", "GEN", 0x8956, 0x8DEA, 0x8DFB),
    ("GEN-class-bonus.s", "GEN", 0x8956, 0x8E12, 0x8E54),
    ("GEN-name-input.s", "GEN", 0x8956, 0x8E83, 0x8EEE),
    ("GEN-save-confirm.s", "GEN", 0x8956, 0x8F0F, 0x8F31),
    ("OUT-location-dispatch.s", "OUT", 0x8956, 0x90FF, 0x913A),
    ("OUT-space-dispatch.s", "OUT", 0x8956, 0x8D6E, 0x8D73),
    ("OUT-key-poll.s", "OUT", 0x8956, 0x8A6A, 0x8A76),
    ("TWN-map-copy.s", "TWN", 0x8956, 0x89B9, 0x89DE),
    ("CAS-map-copy.s", "CAS", 0x8956, 0x89BB, 0x89E0),
)


def main() -> int:
    for program in ("ca65", "ld65"):
        if not shutil.which(program):
            print(f"missing {program} (install cc65)", file=sys.stderr)
            return 2
    output = ROOT / "build" / "verify"
    output.mkdir(parents=True, exist_ok=True)
    for source_name, original_name, load_base, start, end in FRAGMENTS:
        stem = Path(source_name).stem
        source = ROOT / "disasm" / source_name
        original = ROOT / "extracted" / original_name
        if not original.is_file():
            print(f"missing {original}", file=sys.stderr)
            return 2
        config = output / f"{stem}.cfg"
        config.write_text(
            f"MEMORY {{ CODE: start = ${start:04X}, size = ${end-start:04X}, "
            "type = ro, file = %O; }\n"
            "SEGMENTS { CODE: load = CODE, type = ro; }\n"
        )
        obj = output / f"{stem}.o"
        binary = output / f"{stem}.bin"
        subprocess.run(["ca65", str(source), "-o", str(obj)], check=True)
        subprocess.run(["ld65", "-C", str(config), "-o", str(binary), str(obj)], check=True)
        actual = binary.read_bytes()
        expected = original.read_bytes()[start-load_base:end-load_base]
        if actual != expected:
            for offset, (a, b) in enumerate(zip(actual, expected)):
                if a != b:
                    print(f"{source_name}: mismatch at ${start+offset:04X}", file=sys.stderr)
                    break
            else:
                print(f"{source_name}: length mismatch ({len(actual)} vs {len(expected)})", file=sys.stderr)
            return 1
        print(f"{source_name}: matched ${start:04X}-${end-1:04X} ({len(actual)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
