#!/usr/bin/env python3
"""Check TM gem, directional attack, controlled victory gate, and NIF load."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"


def checked(name):
    report = json.loads((TRACE / name / "handoff.json").read_text())
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"TM private snapshot changed: {path}")
    return report, main_ram(path)


def pcs(report):
    return [item["pc"] for item in report["checkpoints"]]


def main():
    if not (TRACE / "tm-victory-nif/handoff.json").is_file():
        print("PENDING controlled TM victory gate trace")
        return 0
    tm = (ROOT / "extracted/TM").read_bytes()
    at = lambda address, length: tm[address-0x8956:address-0x8956+length]
    require(at(0x8FEE, 3) == bytes.fromhex("ad f2 7e") and
            at(0x901D, 5) == bytes.fromhex("ad ab 95 d0 12") and
            at(0x9033, 1) == b"\x60" and
            at(0x9034, 3) == bytes.fromhex("20 36 a4") and
            at(0x9052, 7) == bytes.fromhex("20 03 b7 4e 49 46 00") and
            at(0x951A, 3) == bytes.fromhex("ee ab 95"),
            "TM victory gate or G action differs from extraction")
    first, ram = checked("tm-command")
    require(first["input"]["key_ascii"] == 21 and first["handler"] == "0x96C4" and
            list(ram[:2]) == [5, 5], "first east move differs")
    prior = first
    for number, x in enumerate(range(6, 15), 1):
        step, ram = checked(f"tm-approach-gem/step-{number:02d}")
        require(step["source_snapshot"] == prior["snapshot"] and
                step["input"]["key_ascii"] == 21 and
                step["handler"] == "0x96C4" and list(ram[:2]) == [x, 5] and
                ram[0x95AB] == 0 and
                int.from_bytes(ram[0x7EF4:0x7EF6], "little") == 1000,
                f"TM gem approach step {number} differs")
        prior = step
    require(int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 109,
            "HP at gem approach differs")
    gem, ram = checked("tm-gem-command")
    require(gem["source_snapshot"] == prior["snapshot"] and
            gem["input"]["key_ascii"] == 71 and gem["handler"] == "0x94D6" and
            list(ram[:2]) == [14, 5] and ram[0x95AB] == 1 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 28 and
            int.from_bytes(ram[0x7EF4:0x7EF6], "little") == 1000 and
            list(ram[0xB628:0xB62C]) == [15, 5, 15, 5],
            "TM G result differs")
    expected = {
        "tm-attack-direction": (None, 970, 1, "0x8FC8"),
        "tm-attack-direction-control": ({"address": "0x7EF4", "mondain_hp": 1},
                                        65507, 1, "0x9034"),
        "tm-attack-direction-no-gem-control": ({"mondain_hp": 1, "gem_destroyed": 0},
                                               65507, 0, "0x9033"),
    }
    attacks = {}
    for name, (intervention, hp, flag, end) in expected.items():
        attack, ram = checked(name)
        require(attack["source_snapshot"] == gem["snapshot"] and
                attack["input"] == [65, 21] and
                attack["intervention"] == intervention and
                pcs(attack)[:4] == ["0x8EDC", "0x9815", "0x9177", "0x8F80"] and
                pcs(attack)[-1] == end and
                attack["before"] == {"player_hp": 28, "mondain_hp": 1000,
                                     "gem_destroyed": 1, "position": [14, 5]} and
                int.from_bytes(ram[0x7EF4:0x7EF6], "little") == hp and
                ram[0x95AB] == flag,
                f"TM A/east result differs: {name}")
        attacks[name] = attack
    nif, ram = checked("tm-victory-nif")
    require(nif["source_snapshot"] == attacks["tm-attack-direction-control"]["snapshot"] and
            pcs(nif) == ["0x9052", "0xB703", "0x9059"] and nif["nif_match"] is True and
            ram[0x4000:0x5E00] == (ROOT / "extracted/NIF").read_bytes(),
            "TM controlled victory NIF load differs")
    intro = json.loads((TRACE / "tm-intro-pages/probe.json").read_text())
    intro_ram = main_ram(Path(intro["snapshot"]["path"]))
    require(ram[0x5E00:0x6000] == intro_ram[0x5E00:0x6000] and
            sum(value != 0 for value in ram[0x5E00:0x6000]) == 232,
            "NIF overread tail changed after TM entry")
    copied, copy_ram = checked("tm-nif-copy")
    require(copied["source_snapshot"] == nif["snapshot"] and
            pcs(copied) == ["0x9073", "0x9094"] and
            copied["result"] == {"file_payload_match": True,
                                  "full_8192_copy_match": True,
                                  "source_cleared": True,
                                  "tail_512_nonzero": 232,
                                  "prior_target_changed_bytes": 7954} and
            copy_ram[0x4000:0x6000] == bytes(8192),
            "TM NIF 8-KiB move differs")
    visible_offsets = {((y & 7) << 10) + (((y >> 3) & 7) << 7) +
                       ((y >> 6) * 40) + x
                       for y in range(192) for x in range(40)}
    tail_visible = [offset for offset in visible_offsets if offset >= 0x1E00]
    require(len(visible_offsets) == 7680 and len(tail_visible) == 480 and
            sum(copy_ram[0x6000 + offset] != 0 for offset in tail_visible) == 232,
            "NIF overread tail HGR-layout coverage differs")
    comparison = json.loads((TRACE / "tm-nif-tail-effect/handoff.json").read_text())
    require(comparison["source_snapshot"] == nif["snapshot"] and
            comparison["intervention"] == {"address": "0x5E00", "length": 512,
                                            "tail_cleared_only_in": "tail-cleared"} and
            comparison["differing_bytes"] == {
                stage: {"page_2000": 0, "page_4000": 0, "page_6000": 232}
                for stage in ("after_move", "animation", "final_wait")},
            "TM NIF tail video comparison differs")
    for label in ("intact", "tail-cleared"):
        trial = comparison["trials"][label]
        item = trial["snapshot"]
        require(describe(Path(item["path"])) == {"size": item["size"],
                                                  "sha256": item["sha256"]} and
                trial["tail_nonzero"] == 232 and
                pcs(trial) == ["0x9094", "0x90AA", "0x9132"],
                f"TM NIF tail trial differs: {label}")
    intact_ram = main_ram(Path(comparison["trials"]["intact"]["snapshot"]["path"]))
    cleared_ram = main_ram(Path(comparison["trials"]["tail-cleared"]["snapshot"]["path"]))
    require(intact_ram[0x2000:0x6000] == cleared_ram[0x2000:0x6000] and
            sum(a != b for a, b in zip(intact_ram[0x6000:0x8000],
                                       cleared_ram[0x6000:0x8000])) == 232,
            "TM final wait pages differ from live comparison")
    final, _ = checked("tm-final-wait")
    require(final["source_snapshot"] == copied["snapshot"] and
            final["input"] == 32 and
            pcs(final) == ["0x90AA", "0x9132", "0x914D", "0x912F"],
            "TM final animation/key loop differs")
    print("TM: 10 east moves, G destroys gem, A+east damages Mondain 1000→970;")
    print("controlled 1-HP branches by gem flag to $9034 or $9033; NIF loads at $4000")
    print("finale moves $4000-$5FFF to $6000-$7FFF, clears source, then loops on keys")
    print("extra 512 source bytes persisted; clearing them leaves sampled video pages unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM victory gate verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
