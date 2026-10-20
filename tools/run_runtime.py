#!/usr/bin/env python3
"""Build the socketpair a2m variant and run one or more private traces."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

from build_socketpair_a2m import main as build_emulator
from disassemble import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scripts", nargs="+", metavar="TRACE",
                        help="trace script name under tools/, or a path inside the repo")
    parser.add_argument("--no-check", action="store_true",
                        help="skip tools/check_all.py after the traces")
    args = parser.parse_args()
    build_emulator()
    environment = os.environ.copy()
    environment["ULTIMA_A2M_SOCKETPAIR"] = "1"
    for name in args.scripts:
        candidate = Path(name)
        script = (ROOT / "tools" / candidate) if len(candidate.parts) == 1 else (ROOT / candidate)
        script = script.resolve()
        if ROOT not in script.parents or script.parent != ROOT / "tools" or not script.is_file():
            raise ValueError(f"trace script must be a file under tools/: {name}")
        print(f"\n[runtime] {script.name}", flush=True)
        result = subprocess.run([sys.executable, str(script)], cwd=ROOT,
                                env=environment)
        if result.returncode:
            return result.returncode
    if not args.no_check:
        print("\n[checks] tools/check_all.py", flush=True)
        return subprocess.run([sys.executable, "tools/check_all.py"], cwd=ROOT).returncode
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"runtime batch failed: {error}", file=sys.stderr)
        raise SystemExit(1)
