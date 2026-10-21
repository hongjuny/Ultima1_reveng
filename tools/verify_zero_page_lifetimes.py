#!/usr/bin/env python3
"""Check zero-page and local-coordinate lifetime across three overlay entries."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
CASES = (
    ("out-to-cas", "cas-first-input", (0x1E, 0x1F), (0, 9)),
    ("out-to-twn", "twn-first-input", (0x1D, 0x20), (19, 17)),
    ("out-to-dng", "dng-first-input", (43, 15), (43, 15)),
)


def checked(snapshot):
    path = Path(snapshot["path"])
    require(describe(path) == {"size": snapshot["size"],
                               "sha256": snapshot["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not (TRACE / "dng-first-input/handoff.json").is_file():
        print("PENDING zero-page overlay lifetime comparison")
        return 0
    for before_name, after_name, outdoor, local in CASES:
        before_report = json.loads((TRACE / before_name / "handoff.json").read_text())
        after_report = json.loads((TRACE / after_name / "handoff.json").read_text())
        require(after_report["source_snapshot"] == before_report["snapshot"],
                f"{after_name} does not continue from {before_name}")
        before, after = checked(before_report["snapshot"]), checked(after_report["snapshot"])
        require(tuple(before[0:2]) == outdoor and tuple(after[0:2]) == local and
                tuple(after[0x7E73:0x7E75]) == outdoor,
                f"{after_name}: $00/$01 or saved outdoor coordinates differ")
        if after_name == "dng-first-input":
            require(before[0xA4E8:0xA4EA] == bytes((0, 0)) and
                    after[0xA4E8:0xA4EA] == bytes((1, 1)),
                    "DNG local coordinates do not move into $A4E8/$A4E9")
        else:
            require(tuple(after[0x0C:0x0E]) == outdoor,
                    f"{after_name}: $0C/$0D no longer retain entry coordinates")
        print(f"{after_name}: $00/$01 {outdoor} -> {local}; "
              "$7E73/$7E74 preserve outdoor position")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"zero-page lifetime verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
