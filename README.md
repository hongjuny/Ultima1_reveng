# Ultima I Apple II disassembly notes

This project studies the 1986 Apple II ProDOS release of *Ultima I*. The analysis follows the game's startup and module loading order. It records addresses, control flow, and data formats without storing the game disk or extracted files in Git.

## Native macOS application

With your local extraction and Ghidra installed:

```sh
python3 tools/build_macos_app.py
open "build/Ultima I.app"
```

The app translates the startup code into Swift and constructs the Origin splash,
intro animation, and Ultima I title from the original data at runtime. It then
executes MI.U1/STUPH/GEN to render the original English character creation
screens, including their font, input routines and confirmation/save flow. GEN B
loads the saved character into Sosaria with original OUT rendering, directional
movement and Q saving. Town/castle/dungeon tiles now enter the original TWN/CAS/DNG screens and return
to Sosaria through their original exit paths. See [Sosaria entry](docs/native-sosaria.md) and
[town entry](docs/native-town.md) and [castle entry](docs/native-castle.md) and [dungeon entry](docs/native-dungeon.md).
See the [original-screen comparison](docs/native-character-creation.md).
See [build and controls](macos/README.md) and the [startup translation report](docs/native-startup.md).
The local app bundle contains original assets and stays under ignored `build/`.

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

1. [Gameplay flow report: code, input, graphics, sound, memory (Korean)](docs/gameplay-flow-report.md)
   [Walkthrough-guided investigation plan (Korean)](docs/walkthrough-guided-investigation.md) maps version-specific guide claims to testable branches.
2. [Consolidated progress and gap report (Korean)](docs/consolidated-report-2026-10-21.md)
3. [File and memory map](docs/file-map.md)
4. [Dependency map](docs/dependency-map.md)
5. [Execution architecture (Korean)](docs/execution-architecture.md)
6. [Code/data evidence ledger (Korean)](docs/code-data-ledger.md), [Ghidra call atlas](docs/ghidra-call-atlas.md), and [reviewed assembly address atlas](docs/assembly-atlas.md)
7. [Command dispatch matrix (Korean)](docs/command-dispatch-matrix.md) and [memory and zero-page lifetimes (Korean)](docs/memory-and-zero-page.md)
8. [Shared I/O service vectors (Korean)](docs/shared-services.md) and [outdoor tile-to-pixel rendering (Korean)](docs/outdoor-rendering.md)
9. [File-by-file disassembly](disasm/README.md)
10. [Porting fidelity and evidence](docs/porting-fidelity.md)
11. [Roadmap to a faithful macOS port](docs/porting-roadmap.md)
    [Ghidra-first address-preserving port workflow (Korean)](docs/ghidra-first-port.md) records the new file-wide translation approach.
12. [Progress and effort audit (2026-10-21, Korean)](docs/progress-audit-2026-10-21.md)
13. [Local disk and emulator baseline](docs/baseline.md)
14. [Startup and module loading](docs/startup.md)
15. [Gameplay module dispatch](docs/module-dispatch.md)
16. [Game structure map](docs/game-structure.md)
17. [Analysis log](docs/analysis-log.md)

The `extracted/`, `disk/`, and `build/` directories and Ghidra project files are ignored. Review any future annotated assembly before publication: even text form can contain substantial original game material.

In the current workspace, `.git` cannot be created, so Git metadata lives in ignored `.git-meta/`. Use `sh tools/repo-git status`, `sh tools/repo-git log`, and similar commands here. A normal clone of the GitHub repository uses ordinary `git` commands.
