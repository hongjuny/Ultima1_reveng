#!/usr/bin/env python3
"""Trace MI.U1's first STUPH and GEN loads from the private engine snapshot."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "intro-to-engine" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "engine-to-gen"


def check_image(client, address: int, name: str) -> None:
    expected = (ROOT / "extracted" / name).read_bytes()
    actual = client.mem(address, len(expected))
    if actual != expected:
        first = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
        raise RuntimeError(f"{name} differs at ${address + first:04X}: "
                           f"RAM=${actual[first]:02X}, file=${expected[first]:02X}")
    print(f"{name}: {len(expected)} bytes match at ${address:04X}", flush=True)


def main() -> int:
    source = json.loads(SOURCE.read_text())["engine_snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("engine snapshot differs from intro trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"gen-entry.pending-{os.getpid()}.a2state"
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
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8956:
                    raise RuntimeError(f"expected initial MI.U1 loader at $8956: {cpu}")
                check_image(client, 0x7000, "MI.U1")
                client.ok("set-turbo 8")
                points.append(wait_at(client, "STUPH request", (0x8975,)))
                points.append(wait_at(client, "STUPH loader entry", (0xB703,)))
                loaded = wait_at(client, "STUPH loader return", (0x897E,))
                points.append(loaded)
                if int(loaded["cpu"].split("p=")[1][:2], 16) & 1:
                    raise RuntimeError("STUPH loader returned with carry set")
                check_image(client, 0x0800, "STUPH")
                points.append(wait_at(client, "module selector", (0x88FD,)))
                selected = points[-1]
                if "a=00" not in selected["cpu"]:
                    raise RuntimeError(f"first module selector did not choose GEN: {selected['cpu']}")
                points.append(wait_at(client, "GEN request", (0x8907,)))
                points.append(wait_at(client, "GEN loader entry", (0xB703,)))
                loaded = wait_at(client, "GEN loader return", (0x890E,))
                points.append(loaded)
                if int(loaded["cpu"].split("p=")[1][:2], 16) & 1:
                    raise RuntimeError("GEN loader returned with carry set")
                check_image(client, 0x8956, "GEN")
                points.append(wait_at(client, "GEN entry", (0x8956,)))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "gen-entry.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "checkpoints": points,
              "resident_images": {"MI.U1": "$7000", "STUPH": "$0800", "GEN": "$8956"},
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, StopIteration) as error:
        print(f"engine-to-GEN trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
