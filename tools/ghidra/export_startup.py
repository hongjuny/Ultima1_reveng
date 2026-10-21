#!/usr/bin/env python3
"""Analyze intro code in its runtime locations in a private Ghidra project."""
import os
from pathlib import Path
import subprocess
import sys

from import_modules import ROOT, SCRIPT_DIR, analyzer

BUILD = ROOT / "build/macos-startup"
PROGRAMS = {"OUT": (0x8956, ROOT / "extracted/OUT"),
            "MI.U1": (0x7000, ROOT / "extracted/MI.U1"),
            "STUPH": (0x0800, ROOT / "extracted/STUPH"),
            "GEN": (0x8956, ROOT / "extracted/GEN"),
            "U1.INTRO": (0x0800, ROOT / "extracted/U1.INTRO"),
            "MAKE.INDATA": (0x1E00, ROOT / "extracted/MAKE.INDATA"),
            "INTRO.RELOC": (0x8700, BUILD / "INTRO.RELOC")}
# MAKE.INDATA $1F17 copies $2000-$27FF to $8700-$8EFF before executing it.
SEEDS = {"GEN": (0x8CFA, 0x8E12),
         "INTRO.RELOC": (0x8700, 0x8748),
         "U1.INTRO": (0x0ACA, 0x0B08, 0x0DFD, 0x0E00, 0x0E03, 0x0E7E,
                       0x10EB, 0x110D, 0x1112),
         "MAKE.INDATA": ()}


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    support = (ROOT / "extracted/MAKE.INDATA").read_bytes()
    PROGRAMS["INTRO.RELOC"][1].write_bytes(support[0x200:0xA00])
    manifest = BUILD / "startup-entrypoints.tsv"
    manifest.write_text("".join(f"{name}\t{pc:04X}\n" for name, seeds in SEEDS.items()
                                for pc in seeds))
    env = os.environ.copy()
    env["JAVA_TOOL_OPTIONS"] = f"-Duser.home={ROOT / 'build/ghidra-home'}"
    for name in sys.argv[1:] or PROGRAMS:
        base, source = PROGRAMS[name]
        command = [str(analyzer()), str(BUILD), "Startup", "-import", str(source),
                   "-loader", "BinaryLoader", "-loader-baseAddr", f"0x{base:04X}",
                   "-processor", "6502:LE:16:default", "-scriptPath", str(SCRIPT_DIR),
                   "-preScript", "SeedUltimaEntrypoints.java", str(manifest),
                   "-postScript", "ExportUltimaInstructions.java",
                   str(BUILD / f"{name}-instructions.tsv")]
        if name == "U1.INTRO":
            command += ["-postScript", "ExportUltimaAlternateEntries.java",
                        str(BUILD / "U1.INTRO-alternates.tsv"), "0D9B", "0D9E"]
        if name in ("GEN", "MI.U1", "STUPH", "OUT"):
            command += ["-postScript", "ExportUltimaRuntimeCandidates.java",
                        str(BUILD / f"{name}-runtime.tsv"), f"{base:04X}",
                        f"{base + source.stat().st_size:04X}"]
        command += ["-overwrite"]
        with (BUILD / f"{name}-ghidra.log").open("w") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"Ghidra startup analysis failed: {name}")
        print(f"{name}: private Ghidra startup listing ready", flush=True)


if __name__ == "__main__":
    main()
