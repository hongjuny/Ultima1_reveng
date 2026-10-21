#!/usr/bin/env python3
"""Compare the native Swift startup with independent original RAM checkpoints."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column

BUILD = ROOT / "build/macos-startup"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise ValueError(f"reference input changed: {path}")
    return path


def main():
    executable = ROOT / "build/Ultima I.app/Contents/MacOS/UltimaI"
    output = BUILD / "native-capture"
    if not executable.is_file() or not (BUILD / "reference/handoff.json").is_file():
        print("PENDING native startup app/reference; build the app and capture the original title")
        return
    built = json.loads((BUILD / "app-build.json").read_text())
    for path, expected in built["source_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"native source changed; rebuild the app: {path}")
    if hashlib.sha256(executable.read_bytes()).hexdigest() != built["executable_sha256"]:
        raise ValueError("native executable differs from build manifest")
    subprocess.run([str(executable), "--capture", str(output)], check=True)
    native = json.loads((output / "report.json").read_text())
    if (native["title_pc"] != 0x0B23 or not native["hires"] or native["text"] or
            native["title_phase"] != {"kind_09DD": 4, "counter_09DC": 0x17,
                                      "reveal_09DF": 0x88}):
        raise ValueError("native app did not reach the complete title in HGR mode")
    manifest = json.loads((BUILD / "translation-manifest.json").read_text())
    for name in ("U1.INTRO", "MAKE.INDATA"):
        actual = hashlib.sha256((ROOT / "extracted" / name).read_bytes()).hexdigest()
        if actual != manifest["source_sha256"][name]:
            raise ValueError("native translation source changed")
    support = json.loads((ROOT / "build/traces/intro-support/handoff.json").read_text())
    first = json.loads((ROOT / "build/traces/intro-to-engine/handoff.json").read_text())
    reference = json.loads((BUILD / "reference/handoff.json").read_text())
    if (reference["checkpoint"]["pc"] != "0x0B23" or
            reference["checkpoint"]["condition"] != "mem($09DD)==$04,mem($09DF)==$88" or
            reference["intervention"] != {
            "address": 0x0E23, "before": "2ce8c03848", "after": "a90038b860",
            "purpose": "delay only"}):
        raise ValueError("original title reference or delay intervention differs")
    if reference["source_snapshot"] != first["prekey_snapshot"]:
        raise ValueError("original title reference ancestry differs")
    references = {"origin": main_ram(checked(support["snapshot"])),
                  "intro-first": main_ram(checked(first["prekey_snapshot"])),
                  "title": checked(reference["ram"]).read_bytes()}
    matching_bytes = matching_pixels = 0
    for point in native["checkpoints"]:
        name = point["name"]
        ram = (output / (name + ".ram")).read_bytes()
        expected = references[name]
        for page in (0x2000, 0x4000):
            if ram[page:page+8192] != expected[page:page+8192]:
                offset = next(i for i in range(8192) if ram[page+i] != expected[page+i])
                raise ValueError(f"{name}: video RAM differs at ${page+offset:04X}")
            matching_bytes += 8192
        rgba = (output / (name + ".rgba")).read_bytes()
        if len(rgba) != 560 * 192 * 4:
            raise ValueError(f"{name}: native raster size differs")
        # Normalize the independently captured display page for the Python raster model.
        normalized = bytearray(0x6000)
        page = point["page"]
        normalized[0x4000:0x6000] = expected[page:page+8192]
        for y in range(192):
            for column in range(40):
                for bit, color in enumerate(expected_column(normalized, y, column)):
                    x = column * 14 + bit
                    offset = (y * 560 + x) * 4
                    if rgba[offset:offset+4] != color.to_bytes(3, "big") + b"\xff":
                        raise ValueError(f"{name}: native pixel differs at ({x},{y})")
                    matching_pixels += 1
    report = {"matching_video_bytes": matching_bytes, "matching_pixels": matching_pixels,
              "checkpoints": list(references), "native_title_pc": "0x0B23",
              "ghidra_candidate_instructions": manifest["total_candidate_instructions"],
              "executed_unique_instructions": native["visited_instructions"],
              "reference_intervention": reference["intervention"],
              "timing_claim": "native scheduling; original busy waits collapsed"}
    (BUILD / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Native startup: {matching_bytes} video bytes and {matching_pixels} pixels match "
          "original Origin, first intro, and complete-title checkpoints")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Native startup verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
