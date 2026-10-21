#!/usr/bin/env python3
"""Controlled selector probes for SPA/TM; does not claim a gameplay route."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/overlay-loop-probes"
CASES = {"SPA": (0x14, 0x8A53, 0x8A5F), "TM": (0x18, 0x8E5E, 0x9815)}


def probe(name, selector, loop, input_pc, source, disk, emulator, Ctl,
          bypass_entry=False):
    checkpoints = []
    with (OUTPUT / f"{name.lower()}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("OUT source PC differs")
                client.ok("set-turbo 8")
                client.ok("set-reg sp $FF")
                client.ok(f"set-reg a ${selector:02X}")
                client.ok("set-reg pc $88FD")
                checkpoints.append(wait_at(client, f"{name} entry", (0x8956,)))
                expected = (ROOT / "extracted" / name).read_bytes()
                actual = client.mem(0x8956, len(expected))
                if actual != expected:
                    first = next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), None)
                    raise RuntimeError(f"{name}: loaded bytes differ at {first}")
                if bypass_entry:
                    client.ok(f"set-reg pc ${loop:04X}")
                    checkpoints.append({"label": f"{name} loop (PC injected)",
                                        "pc": f"0x{loop:04X}", "cpu": client.ok("get-cpu")})
                else:
                    checkpoints.append(wait_at(client, f"{name} loop", (loop,)))
                checkpoints.append(wait_at(client, f"{name} input", (input_pc,)))
                final = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    return {"selector": f"${selector:02X}", "source_pc": "$8A6C",
            "method": "set A and PC at common selector; SP reset to $FF"
                      + ("; bypass entry with PC set to loop" if bypass_entry else ""),
            "loaded_bytes": len(expected), "checkpoints": checkpoints, "final_cpu": final}


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source is not OUT poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, config in CASES.items():
        try:
            result[name] = probe(name, *config, snapshot, disk, emulator, Ctl,
                                 bypass_entry=name == "TM")
        except (OSError, RuntimeError, ValueError) as error:
            result[name] = {"error": str(error)}
            print(f"{name}: {error}", flush=True)
    path = OUTPUT / "probes.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"private report: {path}")
    return 0 if all("error" not in value for value in result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
