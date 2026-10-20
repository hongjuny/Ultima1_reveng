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
