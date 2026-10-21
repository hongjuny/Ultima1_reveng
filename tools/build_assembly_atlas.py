#!/usr/bin/env python3
"""Locate every reviewed assembly fragment within its original module image."""

import argparse
from collections import defaultdict
from pathlib import Path
import sys

from disassemble import FILES, ROOT
from verify_disasm import FRAGMENTS


OUTPUT = ROOT / "docs/assembly-atlas.md"


def render():
    grouped = defaultdict(list)
    for source, module, base, start, end in FRAGMENTS:
        expected_base, size, _ = FILES[module]
        if base != expected_base or not base <= start < end <= base + size:
            raise ValueError(f"fragment outside its source image: {source}")
        grouped[module].append((start, end, source))
    unique = {(module, address)
              for module, ranges in grouped.items()
              for start, end, _ in ranges for address in range(start, end)}
    lines = [
        "# Reviewed assembly address atlas", "",
        "This index places every **byte-matched, reviewed fragment** at its original Apple II load address. Each link leads to a small, public annotation; full linear listings and binary assets remain private. An unlisted address is **unreviewed**, not proven to be data or unreachable code. Overlapping reviewed fragments count once in the unique-byte total.", "",
        f"Current inventory: **{len(FRAGMENTS)} fragments, {len(unique)} unique bytes** across {len(grouped)} modules. These are raw-file bytes, not a percentage of executable code: code and data are mixed.", "",
        "| Module | Load range | Reviewed fragments | Unique reviewed bytes |",
        "| --- | --- | ---: | ---: |",
    ]
    for module in FILES:
        if module not in grouped:
            continue
        base, size, _ = FILES[module]
        count = sum(1 for name, _ in unique if name == module)
        lines.append(f"| [{module}](#{module.lower().replace('.', '')}) | `${base:04X}–${base+size-1:04X}` | {len(grouped[module])} | {count} |")
    lines += ["", "The `$8956` ranges below are **mutually exclusive overlays**. A call at `$8A00` must be interpreted with the loaded module named; these files do not form one combined address space. `MI.U1`'s final `$8956–$89BC` loader tail is overwritten after selection. See the [execution architecture](execution-architecture.md) and [Ghidra call atlas](ghidra-call-atlas.md).", ""]
    for module in FILES:
        if module not in grouped:
            continue
        base = FILES[module][0]
        lines += [f"## {module}", "", "| RAM address | File offset | Bytes | Reviewed source |", "| --- | --- | ---: | --- |"]
        for start, end, source in sorted(grouped[module]):
            lines.append(f"| `${start:04X}–${end-1:04X}` | `${start-base:04X}–${end-base-1:04X}` | {end-start} | [{source}](../disasm/{source}) |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != result:
            print("assembly atlas is stale; run python3 tools/build_assembly_atlas.py", file=sys.stderr)
            return 1
        print("reviewed assembly atlas is current")
        return 0
    OUTPUT.write_text(result)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
