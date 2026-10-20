#!/usr/bin/env python3
"""Run the available local extraction, assembly, and data checks."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    ("baseline", ["tools/baseline.py", "verify"]),
    ("disk extraction", ["tools/verify_disk.py"]),
    ("file sizes and addresses", ["tools/disassemble.py", "--check"]),
    ("reviewed assembly", ["tools/verify_disasm.py"]),
    ("TCMAPS records", ["tools/extract_data.py", "--check"]),
    ("intro support relocation", ["tools/verify_intro_support.py"]),
    ("intro-to-engine handoff", ["tools/verify_intro_to_engine.py"]),
    ("first gameplay overlay", ["tools/verify_engine_to_gen.py"]),
    ("GEN menu entry", ["tools/verify_gen_menu.py"]),
    ("GEN new-character choice", ["tools/verify_gen_new_character.py"]),
    ("GEN state initialization", ["tools/verify_gen_first_input.py"]),
    ("GEN first attribute increase", ["tools/verify_gen_attribute_increase.py"]),
    ("GEN attribute bounds and navigation", ["tools/verify_gen_attribute_controls.py"]),
    ("GEN attribute completion", ["tools/verify_gen_attribute_completion.py"]),
    ("GEN race A", ["tools/verify_gen_race_a.py"]),
    ("GEN sex A", ["tools/verify_gen_sex_a.py"]),
    ("GEN class A", ["tools/verify_gen_class_a.py"]),
    ("GEN name A", ["tools/verify_gen_name_a.py"]),
)


def main() -> int:
    for name, args in CHECKS:
        print(f"\n[{name}]", flush=True)
        result = subprocess.run([sys.executable, *args], cwd=ROOT)
        if result.returncode:
            print(f"FAILED {name} (exit {result.returncode})", file=sys.stderr)
            return result.returncode
    print("\nAll available local checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
