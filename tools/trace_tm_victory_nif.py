#!/usr/bin/env python3
"""Follow the controlled TM victory branch into its NIF file request."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-attack-direction-control/handoff.json"
OUTPUT = ROOT / "build/traces/tm-victory-nif"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9034:
        raise RuntimeError("source is not at TM victory branch")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "after-nif.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9034:
                    raise RuntimeError("restored TM victory differs")
                client.ok("set-turbo 8")
                points = [wait_at(client, "NIF file request", (0x9052,)),
                          wait_at(client, "NIF loader", (0xB703,)),
                          wait_at(client, "NIF load return", (0x9059,))]
                memory = client.mem(0x4000, 7680)
                expected = (ROOT / "extracted/NIF").read_bytes()
                match = memory == expected
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "checkpoints": points, "nif_match": match,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM victory NIF: loaded={match}; {[p['pc'] for p in points]}", flush=True)
    if not match:
        raise RuntimeError("NIF memory differs from extracted file")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM victory NIF trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
