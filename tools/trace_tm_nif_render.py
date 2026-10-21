#!/usr/bin/env python3
"""Trace the first and final rows consumed by TM's packed NIF animation."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-nif-copy/handoff.json"
OUTPUT = ROOT / "build/traces/tm-nif-render"


def word(client, address):
    return int.from_bytes(client.mem(address, 2), "little")


def hgr_offset(row):
    return ((row & 7) << 10) | (((row >> 3) & 7) << 7) | ((row >> 6) * 40)


def page_match(page, packed):
    count = 0
    matching_rows = 0
    for row in range(192):
        actual = page[hgr_offset(row):hgr_offset(row) + 40]
        expected = packed[row * 40:(row + 1) * 40]
        count += sum(a == b for a, b in zip(actual, expected))
        matching_rows += actual == expected
    return {"matching_bytes": count, "matching_rows": matching_rows}


def main():
    prior = json.loads(SOURCE.read_text())
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9094:
        raise RuntimeError("source is not at NIF copy completion")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9094:
                    raise RuntimeError("restored NIF PC differs")
                packed = client.mem(0x6000, 7680)
                if packed != (ROOT / "extracted/NIF").read_bytes():
                    raise RuntimeError("NIF packed buffer mismatch")
                client.ok("set-turbo 8")
                points = [wait_at(client, "NIF animation entry", (0x90AA,)),
                          wait_at(client, "first packed row copy", (0x90E7,))]
                first_source = word(client, 0x90E8)
                first_target = word(client, 0x90EB)
                first_row = client.mem(first_source, 40)
                target_before = client.mem(first_target, 40)
                points.append(wait_at(client, "first row copied", (0x90FE,)))
                target_after = client.mem(first_target, 40)
                points.append(wait_at(client, "second packed row copy", (0x90E7,)))
                second_source = word(client, 0x90E8)
                second_target = word(client, 0x90EB)
                points.append(wait_at(client, "192 rows consumed", (0x9108,)))
                consumed_source = word(client, 0x90E8)
                consumed_count = client.mem(0x006D, 1)[0]
                points.append(wait_at(client, "final key wait", (0x9132,)))
                final_source = word(client, 0x90E8)
                final_pages = {
                    "page1": page_match(client.mem(0x2000, 8192), packed),
                    "page2": page_match(client.mem(0x4000, 8192), packed),
                }
                report = {
                    "source_snapshot": source, "working_game_disk": disk_item,
                    "points": points,
                    "first_source": f"${first_source:04X}",
                    "first_target": f"${first_target:04X}",
                    "first_matches_nif": first_row == packed[:40],
                    "first_target_changed": target_before != target_after,
                    "first_target_matches": target_after == first_row,
                    "second_source": f"${second_source:04X}",
                    "second_target": f"${second_target:04X}",
                    "consumed_source": f"${consumed_source:04X}",
                    "consumed_count": consumed_count,
                    "final_source": f"${final_source:04X}",
                    "final_pages": final_pages,
                    "nif_sha256": hashlib.sha256(packed).hexdigest(),
                    "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("NIF first row", report["first_source"], "→", report["first_target"],
          "match", report["first_target_matches"])
    print("NIF second source", report["second_source"],
          "192-row end", report["consumed_source"],
          "final-reset source", report["final_source"])
    print("final HGR page matches:", report["final_pages"])
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF render trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
