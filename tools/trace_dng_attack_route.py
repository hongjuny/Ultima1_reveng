#!/usr/bin/env python3
"""Reproduce the four ordinary A attacks leading to a slot-1 kill."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_dng_after_up import main as next_poll
from trace_dng_key_w import main as key_action
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/dng-east-to-03-after-1/handoff.json"
OUTPUT = ROOT / "build/traces"


def actor_hp(report_path: Path):
    report = json.loads(report_path.read_text())
    ram = main_ram(Path(report["snapshot"]["path"]))
    return ram[0xA51B] + 256 * ram[0xA521]


def main() -> int:
    first = OUTPUT / "dng-attack-a"
    if key_action(65, first, SOURCE):
        return 1
    source = first / "handoff.json"
    print(f"first A handler: slot-1 HP {actor_hp(source)}", flush=True)
    for index in range(1, 4):
        stage = OUTPUT / f"dng-attack-repeat-{index}"
        if next_poll(source, stage / "poll"):
            return 1
        poll = stage / "poll/handoff.json"
        if key_action(65, stage / "key", poll):
            return 1
        source = stage / "key/handoff.json"
        print(f"repeat {index} A handler: slot-1 HP {actor_hp(source)}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG attack route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
