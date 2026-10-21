#!/usr/bin/env python3
"""Build private Ghidra 6502 programs and candidate call graphs for gameplay modules."""

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
BUILD = ROOT / "build/ghidra-project"
MODULES = {
    "U1.SYSTEM": 0x2000,
    "U1.INTRO": 0x0800,
    "MAKE.INDATA": 0x1E00,
    "MI.U1": 0x7000,
    "STUPH": 0x0800,
    "GEN": 0x8956,
    "OUT": 0x8956,
    "CAS": 0x8956,
    "TWN": 0x8956,
    "DNG": 0x8956,
    "SPA": 0x8956,
    "TM": 0x8956,
}


def analyzer():
    override = os.environ.get("ULTIMAI_GHIDRA_HOME")
    choices = ([Path(override)] if override else []) + [
        Path.home() / "Applications/ghidra_12.1.4_PUBLIC",
        Path("/Applications/ghidra_12.1.4_PUBLIC"),
    ]
    for home in choices:
        path = home / "support/analyzeHeadless"
        if path.is_file():
            return path
    raise FileNotFoundError("Ghidra analyzeHeadless missing; set ULTIMAI_GHIDRA_HOME")


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    user_home = ROOT / "build/ghidra-home"
    user_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["JAVA_TOOL_OPTIONS"] = (
        env.get("JAVA_TOOL_OPTIONS", "") + f" -Duser.home={user_home}"
    ).strip()
    selected = sys.argv[1:] or list(MODULES)
    for name in selected:
        if name not in MODULES:
            raise ValueError(f"unknown module: {name}")
        source = ROOT / "extracted" / name
        if not source.is_file():
            raise FileNotFoundError(source)
        output = BUILD / f"{name}-calls.tsv"
        log = BUILD / f"{name}-ghidra.log"
        command = [str(analyzer()), str(BUILD), "UltimaI",
                   "-import", str(source), "-loader", "BinaryLoader",
                   "-loader-baseAddr", f"0x{MODULES[name]:04X}",
                   "-processor", "6502:LE:16:default",
                   "-scriptPath", str(SCRIPT_DIR),
                   "-preScript", "SeedUltimaEntrypoints.java",
                   "-postScript", "ExportUltimaCalls.java", str(output),
                   "-analysisTimeoutPerFile", "120", "-max-cpu", "2",
                   "-overwrite"]
        with log.open("w") as stream:
            result = subprocess.run(command, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, check=False)
        if result.returncode or not output.is_file():
            raise RuntimeError(f"Ghidra import failed for {name}; inspect {log}")
        rows = output.read_text().splitlines()
        functions = sum(row.startswith("function\t") for row in rows)
        calls = sum(row.startswith("call\t") for row in rows)
        print(f"{name}: {functions} candidate functions, {calls} direct calls", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
