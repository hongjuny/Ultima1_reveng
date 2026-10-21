#!/usr/bin/env python3
"""Walk east through the TM arena toward the gemstone."""

import contextlib
import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_tm_command import main as replay
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/tm-command/handoff.json"
OUTPUT = ROOT / "build/traces/tm-approach-gem"


def main():
    source = SOURCE
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for number, x in enumerate(range(6, 15), 1):
        action = OUTPUT / f"step-{number:02d}"
        action.mkdir(parents=True, exist_ok=True)
        with (action / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
            if replay(0x15, source, action):
                raise RuntimeError(f"TM east step {number} failed; see {action / 'trace.log'}")
        path = action / "handoff.json"
        step = json.loads(path.read_text())
        ram = main_ram(Path(step["snapshot"]["path"]))
        state = {"position": list(ram[:2]),
                 "hp": int.from_bytes(ram[0x7EC6:0x7EC8], "little"),
                 "gem_destroyed": ram[0x95AB],
                 "mondain_hp": int.from_bytes(ram[0x7EF4:0x7EF6], "little")}
        if state["position"] != [x, 5] or state["hp"] <= 0:
            raise RuntimeError(f"TM east step {number} differs: {state}")
        entries.append({"number": number, "source_report": str(source),
                        "result_report": str(path), **state})
        (OUTPUT / "route.json").write_text(json.dumps(entries, indent=2) + "\n")
        print(f"TM east {number}/9: {state}", flush=True)
        source = path


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM gem approach failed: {error}", file=sys.stderr)
        raise SystemExit(1)
