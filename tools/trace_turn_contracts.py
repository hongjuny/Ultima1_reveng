#!/usr/bin/env python3
"""Compare a complete Up-key turn in OUT and DNG from private poll snapshots."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build/traces/turn-contracts"
SCENARIOS = {
    "OUT": ("out-first-input", 0x8A6C, 0x8A74, 0x89CB, 0x89CE,
            0x89DC, 0x89DF, 0x8995, 0x89A1, 0x8A6C),
    "DNG": ("dng-first-input", 0x8DDA, 0x8DE4, 0x8DD4, 0x8DD7,
            0x8E0B, 0x8E0E, 0x8DE6, 0x8982, 0x8DDA),
    "CAS": ("cas-first-input", 0x8A27, 0x8A2F, 0x8A4A, None,
            0x8A56, 0x8A59, 0x8A31, None, 0x8A27),
    "TWN": ("twn-first-input", 0x8A1E, 0x8A26, 0x8A41, None,
            0x8A4D, 0x8A50, 0x8A28, None, 0x8A1E),
}


def diff(before: bytes, after: bytes, base: int) -> dict:
    addresses = [base + i for i, (old, new) in enumerate(zip(before, after)) if old != new]
    return {"count": len(addresses), "addresses": [f"${a:04X}" for a in addresses[:64]],
            "truncated": len(addresses) > 64,
            "before_sha256": hashlib.sha256(before).hexdigest(),
            "after_sha256": hashlib.sha256(after).hexdigest()}


def sample(client) -> dict:
    frame = client.get_frame()
    return {"player": client.mem(0x7E00, 0x200),
            "zero_page": client.mem(0x00, 0x80),
            "dungeon": client.mem(0xA4E8, 8),
            "video": client.mem(0x2000, 0x4000, "main"),
            "frame": {"number": frame["frame"],
                      "sha256": hashlib.sha256(frame["pixels"]).hexdigest()}}


def trace(name: str, config: tuple, emulator: Path, Ctl) -> dict:
    source_name, poll, key_return, lookup, decoded, handler_call, handler_return, loop, render, next_poll = config
    prior = json.loads((ROOT / "build/traces" / source_name / "handoff.json").read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != poll:
        raise RuntimeError(f"{name}: source does not stop at ${poll:04X}")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    points = []
    with (OUTPUT / f"{name.lower()}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != poll:
                    raise RuntimeError(f"{name}: restored PC differs")
                before = sample(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data(f"break-exec ${key_return:04X}")
                client.ok("key 11")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != key_return or int(cpu.split(" a=")[1][:2], 16) != 0x0B:
                    raise RuntimeError(f"{name}: key did not return: {cpu}")
                points.append({"label": "key return", "pc": f"${key_return:04X}", "cpu": cpu})
                for label, address in (("lookup", lookup), ("decoded", decoded),
                                       ("handler call", handler_call)):
                    if address is not None:
                        points.append(wait_at(client, f"{name} {label}", (address,)))
                target = int.from_bytes(client.mem(handler_call + 1, 2), "little")
                points.append(wait_at(client, f"{name} handler", (target,)))
                points.append(wait_at(client, f"{name} handler return", (handler_return,)))
                handled = sample(client)
                points.append(wait_at(client, f"{name} loop", (loop,)))
                if render is not None:
                    points.append(wait_at(client, f"{name} display", (render,)))
                points.append(wait_at(client, f"{name} next poll", (next_poll,)))
                completed = sample(client)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    return {"source_snapshot_sha256": source["sha256"], "key": 11,
            "checkpoints": points, "handler": f"${target:04X}",
            "after_handler": {"player": diff(before["player"], handled["player"], 0x7E00),
                              "zero_page": diff(before["zero_page"], handled["zero_page"], 0),
                              "dungeon": diff(before["dungeon"], handled["dungeon"], 0xA4E8),
                              "video": diff(before["video"], handled["video"], 0x2000),
                              "frame": handled["frame"]},
            "after_next_poll": {"player": diff(before["player"], completed["player"], 0x7E00),
                                "zero_page": diff(before["zero_page"], completed["zero_page"], 0),
                                "dungeon": diff(before["dungeon"], completed["dungeon"], 0xA4E8),
                                "video": diff(before["video"], completed["video"], 0x2000),
                                "frame": completed["frame"]},
            "initial_frame": before["frame"], "final_cpu": final_cpu}


def main() -> int:
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {name: trace(name, config, emulator, Ctl) for name, config in SCENARIOS.items()}
    path = OUTPUT / "comparison.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for name, item in report.items():
        print(f"{name}: handler={item['handler']} next={item['final_cpu']} "
              f"player changes={item['after_next_poll']['player']['count']} "
              f"video changes={item['after_next_poll']['video']['count']}")
    print(f"private report: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, IndexError) as error:
        print(f"turn comparison failed: {error}", file=sys.stderr)
        raise SystemExit(1)
