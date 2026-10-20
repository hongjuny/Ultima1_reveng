#!/usr/bin/env python3
"""Force one guard miss by changing only the private RNG seed byte."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-attack-effect" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-guard-miss"


def next_random(initial: bytes) -> int:
    state = bytearray(initial)
    accumulator = state[15]
    carry = 0
    for index in range(14, -1, -1):
        value = accumulator + state[index] + carry
        accumulator, carry = value & 0xFF, value >> 8
        state[index] = accumulator
    state[0] = (state[15] + state[0]) & 0xFF
    for index in range(15, -1, -1):
        state[index] = (state[index] + 1) & 0xFF
        if state[index]:
            break
    return state[0]


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["handler_return_snapshot"]
    if prior["timeout"] is not None or source is None:
        raise RuntimeError("handler return snapshot unavailable")
    disk_item = prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"guard-miss.pending-{os.getpid()}.a2state"
    pre_rng_pending = OUTPUT / f"before-rng.pending-{os.getpid()}.a2state"
    post_rng_pending = OUTPUT / f"after-rng.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    pre_rng_pending.unlink(missing_ok=True)
    post_rng_pending.unlink(missing_ok=True)
    points = []
    timeout = None
    state, chosen, original, predicted, threshold = bytes(16), None, None, None, None
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A59:
                    raise RuntimeError("restored handler return differs")
                before = {"player_hp": list(client.mem(0x7EC6, 2)),
                          "actor_hp": [client.mem(0xB6DE, 1)[0],
                                       client.mem(0xB6EE, 1)[0]]}
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "guard RNG call", (0x997A,)))
                    threshold = client.mem(0x72, 1)[0]
                    state = client.mem(0x1E18, 16)
                    client.ok(f"save-state {pre_rng_pending}")
                    wait_for_snapshot(pre_rng_pending)
                    original = next_random(state)
                    if original != 0x9D or threshold != 0x45:
                        raise RuntimeError("original guard roll differs")
                    chosen = next((seed for seed in range(256)
                                   if seed != state[15] and
                                   0 < next_random(state[:15] + bytes((seed,))) < threshold), None)
                    if chosen is None:
                        raise RuntimeError("no one-byte RNG seed yields a miss")
                    predicted = next_random(state[:15] + bytes((chosen,)))
                    client.set_mem(0x1E27, bytes((chosen,)))
                    if client.mem(0x1E27, 1)[0] != chosen:
                        raise RuntimeError("private RNG change failed")
                    client.ok(f"save-state {post_rng_pending}")
                    wait_for_snapshot(post_rng_pending)
                    points.append(wait_at(client, "guard miss branch", (0x9981, 0x998F)))
                    if points[-1]["pc"] != "0x9981":
                        raise RuntimeError("controlled seed did not select guard miss")
                    points.append(wait_at(client, "next key poll", (0x8A27,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS guard miss stopped: {timeout}", flush=True)
                after = {"player_hp": list(client.mem(0x7EC6, 2)),
                         "actor_hp": [client.mem(0xB6DE, 1)[0],
                                      client.mem(0xB6EE, 1)[0]],
                         "position": list(client.mem(0, 2)),
                         "turn": [client.mem(a, 1)[0] for a in (0x7EE4, 0x7EDA)]}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "miss.a2state"
    pending.replace(final)
    private_states = None
    if timeout is None:
        pre_rng = OUTPUT / "before-rng.a2state"
        post_rng = OUTPUT / "after-rng.a2state"
        pre_rng_pending.replace(pre_rng)
        post_rng_pending.replace(post_rng)
        private_states = {"before": {"path": str(pre_rng), **describe(pre_rng)},
                          "after": {"path": str(post_rng), **describe(post_rng)}}
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "controlled_change": {"address": "0x1E27", "before": state[15],
                                    "after": chosen, "original_roll": original,
                                    "predicted_roll": predicted, "threshold": threshold},
              "rng_state_before": list(state), "intervention_snapshots": private_states,
              "checkpoints": points, "timeout": timeout,
              "before": before, "after": after, "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"guard miss: seed ${state[15]:02X}→${chosen:02X}, "
          f"roll ${original:02X}→${predicted:02X}, threshold ${threshold:02X}")
    print(f"state: {before} → {after}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS guard miss failed: {error}", file=sys.stderr)
        raise SystemExit(1)
