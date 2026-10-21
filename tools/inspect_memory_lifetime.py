#!/usr/bin/env python3
"""Measure resident regions across reached gameplay overlay snapshots."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT


PHASES = ("out-first-input", "cas-first-input", "twn-first-input", "dng-first-input")
OUTPUT = ROOT / "build/traces/memory-lifetime"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def matching(a, b):
    return sum(x == y for x, y in zip(a, b))


def main():
    reports = {name: json.loads((ROOT / "build/traces" / name / "handoff.json").read_text())
               for name in PHASES}
    disk_item = reports[PHASES[0]]["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working disk differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stuph = (ROOT / "extracted/STUPH").read_bytes()
    engine = (ROOT / "extracted/MI.U1").read_bytes()[:0x1956]
    result = {}
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                for phase, report in reports.items():
                    item = report["snapshot"]
                    path = Path(item["path"])
                    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
                        raise RuntimeError(f"{phase}: snapshot differs")
                    client.ok(f"load-state {path}")
                    overlay = phase.split("-")[0].upper()
                    payload = (ROOT / "extracted" / overlay).read_bytes()
                    live_overlay = client.mem(0x8956, len(payload))
                    live_engine = client.mem(0x7000, len(engine))
                    live_stuph = client.mem(0x0800, len(stuph))
                    result[overlay] = {
                        "snapshot_sha256": item["sha256"], "cpu": client.ok("get-cpu"),
                        "overlay": {"base": "$8956", "length": len(payload),
                                    "matching_bytes": matching(live_overlay, payload),
                                    "first_differences": [f"${0x8956+i:04X}" for i, (a, b) in
                                                          enumerate(zip(live_overlay, payload)) if a != b][:16]},
                        "engine": {"base": "$7000", "length": len(engine),
                                   "matching_bytes": matching(live_engine, engine),
                                   "first_differences": [f"${0x7000+i:04X}" for i, (a, b) in
                                                         enumerate(zip(live_engine, engine)) if a != b][:16]},
                        "stuph": {"base": "$0800", "length": len(stuph),
                                   "matching_bytes": matching(live_stuph, stuph)},
                        "regions_sha256": {
                            "$6000-$6FFF": digest(client.mem(0x6000, 0x1000)),
                            "$7E00-$8036": digest(client.mem(0x7E00, 0x237)),
                            "$B000-$B6FF": digest(client.mem(0xB000, 0x700)),
                        },
                    }
                    print(f"{overlay}: overlay {result[overlay]['overlay']['matching_bytes']}/{len(payload)}; "
                          f"engine {result[overlay]['engine']['matching_bytes']}/{len(engine)}", flush=True)
            finally:
                client.s.close()
        finally:
            stop(process)
    path = OUTPUT / "regions.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"private report: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"memory lifetime inspection failed: {error}", file=sys.stderr)
        raise SystemExit(1)
