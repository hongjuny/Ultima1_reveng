#!/usr/bin/env python3
"""Follow the finale's 8 KiB NIF move and source clearing."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-victory-nif/handoff.json"
OUTPUT = ROOT / "build/traces/tm-nif-copy"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9059:
        raise RuntimeError("source is not at NIF loader return")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "after-copy.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9059:
                    raise RuntimeError("restored NIF return differs")
                before_source = client.mem(0x4000, 8192)
                before_target = client.mem(0x6000, 8192)
                client.ok("set-turbo 8")
                points = [wait_at(client, "NIF copy start", (0x9073,)),
                          wait_at(client, "NIF copy complete", (0x9094,))]
                after_target = client.mem(0x6000, 8192)
                after_source = client.mem(0x4000, 8192)
                result = {"file_payload_match": before_source[:7680] ==
                          (ROOT / "extracted/NIF").read_bytes(),
                          "full_8192_copy_match": after_target == before_source,
                          "source_cleared": after_source == bytes(8192),
                          "tail_512_nonzero": sum(value != 0 for value in before_source[7680:]),
                          "prior_target_changed_bytes": sum(a != b for a, b in
                                                            zip(before_target, after_target))}
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "checkpoints": points, "result": result,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM NIF copy: {result}", flush=True)
    if not all(result[key] for key in
               ("file_payload_match", "full_8192_copy_match", "source_cleared")):
        raise RuntimeError("TM NIF copy mismatch")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF copy failed: {error}", file=sys.stderr)
        raise SystemExit(1)
