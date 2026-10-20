# Ultima I Apple II disassembly notes

This project studies the 1986 Apple II ProDOS release of *Ultima I*. The analysis follows the game's startup and module loading order. It records addresses, control flow, and data formats without storing the game disk or extracted files in Git.

## Local setup

1. Supply your own ProDOS extraction in `extracted/`, using the filenames in [the file map](docs/file-map.md).
2. Install `cc65` so that `da65` is on `PATH`. Ghidra can be used for interactive analysis.
3. Run `python3 tools/disassemble.py --check` to verify file sizes and load ranges.
4. Run `python3 tools/disassemble.py` for local listings in `build/disassembly/`.
5. Run `python3 tools/verify_disasm.py` to reassemble reviewed fragments and compare them with the local extraction.
6. Run `python3 tools/extract_data.py --check` to validate known data containers, or omit `--check` to extract records locally under `build/data/`.

The generated listings are **linear drafts**. They interpret embedded text, graphics, inline filenames, and tables as instructions. Review each code range against control flow before treating it as an assembly source. The listings also reproduce original bytes and are ignored by Git.

## Reading order

1. [File and memory map](docs/file-map.md)
2. [Dependency map](docs/dependency-map.md)
3. [File-by-file disassembly](disasm/README.md)
4. [Porting fidelity and evidence](docs/porting-fidelity.md)
5. [Roadmap to a faithful macOS port](docs/porting-roadmap.md)
6. [Startup and module loading](docs/startup.md)
7. [Gameplay module dispatch](docs/module-dispatch.md)
8. [Game structure map](docs/game-structure.md)
9. [Analysis log](docs/analysis-log.md)

The `extracted/` and `build/` directories, disk images, and Ghidra project files are ignored. Review any future annotated assembly before publication: even text form can contain substantial original game material.

In the current workspace, `.git` cannot be created, so Git metadata lives in ignored `.git-meta/`. Use `sh tools/repo-git status`, `sh tools/repo-git log`, and similar commands here. A normal clone of the GitHub repository uses ordinary `git` commands.
