#!/usr/bin/env python3
"""Exercise GEN's upper bound, point-pool gate, and race-menu handoff."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc


SOURCE = ROOT / "build" / "traces" / "gen-attribute-controls" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-attribute-completion"


def wait_for(client, label: str, expected: tuple[int, ...]) -> str:
    try:
        client.ok("wait-paused 15000")
    except RuntimeError as error:
        try:
            client.ok("pause")
            client.ok("wait-paused 3000")
        except RuntimeError:
            pass
        raise RuntimeError(f"{label}: no breakpoint hit; "
                           f"{client.ok('get-cpu')}; {client.ok('get-state')}") from error
    cpu = client.ok("get-cpu")
    if cpu_pc(cpu) not in expected:
        raise RuntimeError(f"{label}: unexpected stop; {cpu}; {client.ok('get-state')}")
    return cpu


def read_state(client) -> dict:
    return {"attributes": list(client.mem(0x7EC8, 12)[::2]),
            "points": client.mem(0x903F, 1)[0],
            "selection": client.mem(0x9041, 1)[0]}


def press(client, key: int, targets: tuple[int, ...]) -> tuple[str, dict]:
    if cpu_pc(client.ok("get-cpu")) != 0x8C00:
        raise RuntimeError("key replay must start at the attribute loop")
    client.ok_or_data("break-clear-all")
    client.ok_or_data("break-exec $8C07")
    client.ok("run")
    wait_for(client, "attribute key read", (0x8C07,))
    client.ok_or_data("break-clear-all")
    for target in targets:
        client.ok_or_data(f"break-exec ${target:04X}")
    client.ok(f"key {key}")  # a2m resumes on key injection
    cpu = wait_for(client, f"key ${key:02X}", targets)
    return cpu, read_state(client)


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("attribute-controls snapshot differs from trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"race-menu.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    events = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8C00 or read_state(client) != {
                    "attributes": [10] * 6, "points": 30, "selection": 1
                }:
                    raise RuntimeError("unexpected initial attribute state")
                client.ok("set-turbo 8")

                for index in range(1, 16):
                    cpu, state = press(client, 0x15, (0x8C00,))
                    if state != {"attributes": [10 + index, 10, 10, 10, 10, 10],
                                  "points": 30 - index, "selection": 1}:
                        raise RuntimeError(f"first attribute increase {index} differs: {state}")
                    events.append({"key_code": 0x15, "pc": "0x8C00", **state})
                print(f"first attribute reached 25: {state}", flush=True)

                _, state = press(client, 0x15, (0x8C00,))
                if state != {"attributes": [25, 10, 10, 10, 10, 10],
                              "points": 15, "selection": 1}:
                    raise RuntimeError(f"attribute maximum did not hold: {state}")
                events.append({"key_code": 0x15, "pc": "0x8C00", **state})
                print(f"extra increase held at 25: {state}", flush=True)

                _, state = press(client, 0x20, (0x8C00, 0x8CD0))
                if cpu_pc(client.ok("get-cpu")) != 0x8C00 or state["points"] != 15:
                    raise RuntimeError(f"space advanced with unassigned points: {state}")
                events.append({"key_code": 0x20, "pc": "0x8C00", **state})
                print(f"space held with 15 points: {state}", flush=True)

                _, state = press(client, 0x2F, (0x8C00,))
                if state["selection"] != 2:
                    raise RuntimeError(f"second attribute not selected: {state}")
                events.append({"key_code": 0x2F, "pc": "0x8C00", **state})
                for index in range(1, 16):
                    _, state = press(client, 0x15, (0x8C00,))
                    if state != {"attributes": [25, 10 + index, 10, 10, 10, 10],
                                  "points": 15 - index, "selection": 2}:
                        raise RuntimeError(f"second attribute increase {index} differs: {state}")
                    events.append({"key_code": 0x15, "pc": "0x8C00", **state})
                print(f"all points assigned: {state}", flush=True)

                cpu, state = press(client, 0x20, (0x8C00, 0x8CD0))
                if cpu_pc(cpu) != 0x8CD0 or state["points"] != 0:
                    raise RuntimeError(f"space did not reach race choice: {cpu}; {state}")
                events.append({"key_code": 0x20, "pc": "0x8CD0", **state})
                print(f"race choice: {cpu}; {state}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "race-menu.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "events": events, "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN attribute completion trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
