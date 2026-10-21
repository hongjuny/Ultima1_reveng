#!/usr/bin/env python3
"""Return from the second king to the castle entrance with quest 1 active."""

import contextlib
import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_cas_step_right import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/odd-castle-after-quest/handoff.json"
OUTPUT = ROOT / "build/traces/odd-castle-exit-route"
PATH = [(25, y) for y in (7, 8, 9)] + [(x, 9) for x in range(24, -1, -1)]


def main():
    prior = json.loads(SOURCE.read_text())
    ram = main_ram(Path(prior["snapshot"]["path"]))
    if tuple(ram[:2]) != (25, 6) or ram[0x7EAA] != 1:
        raise RuntimeError("source is not the accepted second castle quest")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source, current, entries = SOURCE, (25, 6), []
    for number, destination in enumerate(PATH, 1):
        key = 0x0A if number <= 3 else 0x08
        action = OUTPUT / f"step-{number:02d}"
        action.mkdir(parents=True, exist_ok=True)
        with (action / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
            if replay(key, source, action):
                raise RuntimeError(f"castle exit step {number} failed; see {action / 'trace.log'}")
        report_path = action / "handoff.json"
        report = json.loads(report_path.read_text())
        reached = main_ram(Path(report["snapshot"]["path"]))
        actual = tuple(reached[:2])
        if cpu_pc(report["final_cpu"]) != 0x8A27 or actual != destination:
            raise RuntimeError(f"castle exit step {number}: expected {destination}, got {actual}")
        if reached[0x7EAA] != 1:
            raise RuntimeError(f"quest lost at castle exit step {number}")
        entries.append({"number": number, "key": key, "before": list(current),
                        "after": list(actual), "source_report": str(source),
                        "result_report": str(report_path), "hp": reached[0x7EC6]})
        (OUTPUT / "route.json").write_text(json.dumps(entries, indent=2) + "\n")
        print(f"{number:02d}/{len(PATH)} {current}→{actual} quest=1", flush=True)
        source, current = report_path, actual
    print(f"castle entrance reached at {current}; report {source}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd castle exit route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
