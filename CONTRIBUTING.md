# Developer guide

The current application and evidence boundaries are described in
[architecture](docs/architecture.md) and [status](docs/status.md).
ChatGPT and Codex have been substantial contributors to this work. Apply the same
byte checks and independent behavioral checks to generated and handwritten code.

## Build the native app

Requirements for the current build scripts:

- macOS 13 or later as the application deployment target; development so far has
  used Apple Silicon. Other configurations have not been established by testing.
- Xcode Command Line Tools or an Xcode installation providing `swiftc` and
  `codesign`, plus Python 3.
- Ghidra and its compatible Java runtime. The project has used Ghidra 12.1.4.
  Set `ULTIMAI_GHIDRA_HOME` to its installation directory if needed.
- Your own extraction of the supported **1986 Apple II ProDOS** release. Raw
  extracted files have no embedded load-address header. Use the names and sizes
  in the [file map](docs/file-map.md).

```sh
export ULTIMAI_GHIDRA_HOME="/path/to/ghidra"
python3 tools/build_macos_app.py
open "build/Ultima I.app"
```

The required app resources are listed in [macos/README.md](macos/README.md).
The builder creates private Ghidra exports and Swift translations as needed,
bundles local resources, compiles and ad-hoc signs the app. Use `--ghidra` to
refresh all native translation exports. Rebuild after changing Swift sources,
the translators or the build script; a verifier checks the build-input hashes.

Ghidra exports and the native app do not need an emulator at runtime. Full
original-versus-native comparisons require the additional research setup below.

## Research and verification

Additional tools used by the full suite are cc65 (`da65`, `ca65`, `ld65`),
CiderPress II, and the pinned a2m emulator. Some checks use previously collected
private snapshots and trace reports. They must be generated locally, in the
required dependency order; a clean clone does not include that evidence.

The [baseline research notes](docs/baseline.md) are in Korean and retain early
boot troubleshooting and emulator build commands. The baseline manifest contains
local paths and hashes. Do not overwrite an existing manifest without preserving
its captured evidence first.

```sh
# Configure a new local baseline only after installing the research tools:
python3 tools/baseline.py capture \
  --disk disk/UltimaI.woz \
  --extractor /path/to/CiderPress2/cp2 \
  --emulator build/emulator/a2m-build/a2m

# Run all currently available checks:
python3 tools/check_all.py

# Run a specific existing trace with its prerequisites already present:
python3 tools/run_runtime.py --no-check trace_out_after_space.py
```

`run_runtime.py` builds a separate socketpair-control a2m variant and runs the
specified scripts in order. Without `--no-check`, it runs the combined checks
afterward. Trace names are not a promise that the required earlier snapshots
exist. Read the selected script's source/report inputs before running it.

`check_all.py` can print `PENDING` for absent evidence. Report which comparisons
actually ran. Native verifier entry points and tool families are listed in the
[tool guide](tools/README.md).

## Evidence conventions

- Name the original module and address; the same PC can identify different
  overlay instructions at different times.
- Distinguish byte-verified assembly, static interpretation, original-emulator
  observation and native behavioral comparison.
- Identify fixtures and altered state explicitly. Controlled one-hit victory is
  not evidence of a normal full-health playthrough.
- Record inputs, initial state, outputs and unresolved branches. Original bytes
  matching a Ghidra candidate do not prove that the bytes are executable code.
- Keep generated listings, snapshots and captures private. Publish procedures,
  addresses and measured results, reviewing any assembly fragment before sharing.

## Where changes belong

| Change | Location |
| --- | --- |
| Native host, graphics, audio or file services | `macos/Sources/` |
| Instruction translation | `tools/transcribe_startup.py`, `tools/transcribe_game_flow.py` |
| Ghidra import/export | `tools/ghidra/` |
| Original-runtime tracing | `tools/trace_*.py` and the associated verifier |
| Native regression checks | `tools/verify_native_*.py` |
| Current user-facing scope | `README.md`, `docs/status.md`, `macos/README.md` |
| Detailed evidence | Module reports and `disasm/` |

Do not hand-edit generated Swift under `build/` as the final fix. Fix its source
translator or the host boundary and regenerate it. When behavior changes, run
the relevant check and the required combined gate. Documentation-only edits need
link/content checks, not a rebuild of the game.

Keep the public entry points and new implementation reports in English. Existing
Korean research notes remain available through the [documentation index](docs/README.md).
Dated reports describe their investigation period and are not the current status.
Several address atlases and matrices are generated by tools: edit their generator
rather than moving or rewriting the output independently.

## Publication boundaries

Do not commit `extracted/`, `disk/`, `build/`, original images/data, private
snapshots, full generated instruction exports, or app bundles containing original
resources. Also review screenshots and newly annotated fragments before sharing.
Do not infer a license for the original game or project code from its public
availability; licensing decisions belong to the maintainer.

## Git in the maintainer's current checkout

A normal clone uses ordinary `git` commands. One existing workspace stores its
metadata in ignored `.git-meta/` because of local filesystem restrictions; only
in that workspace, use `sh tools/repo-git status` and the equivalent wrapper
commands. This is a local checkout detail, not a project setup requirement.
