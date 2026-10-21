#!/usr/bin/env python3
"""Verify outdoor Q persistence and GEN B restoration of changed state."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from baseline import MANIFEST, describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
START = 0x7E6D
LENGTH = 0x01CA


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private player-save artifact changed: {path}")
    return path


def extract(cp2, disk):
    with tempfile.TemporaryDirectory(dir=ROOT / "build") as temporary:
        subprocess.run([cp2, "extract", f"--exdir={temporary}",
                        "--no-add-ext", str(disk), "U1.VARS"],
                       capture_output=True, text=True, check=True)
        return (Path(temporary) / "U1.VARS").read_bytes()


def main():
    if not (TRACE / "out-player-reload/handoff.json").is_file():
        print("PENDING outdoor Q save and GEN B reload")
        return 0
    source = json.loads((TRACE / "out-after-space/handoff.json").read_text())
    first = json.loads((TRACE / "gen-player-save/handoff.json").read_text())
    menu = json.loads((TRACE / "gen-after-save/handoff.json").read_text())
    save = json.loads((TRACE / "out-player-save/handoff.json").read_text())
    reload = json.loads((TRACE / "out-player-reload/handoff.json").read_text())
    out_bytes = (ROOT / "extracted/OUT").read_bytes()
    at = lambda address, length: out_bytes[address-0x8956:address-0x8956+length]
    require(at(0x9ACE, 2) == bytes.fromhex("ca92") and
            at(0x92D7, 9) == bytes.fromhex("2024b76d7eca01387e"),
            "OUT Q handler pointer or save parameters differ")
    first_disk = checked(first["working_player_disk"])
    new_disk = checked(save["working_player_disk"])
    checked(save["source_snapshot"])
    checked(save["working_game_disk"])
    checked(save["snapshot"])
    require(save["source_snapshot"] == source["snapshot"] and
            save["working_game_disk"] == source["working_game_disk"] and
            save["previous_player_disk"] == first["working_player_disk"] and
            save["disk_before"] ==
            {"size": first["working_player_disk"]["size"],
             "sha256": first["working_player_disk"]["sha256"]} and
            save["working_player_disk"]["sha256"] !=
            save["previous_player_disk"]["sha256"] and
            save["input"] == 81 and save["handler"]["pc"] == "0x92CA" and
            save["call"]["pc"] == "0x92D7" and
            save["result"]["pc"] == "0x92E0" and
            not status_carry(save["result"]["cpu"]) and
            save["changed_record_addresses"] == ["0x7EDA", "0x7EE4"],
            "OUT Q save path or disk lineage differs")
    cp2 = json.loads(MANIFEST.read_text())["extractor"]["path"]
    first_record = extract(cp2, first_disk)
    new_record = extract(cp2, new_disk)
    source_record = main_ram(Path(source["snapshot"]["path"]))[START:START+LENGTH]
    saved_ram = main_ram(Path(save["snapshot"]["path"]))[START:START+LENGTH]
    require(len(first_record) == len(new_record) == LENGTH and
            new_record == source_record == saved_ram and
            [f"0x{START+i:04X}" for i, (a, b) in
             enumerate(zip(first_record, new_record)) if a != b] ==
            save["changed_record_addresses"] and
            (first_record[0x6D], new_record[0x6D]) == (0x00, 0x50) and
            (first_record[0x77], new_record[0x77]) == (0x95, 0x90) and
            save["initial_record_sha256"] ==
            save["record_at_call_sha256"] ==
            save["written_record_sha256"] == hashlib.sha256(new_record).hexdigest(),
            "OUT Q file bytes differ from live state")
    checked(reload["source_snapshot"])
    checked(reload["snapshot"])
    require(reload["source_snapshot"] == menu["snapshot"] and
            reload["save_snapshot"] == save["snapshot"] and
            reload["player_disk"] == save["working_player_disk"] and
            reload["input"] == 66 and
            [p["pc"] for p in reload["checkpoints"]] ==
            ["0x8A10", "0x8A1C", "0x8A7F", "0x8AC0"] and
            not status_carry(reload["checkpoints"][1]["cpu"]) and
            reload["final_cpu"].startswith("pc=8AC0") and
            reload["original_record_sha256"] ==
            hashlib.sha256(first_record).hexdigest() and
            reload["loaded_record_sha256"] ==
            hashlib.sha256(new_record).hexdigest(),
            "GEN B reload of outdoor save differs")
    live = main_ram(Path(reload["snapshot"]["path"]))[START:START+LENGTH]
    require(live == new_record, "GEN live record differs after Q-save reload")
    print("OUT Q: $92CA→$92D7→$92E0 saved 458 bytes; only $7EDA/$7EE4 changed")
    print("GEN B: $8A1C load, $8A7F copy, $8AC0 handoff restored all 458 bytes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError,
            subprocess.CalledProcessError) as error:
        print(f"OUT player-save/reload verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
