#!/usr/bin/env python3
"""Use outdoor Q to save a changed player record to a disposable disk."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/out-after-space/handoff.json"
PLAYER = ROOT / "build/traces/gen-player-save/handoff.json"
OUTPUT = ROOT / "build/traces/out-player-save"
START = 0x7E6D
LENGTH = 0x01CA


def extract(cp2, disk):
    with tempfile.TemporaryDirectory(dir=OUTPUT) as temporary:
        subprocess.run([cp2, "extract", f"--exdir={temporary}",
                        "--no-add-ext", str(disk), "U1.VARS"],
                       capture_output=True, text=True, check=True)
        return (Path(temporary) / "U1.VARS").read_bytes()


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    game_disk = prior["working_game_disk"]
    saved = json.loads(PLAYER.read_text())
    player_disk = saved["working_player_disk"]
    for item in (source, game_disk, player_disk):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source is not outdoor key poll")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    cp2 = manifest["extractor"]["path"]
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    working_player = OUTPUT / "player-working.po"
    shutil.copyfile(player_disk["path"], working_player)
    before_disk = describe(working_player)
    previous_file = extract(cp2, working_player)
    final = OUTPUT / "after-save.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(game_disk["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("restored outdoor poll differs")
                initial_record = client.mem(START, LENGTH)
                client.ok("unmount kind=diskii 6 0")
                client.ok(f"mount-disk 6 0 {working_player}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $92CA")
                client.ok("key 81")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x92CA:
                    raise RuntimeError("Q did not reach outdoor save handler")
                handler = {"pc": "0x92CA", "cpu": client.ok("get-cpu")}
                call = wait_at(client, "outdoor save call", (0x92D7,))
                record_at_call = client.mem(START, LENGTH)
                result = wait_at(client, "outdoor save return", (0x92E0, 0x92E5))
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    written = extract(cp2, working_player)
    ram = main_ram(final)
    if (len(written) != LENGTH or written != record_at_call or
            ram[START:START+LENGTH] != record_at_call):
        raise RuntimeError("outdoor save file does not match live player record")
    differences = [f"0x{START+i:04X}" for i, (a, b) in
                   enumerate(zip(previous_file, written)) if a != b]
    report = {"source_snapshot": source, "working_game_disk": game_disk,
              "previous_player_disk": player_disk,
              "working_player_disk": {"path": str(working_player),
                                      **describe(working_player)},
              "disk_before": before_disk,
              "input": 81, "handler": handler, "call": call, "result": result,
              "initial_record_sha256": hashlib.sha256(initial_record).hexdigest(),
              "record_at_call_sha256": hashlib.sha256(record_at_call).hexdigest(),
              "written_record_sha256": hashlib.sha256(written).hexdigest(),
              "changed_record_addresses": differences,
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"OUT Q save: {handler['pc']}→{call['pc']}→{result['pc']}; "
          f"{len(differences)} player-record bytes changed")
    print(differences)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError,
            subprocess.CalledProcessError) as error:
        print(f"OUT player-save trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
