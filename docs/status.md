# Current status and limitations

Updated 2026-10-22. This page summarizes the native app; older research reports
preserve the state of individual investigations and may describe earlier gaps.

## Implemented and checked

| Area | Current evidence | Limits |
| --- | --- | --- |
| Intro | Original splash, animation and title; three HGR/pixel checkpoints | Selected waits are collapsed; title is held by the native UI |
| Character creation | Original menus, allocation, choices, name, confirmation, save/load | Not every invalid-input or record-error branch is covered |
| Sosaria | Entry, initial movement, command handling and outdoor saving | Encounters, spells, vehicles and other branches need broader native validation |
| Towns and castles | Entry/exit, representative movement and castle quest interaction | Not exhaustive coverage of shops, NPCs, combat or quest conditions |
| Dungeons | Entry, initial movement/facing, entrance ladder exit and save restriction | Deep-floor and combat/container coverage remains partial |
| Space | Controlled boarding, directions/fuel, V/F/V and controlled landing | Natural shuttle acquisition, docking, aimed kills and long navigation sessions remain open |
| Time machine and ending | Opening pages, movement, controlled gem/combat/victory path and NIF rendering | Test supplies prerequisites; automated victory lowers boss HP and raises player HP |
| Sound | Nine original shared effects render PCM; two exact edge-interval comparisons | Actual output requires listening; full event coverage and bus-cycle timing are not established |
| Native UI | AppKit window, keyboard, scaling, playback/mute controls and isolated tests | Automated validation is headless; desktop interaction is checked manually |

Detailed reports: [startup](native-startup.md),
[character creation](native-character-creation.md), [Sosaria](native-sosaria.md),
[towns](native-town.md), [castles](native-castle.md),
[dungeons](native-dungeon.md), [space](native-space.md),
[time machine and test sessions](native-tm.md), [audio](native-audio.md).

## Deliberate changes

- Brisk instruction-budget pacing, rather than original CPU-cycle game speed.
- Native local file services replace disk swaps and ProDOS execution.
- The complete title is held until the player starts the game.
- Separate temporary test sessions let developers enter SPA/TM immediately.
  Normal-game prerequisites and the actual player record are not changed.

Original graphics, text and rules remain the intended reference. These deliberate
changes do not imply that all other differences have already been found.

## Remaining work, in priority order

1. **Normal progression:** connect validation across economy, equipment, quests,
   vehicle acquisition, space qualifications and time-machine prerequisites.
2. **Failure and recovery:** native checks for death, resource depletion, invalid
   actions, failed transactions and return/restart behavior.
3. **Space completeness:** natural navigation, docking/refuelling, aimed combat
   and return to Sosaria without approach fixtures.
4. **Presentation and input:** listen to effects during play, verify event timing,
   held/repeated/control keys and longer animation/input sessions.
5. **Distribution and maintenance:** reproducible setup on a clean machine,
   clearer dependency diagnostics, and a distribution process that keeps original
   material local. There is currently no self-contained public app release.

The original mixed code/data files are not fully semantically classified.
Speculative Ghidra coverage, reviewed assembly coverage and exercised gameplay
coverage must not be reported as the same completion percentage.

## Reproduce available checks

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_audio.py
python3 tools/check_all.py
```

The full suite requires private baseline inputs and reference captures in
addition to the game extraction. A clean clone cannot reproduce those comparisons
until the local evidence has been collected. Some checks report `PENDING` when
references are absent: **a successful exit is not proof that every check ran**.
See the [developer guide](../CONTRIBUTING.md) for setup and evidence handling.
