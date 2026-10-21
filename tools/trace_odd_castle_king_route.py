#!/usr/bin/env python3
"""Walk from the second castle entrance to the king without editing RAM."""

import contextlib
import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_cas_step_right import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/odd-castle-entry/poll/handoff.json"
OUTPUT = ROOT / "build/traces/odd-castle-king-route"
PATH = [(x, 9) for x in range(1, 26)] + [(25, y) for y in (8, 7, 6)]


def main():
    prior = json.loads(SOURCE.read_text())
    ram = main_ram(Path(prior["snapshot"]["path"]))
    if tuple(ram[:2]) != (0, 9) or ram[0x9E3B] != 1:
        raise RuntimeError("source is not the second castle entrance")
    if ram[0xB400 + 6 * 38 + 25] != 0x6C:
        raise RuntimeError("king tile differs")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source, current, entries = SOURCE, (0, 9), []
    for number, destination in enumerate(PATH, 1):
        key = 0x15 if destination[0] > current[0] else 0x0B
        action = OUTPUT / f"step-{number:02d}"
        action.mkdir(parents=True, exist_ok=True)
        with (action / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
            if replay(key, source, action):
                raise RuntimeError(f"castle step {number} failed; see {action / 'trace.log'}")
        report_path = action / "handoff.json"
        report = json.loads(report_path.read_text())
        reached = main_ram(Path(report["snapshot"]["path"]))
        actual = tuple(reached[:2])
        if cpu_pc(report["final_cpu"]) != 0x8A27 or actual != destination:
            raise RuntimeError(f"castle step {number}: expected {destination}, got {actual}")
        item = {"number": number, "key": key, "before": list(current),
                "after": list(actual), "source_report": str(source),
                "result_report": str(report_path), "hp": reached[0x7EC6]}
        entries.append(item)
        (OUTPUT / "route.json").write_text(json.dumps(entries, indent=2) + "\n")
        print(f"{number:02d}/{len(PATH)} {current}→{actual} hp={item['hp']}", flush=True)
        source, current = report_path, actual
    print(f"king tile reached at {current}; report {source}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd castle king route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
