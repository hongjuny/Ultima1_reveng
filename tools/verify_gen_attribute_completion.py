#!/usr/bin/env python3
"""Verify GEN's upper bound, point gate, and race-menu snapshot."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-attribute-completion" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN attribute completion trace")
        return 0
    report = json.loads(REPORT.read_text())
    events = report["events"]
    require(len(events) == 34, "unexpected attribute-completion event count")
    for index in range(15):
        event = events[index]
        require(event["key_code"] == 0x15 and event["pc"] == "0x8C00" and
                event["attributes"] == [11 + index, 10, 10, 10, 10, 10] and
                event["points"] == 29 - index and event["selection"] == 1,
                f"first attribute increase {index + 1} differs")
    require(events[15]["key_code"] == 0x15 and
            events[15]["attributes"] == [25, 10, 10, 10, 10, 10] and
            events[15]["points"] == 15, "upper bound did not hold")
    require(events[16]["key_code"] == 0x20 and events[16]["pc"] == "0x8C00" and
            events[16]["points"] == 15, "space advanced with points remaining")
    require(events[17]["key_code"] == 0x2F and events[17]["selection"] == 2,
            "second attribute was not selected")
    for index in range(15):
        event = events[18 + index]
        require(event["key_code"] == 0x15 and event["pc"] == "0x8C00" and
                event["attributes"] == [25, 11 + index, 10, 10, 10, 10] and
                event["points"] == 14 - index and event["selection"] == 2,
                f"second attribute increase {index + 1} differs")
    final = events[33]
    require(final["key_code"] == 0x20 and final["pc"] == "0x8CD0" and
            final["attributes"] == [25, 25, 10, 10, 10, 10] and
            final["points"] == 0 and final["selection"] == 0,
            "race-menu handoff differs")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "attribute-completion snapshot differs from report")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require([ram[address] for address in range(0x7EC8, 0x7ED4, 2)] ==
            [25, 25, 10, 10, 10, 10] and ram[0x903F] == 0 and
            ram[0x9041] == 0, "race-menu RAM state differs")
    print("GEN maximum 25 held; space rejected with 15 points")
    print("GEN zero points: $8CD0 race input, attributes 25/25/10/10/10/10")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN attribute completion verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
