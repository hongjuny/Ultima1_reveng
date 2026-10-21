# DNG — dungeon gameplay

Overlay range: `$8956–$B098`; entry `$8956`.

The [private route verifier](../tools/verify_out_to_dng.py) replays 29 outdoor moves from castle tile `(30,31)` to raw tile `$0E`/code `$07` at `(43,15)`. `E` saves `(43,15)` at `$7E73–$7E74`, reaches selector `$9137` with A=`$08`, and loads `DNG`. The full 10,051 bytes at `$8956` match the extracted file before entry. This confirms one ordinary-play entry path.

Entry `$8956` initializes dungeon fields at `$A4E8–$A506`, calls `$8C5D`, and jumps into the main loop at `$8DE6`. The replay reaches `$8C5D` before the loop and finds a 121-byte area at `$B099–$B111` populated before the first key read. This address begins immediately after the file's last byte `$B098`; it is runtime state, not part of the disk payload. The first loop calls `$8982` and reaches the [byte-matched bounded key poll](DNG-key-poll.s) at `$8DDA`; the poll calls shared `$15C2` with X initially `$80` and copies the returned key value to X. Its twelve bytes reassemble exactly.

Visible text and entry code indicate dungeon levels, facing directions, encounters, and containers. At `$9725`, a direct `JMP $88FB` returns through the common `OUT` selection path. The generator's exact map encoding and seed behavior, individual commands, encounters, combat, and exit condition remain to trace.

At that first `$8DDA` poll, `W` (`$57`) was absent from the shared command table `$7E53–$7E6C`; lookup `$82A2` returned X=`$FF` and the caller returned to its input loop without changing the local dungeon position `(1,1)`. From the same snapshot, Up (`$0B`) returned command index zero. The indirect call at `$8E0B` targeted `$8E95`; its [byte-matched position commit](DNG-move-commit.s) stores candidate X/Y in `$A4E8/$A4E9`. The runtime position changed `(1,1)→(1,2)`, while facing `$A4EC/$A4ED`, HP, and food were unchanged at the handler return and the next `$8DDA` poll. The [private first-key verifier](../tools/verify_dng_first_keys.py) checks both input paths and the next poll. Other tile types, further blocked-move conditions, stair behavior, and per-turn effects remain open.

The [dungeon map format and movement record](../docs/dungeon-map.md) now covers the 11×11 working array, template copy, first observed generator seed, all four direction keys, Space, and `$00` passable versus `$01` blocked cells. The [map reader](DNG-map-access.s), [writer](DNG-map-write.s), and [candidate coordinate routine](DNG-candidate-position.s) reassemble exactly. The private verifiers check the stage snapshots and alternate movement branches.
