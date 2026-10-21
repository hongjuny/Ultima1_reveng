#!/usr/bin/env python3
"""Build the native startup app from private Ghidra translation and local assets."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

from disassemble import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghidra", action="store_true", help="refresh private startup analyses")
    args = parser.parse_args()
    build = ROOT / "build/macos-startup"
    if args.ghidra or not (build / "U1.INTRO-alternates.tsv").is_file() or not all((build / f"{name}-instructions.tsv").is_file()
                              for name in ("U1.INTRO", "MAKE.INDATA", "INTRO.RELOC")):
        subprocess.run([sys.executable, "tools/ghidra/export_startup.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "tools/transcribe_startup.py"], cwd=ROOT, check=True)
    app = ROOT / "build/Ultima I.app"
    contents = app / "Contents"
    executable = contents / "MacOS/UltimaI"
    data = contents / "Resources/OriginalData"
    executable.parent.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    for name in ("U1.INTRO", "MAKE.INDATA"):
        shutil.copyfile(ROOT / "extracted" / name, data / name)
    env = os.environ.copy()
    cache = str(build / "module-cache")
    env["CLANG_MODULE_CACHE_PATH"] = cache
    env["SWIFT_MODULE_CACHE_PATH"] = cache
    sources = sorted((ROOT / "macos/Sources").glob("*.swift"))
    sources.append(build / "StartupTranslated.swift")
    command = ["swiftc", "-O", "-module-name", "UltimaIStartup",
               "-target", f"{platform.machine()}-apple-macos13.0",
               "-module-cache-path", cache, "-framework", "AppKit", "-framework", "ImageIO",
               *map(str, sources), "-o", str(executable)]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    info = {"CFBundleExecutable": "UltimaI", "CFBundleIdentifier": "org.ultima1-reveng.startup",
            "CFBundleName": "Ultima I", "CFBundleDisplayName": "Ultima I",
            "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "0.1",
            "CFBundleVersion": "1", "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True, "NSPrincipalClass": "NSApplication"}
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
    inputs = sources + [ROOT / "tools/transcribe_startup.py", ROOT / "tools/build_macos_app.py"]
    (build / "app-build.json").write_text(json.dumps({
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in inputs},
        "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()}, indent=2) + "\n")
    print(app)


if __name__ == "__main__":
    main()
