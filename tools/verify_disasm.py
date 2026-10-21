#!/usr/bin/env python3
"""Reassemble reviewed code fragments and compare against local extraction."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = (
    ("MI.U1-selector.s", "MI.U1", 0x7000, 0x88F8, 0x893F),
    ("MI.U1-turn-update.s", "MI.U1", 0x7000, 0x82E2, 0x8331),
    ("MI.U1-death-reset.s", "MI.U1", 0x7000, 0x888D, 0x88A1),
    ("MI.U1-status-values.s", "MI.U1", 0x7000, 0x837F, 0x83A9),
    ("STUPH-random.s", "STUPH", 0x0800, 0x1DF1, 0x1E18),
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
    ("OUT-space-handler.s", "OUT", 0x8956, 0x8A76, 0x8A7D),
    ("OUT-enter-gate.s", "OUT", 0x8956, 0x90C8, 0x90DD),
    ("OUT-direction-entry.s", "OUT", 0x8956, 0x9351, 0x936D),
    ("OUT-tile-lookup.s", "OUT", 0x8956, 0x99D1, 0x99F8),
    ("OUT-death-gate.s", "OUT", 0x8956, 0x898A, 0x8995),
    ("OUT-resurrection-init.s", "OUT", 0x8956, 0x89E8, 0x8A1D),
    ("OUT-resurrection-fill.s", "OUT", 0x8956, 0x8A3A, 0x8A5F),
    ("CAS-key-poll.s", "CAS", 0x8956, 0x8A25, 0x8A31),
    ("CAS-left-edge.s", "CAS", 0x8956, 0x8AA8, 0x8AC1),
    ("CAS-move-check.s", "CAS", 0x8956, 0x8C00, 0x8C13),
    ("CAS-map-tile-check.s", "CAS", 0x8956, 0x9BD9, 0x9BFE),
    ("CAS-collision-wrapper.s", "CAS", 0x8956, 0x9BC0, 0x9BD9),
    ("CAS-actor-lookup.s", "CAS", 0x8956, 0x9BFE, 0x9C23),
    ("CAS-attack-ray.s", "CAS", 0x8956, 0x8CC9, 0x8CF7),
    ("CAS-attack-hit-roll.s", "CAS", 0x8956, 0x8D08, 0x8D2C),
    ("CAS-attack-damage.s", "CAS", 0x8956, 0x8D46, 0x8D84),
    ("CAS-guard-hit-roll.s", "CAS", 0x8956, 0x9951, 0x9981),
    ("CAS-guard-damage-roll.s", "CAS", 0x8956, 0x998F, 0x99A6),
    ("CAS-guard-player-hp.s", "CAS", 0x8956, 0x99CB, 0x99E1),
    ("CAS-move-commit.s", "CAS", 0x8956, 0x8C29, 0x8C4C),
    ("TWN-map-copy.s", "TWN", 0x8956, 0x89B9, 0x89DE),
    ("TWN-food-purchase.s", "TWN", 0x8956, 0x932F, 0x9365),
    ("TWN-food-price.s", "TWN", 0x8956, 0x9257, 0x926F),
    ("CAS-map-copy.s", "CAS", 0x8956, 0x89BB, 0x89E0),
    ("DNG-key-poll.s", "DNG", 0x8956, 0x8DDA, 0x8DE6),
    ("DNG-move-commit.s", "DNG", 0x8956, 0x8EBE, 0x8ECE),
    ("DNG-map-access.s", "DNG", 0x8956, 0x9D32, 0x9D49),
    ("DNG-candidate-position.s", "DNG", 0x8956, 0xA432, 0xA449),
    ("DNG-map-write.s", "DNG", 0x8956, 0xA41F, 0xA432),
    ("DNG-monster-hp.s", "DNG", 0x8956, 0x9B05, 0x9B20),
    ("DNG-monster-hit-roll.s", "DNG", 0x8956, 0x9A37, 0x9A64),
    ("DNG-monster-damage-roll.s", "DNG", 0x8956, 0x9A95, 0x9ADC),
    ("DNG-stair-gate.s", "DNG", 0x8956, 0x9666, 0x9670),
    ("DNG-descend-entry.s", "DNG", 0x8956, 0x972C, 0x9732),
    ("DNG-ascend-regenerate.s", "DNG", 0x8956, 0x9728, 0x972C),
    ("DNG-exit-out.s", "DNG", 0x8956, 0x9716, 0x9728),
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
