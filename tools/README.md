# Tool guide

Run commands from the repository root. Private inputs and outputs stay in
`extracted/`, `disk/` and `build/`. Most trace scripts are small, scenario-specific
research tools with prerequisites; their presence does not make each one a
standalone clean-clone test. See the [developer guide](../CONTRIBUTING.md).

## Common entry points

| Task | Command |
| --- | --- |
| Build the macOS app | `python3 tools/build_macos_app.py` |
| Refresh native Ghidra exports and build | `python3 tools/build_macos_app.py --ghidra` |
| Run available checks | `python3 tools/check_all.py` |
| Check original-file sizes and addresses | `python3 tools/disassemble.py --check` |
| Generate private linear disassembly drafts | `python3 tools/disassemble.py` |
| Reassemble reviewed fragments | `python3 tools/verify_disasm.py` |
| Check known data containers | `python3 tools/extract_data.py --check` |
| Run an existing original-emulator trace | `python3 tools/run_runtime.py --no-check trace_out_after_space.py` |

Linear listings and speculative instruction candidates are not a completed
code/data classification. Generated outputs can reproduce original game bytes
and must not be published.

## Tool families

| Pattern or directory | Role |
| --- | --- |
| `ghidra/` | Import original modules separately; export instructions, calls, zero-page references and runtime candidates |
| `transcribe_startup.py`, `transcribe_game_flow.py` | Byte-check Ghidra exports and generate private address-preserving Swift |
| `build_macos_app.py` | Assemble the local native app from sources, generated Swift and original resources |
| `verify_native_*.py` | Execute the native app headlessly and compare selected screens, state, saves or sound |
| `trace_*.py` | Capture a specific original-emulator scenario; read each script's source inputs first |
| `verify_*.py` | Check a particular recorded contract or data interpretation |
| `build_*atlas.py`, `build_*matrix.py`, other `build_*.py` | Generate reference documents or prepare local tool infrastructure; inspect the individual script |
| `extract_*.py`, `inspect_*.py` | Decode or inspect local game data and service tables |
| `baseline.py`, `capture_boot.py`, `verify_disk.py` | Record private input/tool versions, capture boot and compare disk extraction |
| `repo-git` | Wrapper for one maintainer checkout's separate metadata directory; ordinary clones use `git` |

## Native verification entry points

```sh
python3 tools/verify_native_startup.py
python3 tools/verify_native_character.py
python3 tools/verify_native_sosaria.py
python3 tools/verify_native_town.py
python3 tools/verify_native_castle.py
python3 tools/verify_native_dungeon.py
python3 tools/verify_native_space.py
python3 tools/verify_native_test_sessions.py
python3 tools/verify_native_audio.py
```

Build first. Several screen comparisons require independent original snapshots.
The audio test executes original STUPH effects and writes private WAV/JSON output
without opening an audio device. A `PENDING` message means evidence was absent,
not that the corresponding behavior was verified.

The combined suite remains `check_all.py`; this guide provides navigation rather
than duplicating the full scenario inventory maintained in that script.
