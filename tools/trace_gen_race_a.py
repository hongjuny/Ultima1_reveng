#!/usr/bin/env python3
"""Replay GEN race choice A and trace its attribute bonus."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "gen-attribute-completion" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-race-a"
KEY = 65


def read_attributes(client) -> list[int]:
    return list(client.mem(0x7EC8, 12)[::2])


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("race-menu snapshot differs from trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"class-menu.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8CD0 or read_attributes(client) != [
                    25, 25, 10, 10, 10, 10
                ]:
                    raise RuntimeError("snapshot is not at the expected race input")
                client.ok("set-turbo 8")
                # a2m's key command resumes execution, so arm before injection.
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8CFA")
                client.ok(f"key {KEY}")
                try:
                    client.ok("wait-paused 15000")
                except RuntimeError as error:
                    client.ok("pause")
                    client.ok("wait-paused 3000")
                    raise RuntimeError(f"race choice not accepted: "
                                       f"{client.ok('get-cpu')}; {client.ok('get-state')}") from error
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8CFA or client.mem(0x7ED6, 1)[0] != 1:
                    raise RuntimeError(f"race A did not reach bonus dispatch: {cpu}")
                print(f"race A selected: $8CFA {cpu}", flush=True)
                points.append({"label": "race A selected", "pc": "0x8CFA", "cpu": cpu,
                               "state": client.ok("get-state")})
                points.append(wait_at(client, "race bonus complete", (0x8D3C,)))
                if read_attributes(client) != [25, 25, 10, 10, 10, 15]:
                    raise RuntimeError(f"race A bonus differs: {read_attributes(client)}")
                print(f"race A attributes: {read_attributes(client)}", flush=True)
                points.append(wait_at(client, "class choice input", (0x8D72,)))
                if read_attributes(client) != [25, 25, 10, 10, 10, 15]:
                    raise RuntimeError("race attributes changed before class input")
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "class-menu.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "input": {"key_ascii": KEY, "at_pc": "0x8CD0"},
              "checkpoints": points, "attributes_after_bonus": [25, 25, 10, 10, 10, 15],
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN race-A trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
