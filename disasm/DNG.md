# DNG — dungeon gameplay

Overlay range: `$8956–$B098`; entry `$8956`.

The [private route verifier](../tools/verify_out_to_dng.py) replays 29 outdoor moves from castle tile `(30,31)` to raw tile `$0E`/code `$07` at `(43,15)`. `E` saves `(43,15)` at `$7E73–$7E74`, reaches selector `$9137` with A=`$08`, and loads `DNG`. The full 10,051 bytes at `$8956` match the extracted file before entry. This confirms one ordinary-play entry path.

Entry `$8956` initializes dungeon fields at `$A4E8–$A506`, calls `$8C5D`, and jumps into the main loop at `$8DE6`. The replay reaches `$8C5D` before the loop and finds a 121-byte area at `$B099–$B111` populated before the first key read. This address begins immediately after the file's last byte `$B098`; it is runtime state, not part of the disk payload. The first loop calls `$8982` and reaches the [byte-matched bounded key poll](DNG-key-poll.s) at `$8DDA`; the poll calls shared `$15C2` with X initially `$80` and copies the returned key value to X. Its twelve bytes reassemble exactly.

Visible text and entry code indicate dungeon levels, facing directions, encounters, and containers. At `$9725`, a direct `JMP $88FB` returns through the common `OUT` selection path. The generator's exact map encoding and seed behavior, individual commands, encounters, combat, and exit condition remain to trace.
