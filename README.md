# Ultima I Apple II disassembly notes

This project studies the 1986 Apple II ProDOS release of *Ultima I*. The analysis follows the game's startup and module loading order. It records addresses, control flow, and data formats without storing the game disk or extracted files in Git.

## Local setup

1. Supply your own ProDOS extraction in `extracted/`, using the filenames in [the file map](docs/file-map.md).
2. Keep the original disk at `disk/UltimaI.woz` for byte-for-byte extraction checks. Install `cc65` and CiderPress II. Ghidra 12.1.4 is used for the candidate call graph.
3. Follow [the local baseline setup](docs/baseline.md), then run `python3 tools/check_all.py` for the combined checks.
4. Run `python3 tools/disassemble.py` for local listings in `build/disassembly/`.
5. Run `python3 tools/verify_disasm.py` to reassemble reviewed fragments and compare them with the local extraction.
6. Run `python3 tools/extract_data.py --check` to validate known data containers, or omit `--check` to extract records locally under `build/data/`.
7. Run private emulator traces with `python3 tools/run_runtime.py trace_out_after_space.py`. The runner builds an isolated a2m control variant, runs the named trace scripts in order, and then runs `check_all.py`.
8. If Ghidra is installed, run `python3 tools/ghidra/import_modules.py` to rebuild the private 6502 programs and call/zero-page TSV files under `build/ghidra-project/`; `python3 tools/ghidra/verify_exports.py` checks the published candidate counts and selected call edges.

The generated listings are **linear drafts**. They interpret embedded text, graphics, inline filenames, and tables as instructions. Review each code range against control flow before treating it as an assembly source. The listings also reproduce original bytes and are ignored by Git.

## Reading order

1. [File and memory map](docs/file-map.md)
2. [Dependency map](docs/dependency-map.md)
3. [Execution architecture (Korean)](docs/execution-architecture.md)
4. [Ghidra call atlas](docs/ghidra-call-atlas.md) and [reviewed assembly address atlas](docs/assembly-atlas.md)
5. [Command dispatch matrix (Korean)](docs/command-dispatch-matrix.md) and [memory and zero-page lifetimes (Korean)](docs/memory-and-zero-page.md)
6. [Shared I/O service vectors (Korean)](docs/shared-services.md)
7. [File-by-file disassembly](disasm/README.md)
8. [Porting fidelity and evidence](docs/porting-fidelity.md)
9. [Roadmap to a faithful macOS port](docs/porting-roadmap.md)
10. [Progress and effort audit (2026-10-21, Korean)](docs/progress-audit-2026-10-21.md)
11. [Local disk and emulator baseline](docs/baseline.md)
12. [Startup and module loading](docs/startup.md)
13. [Gameplay module dispatch](docs/module-dispatch.md)
14. [Game structure map](docs/game-structure.md)
15. [Analysis log](docs/analysis-log.md)

The `extracted/`, `disk/`, and `build/` directories and Ghidra project files are ignored. Review any future annotated assembly before publication: even text form can contain substantial original game material.

In the current workspace, `.git` cannot be created, so Git metadata lives in ignored `.git-meta/`. Use `sh tools/repo-git status`, `sh tools/repo-git log`, and similar commands here. A normal clone of the GitHub repository uses ordinary `git` commands.
