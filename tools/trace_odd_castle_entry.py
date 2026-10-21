#!/usr/bin/env python3
"""Enter the second mapped castle after the ordinary outdoor walking route."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_cas_first_input import main as castle_first_input
from trace_out_enter_04 import main as outdoor_enter
from trace_out_to_cas import main as castle_load
from verify_intro_support import main_ram


OUTPUT = ROOT / "build/traces/odd-castle-entry"


def main():
    source = ROOT / "build/traces/out-odd-castle-route/step-38/handoff.json"
    enter = OUTPUT / "enter"
    load = OUTPUT / "load"
    poll = OUTPUT / "poll"
    if outdoor_enter(source, enter, expected_coords=bytes((22, 20))):
        raise RuntimeError("odd castle E transition failed")
    if castle_load(enter / "handoff.json", load):
        raise RuntimeError("odd castle overlay load failed")
    if castle_first_input(load / "handoff.json", poll):
        raise RuntimeError("odd castle first input failed")
    report = json.loads((poll / "handoff.json").read_text())
    ram = main_ram(Path(report["snapshot"]["path"]))
    state = {"castle_index": ram[0x9E3B], "world_location": ram[0x7EED],
             "group": ram[0x7E6F], "position": list(ram[:2]),
             "quest": list(ram[0x7EA9:0x7EB1])}
    if state != {"castle_index": 1, "world_location": 1, "group": 0,
                 "position": [0, 9], "quest": [0] * 8}:
        raise RuntimeError(f"unexpected second castle state: {state}")
    (OUTPUT / "route.json").write_text(json.dumps({"source_report": str(source),
                                                    "enter_report": str(enter / "handoff.json"),
                                                    "load_report": str(load / "handoff.json"),
                                                    "poll_report": str(poll / "handoff.json"),
                                                    "state": state}, indent=2) + "\n")
    print(f"second castle state: {state}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd castle entry trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
