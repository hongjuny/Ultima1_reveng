# Evidence needed for a faithful macOS port

The target is the observable behavior of this Apple II ProDOS release: game rules, state transitions, data, input, presentation, persistence, and timing. A plausible rewrite is insufficient when the original behavior can be measured.

## Evidence levels

| Level | Meaning | What to record |
| --- | --- | --- |
| Byte verified | Reviewed 6502 fragment reassembles to the extracted bytes | File, address range, source, verification command |
| Static trace | Control flow or data use follows from identified instructions | Callers, branches, read/write addresses, unresolved indirect paths |
| Runtime confirmed | Same path observed in an Apple II emulator | Disk version, initial state, inputs with timing, relevant memory/visual output |
| Hypothesis | Plausible interpretation awaiting a trace | Evidence address and a test that could falsify it |

Do not mark a module or data format complete because its first entry and visible text are known. Each reachable code range, externally accessed data range, indirect target, and state mutation needs classification. Unknown bytes remain explicitly unclassified.

## Porting inventory

| Area | Current evidence | Needed before faithful implementation |
| --- | --- | --- |
| Startup and loading | Entry jumps, inline filenames, overlay base `$8956` | Semantics of `$B703`, `$B70C`, `$B733`, `$B736`; exact load order and failure paths |
| Shared state | Name table at `$7E16`; some fields near `$7E00` referenced | Typed memory map, initialization, ownership, persistence |
| Character creation | `GEN` menu branch verified | Attribute rules, choices, saved-character validation and format |
| Outdoor loop | Module selection cases verified | Input dispatch, movement, time step, encounters, economy, world-map encoding |
| Dungeon/town/castle/space/finale | Entry and some exits identified | Complete commands, combat, shops, quests, vehicles, victory path |
| Data and graphics | `TCMAPS` has ten 764-byte packed slots, but town/castle copy 768-byte windows | Explain four-byte overlap and last-window overread; decode map layout, tiles, glyphs, `MAPCHARS`, `NIF`, `STUPH` display regions |
| Apple II behavior | Keyboard/soft-switch accesses visible in code | Key mapping, display pages and modes, sound, timing, integer/decimal behavior |
| Persistence | File and disk operations visible but not traced | Save/load layout, write timing, disk error behavior |

## Repeatable comparisons

For a behavior under study, preserve the input sequence and a known initial game state. Record branch addresses and changed memory after each action; capture the corresponding screen and sound where relevant. A macOS implementation should run the same scenario and compare state and output. For data files, extract records with checked pointers and lengths, and keep checksums in a local manifest so a conversion can be reproduced without committing original assets.

`TCMAPS` is an example of why the port must follow code as well as file boundaries: the pointer stride is 764 bytes, while the runtime copy is 768 bytes. The four bytes read past the final file payload require an emulator memory trace before deciding how to model them.

The [dependency map](dependency-map.md) describes the changing memory image. The [file-by-file record](../disasm/README.md) tracks instruction and data coverage. This inventory should be revised whenever a trace changes an assumption.
