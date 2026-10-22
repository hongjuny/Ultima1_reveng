# Native macOS startup

The local app at `build/Ultima I.app` renders the Origin logo, the animated
castle/lake/night scene and the Ultima I title in their original order. It holds
the completed title until Return/Space or Start Game begins character creation.
See [build and controls](../macos/README.md) and [current status](status.md).
This report covers startup; gameplay now continues through all connected overlays.

## Original-to-native mapping

| Original stage | Native implementation |
| --- | --- |
| `U1.SYSTEM` startup selection and ProDOS load | The host loads bundled `U1.INTRO` at `$0800`; it does not execute ProDOS |
| `U1.INTRO $0800 → $0F23` | Address-preserving Swift blocks exported through Ghidra |
| `$0F28 → $B70C`, inline `MAKE.INDATA` | The host consumes the inline filename, loads/executes at `$1E00`, then applies the carry-clear return contract |
| `MAKE.INDATA $1F17` | Original copy/decompression logic; `$2000–$27FF → $8700–$8EFF` and `$27BD–$4DBC → $6000–$85FF` |
| Relocated `$8700–$8762` | Separate `INTRO.RELOC` Ghidra program at its execution address |
| Intro screen construction | Original data reads, address tables, memory writes, modified operands and branches |
| HGR pages and soft switches | Swift memory bus and [CoreGraphics renderer](../macos/Sources/HGRRenderer.swift) |
| Busy waits `$1F46`, `$0E23` | Equivalent exit registers/flags plus native scheduling; not cycle-accurate timing |

[Startup export](../tools/ghidra/export_startup.py) uses the private
`build/macos-startup/Startup.gpr`, separately from the broader research project.
The startup inputs contain 858 `U1.INTRO`, 259 `MAKE.INDATA` and 54 `INTRO.RELOC`
instruction candidates: **1,171 total**. The
[generator](../tools/transcribe_startup.py) checks each instruction's bytes against
local input and emits page-based Swift functions keyed by original PC.
Unexpected PCs or opcode changes fail explicitly.

Two important cases required explicit treatment. The JSR at `$0A5E` becomes RTS
at runtime. `$0D9B/$0D9E` are LDA entries overlapping BIT operands; Ghidra's
`PseudoDisassembler` exports those alternative entries. These cases are not
filled by assuming every byte in the file begins a valid instruction.

## Screen acceptance checks

The complete title boundary is `PC=$0B23`, `$09DD=4`, `$09DF=$88`. The native UI
holds this frame instead of continuing the original title's departure/dissolve.

[verify_native_startup.py](../tools/verify_native_startup.py) runs the built app
headlessly. The app reads its own original resources; emulator snapshots are
independent comparison evidence, not runtime inputs.

| Checkpoint | Independent reference | Comparison |
| --- | --- | --- |
| Complete Origin logo | `intro-support` snapshot | Both HGR pages, 16,384 bytes |
| First intro key poll | `intro-key-ready` snapshot | Both pages and displayed-page selection; Origin is still displayed at this first poll |
| Complete title | Conditional breakpoint in original execution | Both pages; active title page `$2000` |

Across the three checkpoints, **49,152 HGR bytes** and **322,560 rendered pixels**
match independently calculated results. Build-input and executable hashes prevent
verifying an outdated app after source changes. The title reference shortens only
the `$0E23` delay to its equivalent `A=0,C=1,V=0` exit state. These comparisons do
not establish exact timing or audible output; see [audio verification](native-audio.md).

The AppKit window, playback controls, scaling and fullscreen support are described
in the app guide. Automated tool execution validates startup headlessly; desktop
window interaction requires a normal macOS session. Original resources, generated
translations, captures and the app bundle stay under ignored `build/`.
