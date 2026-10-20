#!/usr/bin/env python3
"""Compare the saved player record across a controlled CAS death and OUT revival."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
PRIOR = TRACE / "cas-attack-effect" / "handoff.json"
DEATH = TRACE / "cas-guard-death" / "handoff.json"
OUT = TRACE / "cas-death-to-out" / "handoff.json"
FIRST = 0x7E6D
END = 0x8037  # exclusive; the 458-byte U1.VARS copy ends at $8036
EXPECTED = {
    0x7E7A: (0x01, 0x01, 0x00),
    0x7E7B: (0x01, 0x01, 0x00),
    0x7E84: (0x02, 0x02, 0x00),
    0x7EC6: (0x96, 0x00, 0x63),
    0x7ED4: (0x64, 0x00, 0x00),
    0x7EE5: (0xC3, 0x00, 0x63),
}


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "player-record snapshot differs")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (PRIOR, DEATH, OUT)):
        print("PENDING controlled death player-record comparison")
        return 0
    prior = json.loads(PRIOR.read_text())
    death = json.loads(DEATH.read_text())
    out = json.loads(OUT.read_text())
    require(death["source_snapshot"] == prior["handler_return_snapshot"] and
            out["source_snapshot"] == death["snapshot"] and
            death["controlled_change"] ==
            {"address": "0x7EC6", "before": 0x96, "after": 0x0A},
            "player-record trace ancestry differs")
    before = checked_ram(prior["handler_return_snapshot"])
    at_selector = checked_ram(death["snapshot"])
    after = checked_ram(out["snapshot"])
    actual = {address: (before[address], at_selector[address], after[address])
              for address in range(FIRST, END) if before[address] != after[address]}
    require(actual == EXPECTED, "player-record changes across resurrection differ")
    require(all(before[address] == at_selector[address] == after[address]
                for address in range(FIRST, END) if address not in EXPECTED),
            "unexpected intermediate change in player record")
    require(END - FIRST == 458 and
            before[0x7EC7] == at_selector[0x7EC7] == after[0x7EC7] == 0 and
            before[0x7ED5] == at_selector[0x7ED5] == after[0x7ED5] == 0 and
            before[0x7EE6] == at_selector[0x7EE6] == after[0x7EE6] == 0,
            "player-record extent or high bytes differ")
    print("controlled death → resurrection: 6 changed bytes in 458-byte player record")
    print("452 bytes retained; $7EC6/$7EE5 refill to $63; $7ED4 remains zero")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"resurrection record verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
