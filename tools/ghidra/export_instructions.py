#!/usr/bin/env python3
"""Export Ghidra's private instruction candidates and compare bytes with extraction."""

import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys

from import_modules import BUILD, MODULES, ROOT, SCRIPT_DIR, analyzer


def validate(name, output):
    sys.path.insert(0, str(ROOT / "tools"))
    from build_code_data_ledger import load_kinds
    from disassemble import FILES

    base, size, _ = FILES[name]
    payload = (ROOT / "extracted" / name).read_bytes()
    kinds = load_kinds(name, base, size)
    if len(payload) != size:
        raise ValueError(f"{name}: extraction size changed")
    occupied = set()
    count = 0
    with output.open(newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            start, end = int(row["address"], 16), int(row["end"], 16) + 1
            if row["program"] != name or not base <= start < end <= base + size:
                raise ValueError(f"{name}: candidate outside file at ${start:04X}")
            raw = bytes.fromhex(row["bytes"])
            if payload[start-base:end-base] != raw:
                raise ValueError(f"{name}: candidate bytes differ at ${start:04X}")
            for address in range(start, end):
                if address in occupied:
                    raise ValueError(f"{name}: overlapping candidates at ${address:04X}")
                if kinds[address-base] != "instruction":
                    raise ValueError(f"{name}: candidate is not an instruction in Ghidra memory export at ${address:04X}")
                occupied.add(address)
            count += 1
    expected = {base+offset for offset, kind in enumerate(kinds)
                if kind == "instruction"}
    if occupied != expected:
        missing = min(expected - occupied) if expected - occupied else None
        extra = min(occupied - expected) if occupied - expected else None
        raise ValueError(f"{name}: instruction listing differs from memory map; "
                         f"missing={missing} extra={extra}")
    print(f"{name}: {count} Ghidra instruction candidates, "
          f"{len(occupied)} bytes matched to extraction", flush=True)
    return count, len(occupied)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate existing private TSV exports without running Ghidra")
    parser.add_argument("modules", nargs="*", choices=MODULES)
    args = parser.parse_args()
    if not (BUILD / "UltimaI.gpr").is_file():
        raise FileNotFoundError("private Ghidra project missing; run import_modules.py")
    selected = args.modules or list(MODULES)
    if args.check:
        for name in selected:
            output = BUILD / f"{name}-instructions.tsv"
            if not output.is_file():
                raise FileNotFoundError(output)
            validate(name, output)
        return 0
    env = os.environ.copy()
    env["JAVA_TOOL_OPTIONS"] = (
        env.get("JAVA_TOOL_OPTIONS", "") +
        f" -Duser.home={ROOT / 'build/ghidra-home'}"
    ).strip()
    for name in selected:
        output = BUILD / f"{name}-instructions.tsv"
        log = BUILD / f"{name}-instructions.log"
        command = [str(analyzer()), str(BUILD), "UltimaI",
                   "-process", name, "-scriptPath", str(SCRIPT_DIR),
                   "-postScript", "ExportUltimaInstructions.java", str(output),
                   "-readOnly", "-max-cpu", "2"]
        with log.open("w") as stream:
            result = subprocess.run(command, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, check=False)
        if result.returncode or not output.is_file():
            raise RuntimeError(f"Ghidra instruction export failed for {name}; inspect {log}")
        validate(name, output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
