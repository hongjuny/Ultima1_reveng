#!/usr/bin/env python3
"""Probe the four RAM bytes copied beyond the final TCMAPS record."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-to-cas/handoff.json"
OUTPUT = ROOT / "build/traces/tcmaps-last-slot"
FILE_END = 0x5DEC


def trial(emulator, disk, source, slot, output):
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    state_path = output / f"slot-{slot}.a2state"
    state_path.unlink(missing_ok=True)
    with (output / f"slot-{slot}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x8956:
                    raise RuntimeError("restored CAS entry differs")
                original_slot = client.mem(0x7EED, 1)[0]
                if slot != original_slot:
                    client.set_mem(0x7EED, bytes([slot]))
                client.ok("set-turbo 8")
                pre_tail = client.mem(FILE_END, 4).hex()
                points = [wait_at(client, "TCMAPS request", (0x898D,)),
                          wait_at(client, "MAPCHARS request", (0x89A3,))]
                loaded_tail = client.mem(FILE_END, 4).hex()
                maps = (ROOT / "extracted/TCMAPS").read_bytes()
                if client.mem(0x4000, len(maps)) != maps:
                    raise RuntimeError("TCMAPS load differs")
                points.append(wait_at(client, "map copy", (0x89CE,)))
                source_address = int.from_bytes(client.mem(0x89CF, 2), "little")
                source_window = client.mem(source_address, 768)
                points.append(wait_at(client, "after map copy", (0x89E0,)))
                copied = client.mem(0xB400, 768)
                if copied != source_window:
                    raise RuntimeError("CAS copied map differs from source window")
                client.ok(f"save-state {state_path}")
                wait_for_snapshot(state_path)
                time.sleep(0.2)
                return {"slot": slot, "original_slot": original_slot,
                        "intervention": None if slot == original_slot else
                        {"address": "0x7EED", "value": slot},
                        "pre_load_tail": pre_tail, "loaded_tail": loaded_tail,
                        "copied_tail": copied[-4:].hex(),
                        "source_address": f"0x{source_address:04X}",
                        "source_file_bytes": min(768, FILE_END-source_address),
                        "checkpoints": points, "final_cpu": client.ok("get-cpu"),
                        "snapshot": {"path": str(state_path), **describe(state_path)}}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x8956:
        raise RuntimeError("source is not CAS entry")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trials = {name: trial(emulator, Path(disk_item["path"]), source, slot, OUTPUT)
              for name, slot in (("ordinary", 0), ("last", 9))}
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "trials": trials}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, result in trials.items():
        print(f"{name}: source {result['source_address']} file bytes "
              f"{result['source_file_bytes']}; RAM tail "
              f"{result['pre_load_tail']}→{result['loaded_tail']}; "
              f"copied tail {result['copied_tail']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TCMAPS final-slot trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
