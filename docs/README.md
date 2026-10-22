# Documentation index

Start with the English guides below. Detailed notes preserve the language and
state of their original investigation; several were written before the native
app existed. **Use [current status](status.md) for implementation claims**, rather
than treating an old report's “next step” as today's missing feature.

## Current project guides — English

| Guide | Purpose |
| --- | --- |
| [Project overview](../README.md) | What this project is, current scope and local build entry point |
| [Build, controls and saves](../macos/README.md) | Run the native application |
| [Architecture](architecture.md) | Original overlays, translation, host boundaries, graphics, audio and persistence |
| [Status and limitations](status.md) | Implemented paths, fixtures and remaining work |
| [Developer guide](../CONTRIBUTING.md) | Dependencies, verification, contribution and publication boundaries |
| [Tool guide](../tools/README.md) | Entry points and script families |

## Native implementation reports — English

| Report | Scope |
| --- | --- |
| [Startup](native-startup.md) | Intro relocation, overlapping instructions and screen comparisons |
| [Character creation](native-character-creation.md) | Original GEN screens, input and saved record |
| [Sosaria](native-sosaria.md) | OUT entry, movement, save/load and missing-save handling |
| [Town](native-town.md) | TWN loading, map/font resources and exit |
| [Castle](native-castle.md) | CAS entry, movement, king interaction and return |
| [Dungeon](native-dungeon.md) | First-person entry, direction, ladder exit and saving restrictions |
| [Space](native-space.md) | SPA boarding, controls, fuel, view modes and controlled landing |
| [Time machine](native-tm.md) | TM pages, controlled ending and isolated test sessions |
| [Audio](native-audio.md) | Original speaker transitions, PCM output and timing checks |

## Original-program references — English

These describe the original program and selected evidence, not an exhaustive
native feature checklist.

- [File and memory map](file-map.md)
- [File dependencies and module transitions](dependency-map.md)
- [Game structure](game-structure.md)
- [Startup and loading](startup.md)
- [Player state and save format](player-state.md)
- [Dungeon map](dungeon-map.md) and [dungeon combat](dungeon-combat.md)
- [Reviewed assembly address atlas](assembly-atlas.md)
- [File-by-file disassembly index](../disasm/README.md)
- [Fidelity evidence levels and early inventory](porting-fidelity.md)

## Detailed research notes — Korean or mixed Korean/English

These retain address-level findings and provenance. Generated atlases remain at
stable paths because tools and other reports refer to them. They are research
references, not the recommended entry point for running the app.

| Topic | Notes |
| --- | --- |
| Original execution | [Execution architecture](execution-architecture.md), [gameplay flow report](gameplay-flow-report.md), [module dispatch](module-dispatch.md), [turn contracts](turn-contracts.md) |
| Ghidra and classification | [Address-preserving port workflow](ghidra-first-port.md), [call atlas](ghidra-call-atlas.md), [code/data ledger](code-data-ledger.md) |
| State and memory | [Memory and zero-page lifetimes](memory-and-zero-page.md), [player access atlas](player-access-atlas.md) |
| Input and output | [Command matrix](command-dispatch-matrix.md), [shared services](shared-services.md), [outdoor rendering](outdoor-rendering.md), [space view commands](spa-view-commands.md) |
| Progression | [Quests and final craft](quest-and-final-craft.md), [walkthrough-guided investigation](walkthrough-guided-investigation.md) |
| Reproduction | [Original baseline and boot troubleshooting](baseline.md) |
| Planning | [Original porting roadmap and acceptance criteria](porting-roadmap.md) |

## Historical reports and log

These are useful for understanding how the approach evolved. Their completion
counts and implementation gaps are historical snapshots.

- [Consolidated research report, 2026-10-21](consolidated-report-2026-10-21.md) — Korean.
- [Progress and effort audit, 2026-10-21](progress-audit-2026-10-21.md) — Korean.
- [Analysis log](analysis-log.md) — English chronological research entries.

Original game files, reference snapshots and generated translations remain local
under ignored paths. Maintainer-supplied gameplay screenshots are published in
the [project preview](../README.md#screenshots); private reference captures stay
under ignored `build/`.
