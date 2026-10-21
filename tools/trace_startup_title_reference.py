#!/usr/bin/env python3
"""Capture original title completion, collapsing only the nested delay loop."""
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc

OUTPUT = ROOT / "build/macos-startup/reference"


def main():
    prior = json.loads((ROOT / "build/traces/intro-to-engine/handoff.json").read_text())
    source = prior["prekey_snapshot"]
    disk = prior["boot_media"]
    for item in (source, disk):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise ValueError("reference source changed")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl, write_argb_png
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello"); client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x0B23:
                    raise ValueError("reference is not the first intro key poll")
                before = client.mem(0x0E23, 5)
                if before != bytes.fromhex("2c e8 c0 38 48"):
                    raise ValueError("delay bytes changed")
                # LDA #0; SEC; CLV; RTS has the delay's same no-key exit
                # register/flag state. Timing is explicitly excluded here.
                client.set_mem(0x0E23, bytes.fromhex("a9 00 38 b8 60"))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                condition = "mem($09DD)==$04,mem($09DF)==$88"
                client.ok_or_data(f"break-create exec $0B23 when={condition}")
                client.ok("run"); client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if (cpu_pc(cpu) != 0x0B23 or client.mem(0x09DD, 1) != b"\x04" or
                        client.mem(0x09DF, 1) != b"\x88"):
                    raise ValueError(f"title condition not reached: {cpu}")
                point = {"label": "original complete-title frame", "pc": "0x0B23",
                         "condition": condition, "cpu": cpu}
                print(point, flush=True)
                ram = client.mem(0, 65536, "main")
                (OUTPUT / "title.ram").write_bytes(ram)
                frame = client.get_frame()
                write_argb_png(str(OUTPUT / "title.png"), frame["width"], frame["height"],
                               frame["pixels"], stride=frame["stride"])
                report = {"source_snapshot": source, "boot_media": disk,
                          "intervention": {"address": 0x0E23, "before": before.hex(),
                                           "after": "a90038b860", "purpose": "delay only"},
                          "checkpoint": point,
                          "softswitches": client.get_softswitches(),
                          "ram": {"path": str(OUTPUT / "title.ram"),
                                  **describe(OUTPUT / "title.ram")}}
                (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
            finally:
                client.s.close()
        finally:
            stop(process)


if __name__ == "__main__":
    main()
