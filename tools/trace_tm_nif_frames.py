#!/usr/bin/env python3
"""Sample both HGR pages while TM scrolls the 192 packed NIF rows."""

import hashlib
import json
from pathlib import Path
import re
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc
from trace_tm_nif_render import SOURCE, hgr_offset, word


OUTPUT = ROOT / "build/traces/tm-nif-frames"
SAMPLE_ROWS = {1, 2, 3, 16, 48, 96, 144, 191, 192}


def matching_rows(page, packed, consumed):
    """Compare packed source rows with the lower consumed screen rows."""
    return sum(
        page[hgr_offset(192 - consumed + i):hgr_offset(192 - consumed + i) + 40]
        == packed[40 * i:40 * (i + 1)]
        for i in range(consumed)
    )


def cpu_cycles(cpu):
    match = re.search(r"\bcycles=(\d+)\b", cpu)
    if not match:
        raise RuntimeError(f"a2m did not report cycles: {cpu}")
    return int(match.group(1))


def main():
    prior = json.loads(SOURCE.read_text())
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9094:
        raise RuntimeError("source is not at NIF copy completion")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9094:
                    raise RuntimeError("restored NIF PC differs")
                packed = client.mem(0x6000, 7680)
                if packed != (ROOT / "extracted/NIF").read_bytes():
                    raise RuntimeError("NIF packed buffer mismatch")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $90FE")
                samples = []
                row_cycles = []
                for consumed in range(1, 193):
                    client.ok("run")
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x90FE:
                        raise RuntimeError(f"row {consumed}: unexpected stop {cpu}")
                    row_cycles.append(cpu_cycles(cpu))
                    if consumed not in SAMPLE_ROWS:
                        continue
                    pages = {f"${base:04X}": matching_rows(client.mem(base, 8192), packed, consumed)
                             for base in (0x2000, 0x4000)}
                    switches = client.get_softswitches()
                    sample = {"consumed": consumed, "cpu": cpu,
                              "remaining_before_decrement": client.mem(0x006D, 1)[0],
                              "next_source": f"${word(client, 0x90E8):04X}",
                              "last_destination": f"${word(client, 0x90EB):04X}",
                              "matching_lower_rows": pages,
                              "video_switches": {key: switches[key]
                                                 for key in ("TEXT", "MIXED", "PAGE2", "HIRES")},
                              "state": client.ok("get-state")}
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $9101")
                    client.ok("run")
                    client.ok("wait-paused 15000")
                    after_cpu = client.ok("get-cpu")
                    if cpu_pc(after_cpu) != 0x9101:
                        raise RuntimeError(f"row {consumed}: page flip did not return: {after_cpu}")
                    after_switches = client.get_softswitches()
                    sample["after_flip_cpu"] = after_cpu
                    sample["video_after_flip"] = {key: after_switches[key]
                                                  for key in ("TEXT", "MIXED", "PAGE2", "HIRES")}
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $90FE")
                    samples.append(sample)
                    print(f"NIF row {consumed}: target {sample['last_destination']} "
                          f"lower-row matches {pages}; page2 "
                          f"{sample['video_switches']['PAGE2']}→"
                          f"{sample['video_after_flip']['PAGE2']}", flush=True)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "nif_sha256": hashlib.sha256(packed).hexdigest(),
                          "sample_rows": sorted(SAMPLE_ROWS), "samples": samples,
                          "row_copy_hits": 192, "row_copy_cycles": row_cycles,
                          "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    deltas = [b - a for a, b in zip(row_cycles, row_cycles[1:])]
    print(f"NIF row intervals: min={min(deltas)} max={max(deltas)} "
          f"mean={sum(deltas) / len(deltas):.1f} CPU cycles", flush=True)
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF frame trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
