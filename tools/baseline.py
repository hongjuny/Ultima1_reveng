#!/usr/bin/env python3
"""Capture or verify a private baseline for the user-supplied extraction."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from disassemble import FILES, ROOT


MANIFEST = ROOT / "build" / "baseline" / "manifest.json"
VERSION_TOOLS = ("python3", "da65", "ca65", "ld65")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(path: Path) -> dict:
    return {"size": path.stat().st_size, "sha256": sha256(path)}


def tool_version(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise ValueError(f"required tool not found: {name}")
    result = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=True
    )
    return (result.stdout or result.stderr).strip().splitlines()[0]


def extractor_version(executable: Path) -> str:
    result = subprocess.run(
        [str(executable), "version"], capture_output=True, text=True, check=True
    )
    return (result.stdout or result.stderr).strip().splitlines()[0]


def emulator_version(executable: Path) -> str:
    result = subprocess.run(
        [str(executable), "--version"], capture_output=True, text=True, check=True
    )
    return (result.stdout or result.stderr).strip().splitlines()[0]


def capture(disk: Path | None, extractor: Path | None, emulator: Path | None) -> int:
    files = {}
    for name, (address, expected_size, _) in FILES.items():
        path = ROOT / "extracted" / name
        if not path.is_file():
            raise ValueError(f"missing extracted file: {name}")
        entry = describe(path)
        if entry["size"] != expected_size:
            raise ValueError(f"wrong size for {name}: {entry['size']} != {expected_size}")
        files[name] = {"load_address": f"0x{address:04X}", **entry}

    disk_entry = None
    if disk is not None:
        resolved = disk.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"disk image not found: {disk}")
        disk_entry = {"path": str(resolved), **describe(resolved)}
    if extractor is not None and disk_entry is None:
        raise ValueError("--extractor requires --disk")
    extractor_entry = None
    if extractor is not None:
        resolved = extractor.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"extractor not found: {extractor}")
        extractor_entry = {"path": str(resolved), "version": extractor_version(resolved)}
    emulator_entry = None
    if emulator is not None:
        resolved = emulator.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"emulator not found: {emulator}")
        emulator_entry = {"path": str(resolved), "version": emulator_version(resolved),
                          **describe(resolved)}

    manifest = {
        "schema": 1,
        "purpose": "private, local extraction identity; never publish",
        "disk_image": disk_entry,
        "extractor": extractor_entry,
        "tools": {name: tool_version(name) for name in VERSION_TOOLS},
        "files": files,
        "runtime": {
            "emulator": emulator_entry,
            "machine": "Apple //e Enhanced" if emulator_entry else None,
            "rom": "embedded in pinned a2m build" if emulator_entry else None,
            "boot_snapshot": None,
            "input_replay": None,
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"captured {len(files)} files in {MANIFEST.relative_to(ROOT)}")
    if disk_entry is None:
        print("PENDING disk image: capture again with --disk PATH")
    if extractor_entry is None:
        print("PENDING extractor: capture again with --extractor PATH")
    print("PENDING boot snapshot and input replay")
    return 0


def verify() -> int:
    if not MANIFEST.is_file():
        raise ValueError("no local baseline; run 'python3 tools/baseline.py capture' first")
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("schema") != 1 or set(manifest.get("files", {})) != set(FILES):
        raise ValueError("baseline schema or extracted file list differs")
    differences = []
    for name, (address, expected_size, _) in FILES.items():
        path = ROOT / "extracted" / name
        saved = manifest["files"][name]
        if not path.is_file():
            differences.append(f"{name}: missing")
            continue
        current = {"load_address": f"0x{address:04X}", **describe(path)}
        if current["size"] != expected_size:
            differences.append(f"{name}: size {current['size']} != catalog {expected_size}")
        for field in current:
            if current[field] != saved.get(field):
                differences.append(f"{name}: {field} differs from baseline")

    disk = manifest.get("disk_image")
    if disk:
        path = Path(disk["path"])
        if not path.is_file():
            differences.append(f"disk image missing: {path}")
        else:
            for field, value in describe(path).items():
                if value != disk.get(field):
                    differences.append(f"disk image: {field} differs from baseline")

    extractor = manifest.get("extractor")
    if extractor:
        path = Path(extractor["path"])
        if not path.is_file():
            differences.append(f"extractor missing: {path}")
        elif extractor_version(path) != extractor.get("version"):
            differences.append("extractor version differs from baseline")

    emulator = manifest.get("runtime", {}).get("emulator")
    if emulator:
        path = Path(emulator["path"])
        if not path.is_file():
            differences.append(f"emulator missing: {path}")
        else:
            for field, value in {"version": emulator_version(path), **describe(path)}.items():
                if value != emulator.get(field):
                    differences.append(f"emulator: {field} differs from baseline")
    snapshot = manifest.get("runtime", {}).get("boot_snapshot")
    boot_media = manifest.get("runtime", {}).get("boot_media")
    if boot_media:
        path = Path(boot_media["path"])
        if not path.is_file():
            differences.append(f"boot media missing: {path}")
        else:
            for field, value in describe(path).items():
                if value != boot_media.get(field):
                    differences.append(f"boot media: {field} differs from baseline")
    if snapshot:
        path = Path(snapshot["path"])
        if not path.is_file():
            differences.append(f"boot snapshot missing: {path}")
        else:
            for field, value in describe(path).items():
                if value != snapshot.get(field):
                    differences.append(f"boot snapshot: {field} differs from baseline")
    replay = manifest.get("runtime", {}).get("input_replay")
    if replay:
        path = Path(replay["path"])
        if not path.is_file():
            differences.append(f"input replay missing: {path}")
        else:
            for field, value in describe(path).items():
                if value != replay.get(field):
                    differences.append(f"input replay: {field} differs from baseline")

    for name in VERSION_TOOLS:
        try:
            version = tool_version(name)
        except (ValueError, subprocess.CalledProcessError) as error:
            differences.append(str(error))
            continue
        if version != manifest.get("tools", {}).get(name):
            differences.append(f"{name}: version differs from baseline")

    if differences:
        for difference in differences:
            print(f"MISMATCH {difference}", file=sys.stderr)
        return 1
    print(f"matched {len(FILES)} extracted files and {len(VERSION_TOOLS)} tool versions")
    if disk is None:
        print("PENDING disk image")
    if extractor is None:
        print("PENDING extractor and disk-to-extraction comparison")
    if not all(manifest.get("runtime", {}).values()):
        print("PENDING runtime snapshot and input replay")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture_parser = commands.add_parser("capture", help="write a private local manifest")
    capture_parser.add_argument("--disk", type=Path, help="original disk image path")
    capture_parser.add_argument("--extractor", type=Path, help="CiderPress cp2 executable")
    capture_parser.add_argument("--emulator", type=Path, help="local a2m executable")
    commands.add_parser("verify", help="compare with the saved manifest")
    args = parser.parse_args()
    try:
        return capture(args.disk, args.extractor, args.emulator) if args.command == "capture" else verify()
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"baseline error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
