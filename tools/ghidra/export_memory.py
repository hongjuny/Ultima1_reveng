#!/usr/bin/env python3
"""Refresh zero-page/player references and code/data candidates in private Ghidra exports."""

import os
from pathlib import Path
import subprocess
import sys

from import_modules import BUILD, MODULES, ROOT, SCRIPT_DIR, analyzer


def main():
    if not (BUILD / "UltimaI.gpr").is_file():
        raise FileNotFoundError("private Ghidra project missing; run import_modules.py")
    env = os.environ.copy()
    env["JAVA_TOOL_OPTIONS"] = (
        env.get("JAVA_TOOL_OPTIONS", "") +
        f" -Duser.home={ROOT / 'build/ghidra-home'}"
    ).strip()
    for name in sys.argv[1:] or MODULES:
        if name not in MODULES:
            raise ValueError(f"unknown module: {name}")
        output = BUILD / f"{name}-memory.tsv"
        log = BUILD / f"{name}-memory.log"
        command = [str(analyzer()), str(BUILD), "UltimaI",
                   "-process", name, "-scriptPath", str(SCRIPT_DIR),
                   "-postScript", "ExportUltimaMemory.java", str(output),
                   "-readOnly", "-max-cpu", "2"]
        with log.open("w") as stream:
            result = subprocess.run(command, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, check=False)
        if result.returncode or not output.is_file():
            raise RuntimeError(f"memory export failed for {name}; inspect {log}")
        rows = output.read_text().splitlines()
        zp = sum(row.startswith("zp\t") for row in rows)
        player = sum(row.startswith("player\t") for row in rows)
        spans = sum(row.startswith("span\t") for row in rows)
        print(f"{name}: {zp} zero-page, {player} player-record references, "
              f"{spans} classification spans", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
