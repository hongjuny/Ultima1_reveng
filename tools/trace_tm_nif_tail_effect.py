#!/usr/bin/env python3
"""Compare finale video memory with the NIF overread tail intact or cleared."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-victory-nif/handoff.json"
OUTPUT = ROOT / "build/traces/tm-nif-tail-effect"


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
    trials = {}
    for label, clear in (("intact", False), ("tail-cleared", True)):
        out = OUTPUT / label
        out.mkdir(parents=True, exist_ok=True)
        final = out / "final-wait.a2state"
        final.unlink(missing_ok=True)
        with (out / "a2m.log").open("w") as log:
            process = launch(emulator, Path(disk_item["path"]), None, log)
            try:
                client = connect(Ctl, process)
                try:
                    client.ok("hello")
                    client.ok("wait-paused 3000")
                    client.ok(f"load-state {source['path']}")
                    if cpu_pc(client.ok("get-cpu")) != 0x9059:
                        raise RuntimeError("restored TM finale differs")
                    tail = client.mem(0x5E00, 512)
                    if clear:
                        client.set_mem(0x5E00, bytes(512))
                    client.ok("set-turbo 8")
                    points = []
                    stages = {}
                    for name, address in (("after_move", 0x9094),
                                          ("animation", 0x90AA),
                                          ("final_wait", 0x9132)):
                        points.append(wait_at(client, name, (address,)))
                        stages[name] = {f"page_{page:04X}": client.mem(page, 8192)
                                        for page in (0x2000, 0x4000, 0x6000)}
                    client.ok(f"save-state {final}")
                    wait_for_snapshot(final)
                    time.sleep(0.2)
                    trials[label] = {"tail_nonzero": sum(value != 0 for value in tail),
                                     "checkpoints": points, "stages": stages,
                                     "snapshot": {"path": str(final), **describe(final)},
                                     "final_cpu": client.ok("get-cpu")}
                finally:
                    client.s.close()
            finally:
                stop(process)
    comparisons = {}
    for stage in ("after_move", "animation", "final_wait"):
        comparisons[stage] = {
            page: sum(a != b for a, b in zip(trials["intact"]["stages"][stage][page],
                                              trials["tail-cleared"]["stages"][stage][page]))
            for page in ("page_2000", "page_4000", "page_6000")}
    for trial in trials.values():
        del trial["stages"]
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "intervention": {"address": "0x5E00", "length": 512,
                               "tail_cleared_only_in": "tail-cleared"},
              "trials": trials, "differing_bytes": comparisons}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM NIF tail effect: {comparisons}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF tail comparison failed: {error}", file=sys.stderr)
        raise SystemExit(1)
