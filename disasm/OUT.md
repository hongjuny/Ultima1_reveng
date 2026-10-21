# OUT — outdoor gameplay

Overlay range: `$8956–$9DC3`; entry `$8956`.

The `GEN`→`OUT` handoff loaded all 5230 bytes into `$8956–$9DC3`, confirmed against the extracted file in paused runtime snapshots. The common selector returned from `$7DCC` at `$892E`, reached its final jump at `$893C`, and entered `OUT` at `$8956` (cycle 47,824,422). This successful load required preserving the Disk II head position across the emulator's player-to-game disk swap; see [STUPH](STUPH.md).

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | Reads `$7E73–$7E74` into zero-page pointers | Module entry/state restore |
| `$898A` | Reached after initial page copy with `$B600` nonzero | Initialization continued |
| `$898A–$8994` | [Byte-matched HP gate](OUT-death-gate.s) | Zero HP branches to resurrection at `$89E8` |
| `$89E8–$8A1C` | [Byte-matched resurrection setup](OUT-resurrection-init.s) | Repositions player via `$9461` and clears selected state fields |
| `$8A3A–$8A5E` | [Byte-matched HP/food loops](OUT-resurrection-fill.s) | In the controlled death replay, fills each low byte to `$63` |
| `$89A1` | Main outdoor loop; calls `$836E`, then checks `$7EC6–$7EC7` and `$7EE5–$7EE6` | Health/food gate; reached at cycle 48,111,821 |
| `$8A6A–$8A75` | 12-byte bounded poll: `X=$80`, call STUPH `$15C5` (`JMP $1DA3`), decrement X on zero, return A in X | First outdoor input call reached at `$8A6C`; health `$0096`, food `$00C8` |
| `$89CB–$89DF` | Calls shared `$82A2` command lookup; carry set skips the selected handler | `P` (`$50`) took the skip branch at `$89DF`; health and food unchanged at that checkpoint |
| `$8A76–$8A7C` | `LDY #$05`; `LDA #$50`; `JMP $82E2` | Space handler: `$7EE4` `$95→$90`, `$7EDA` `$00→$50` at return; health and food unchanged |
| `$92CA–$92DF` | [Byte-matched Q save](OUT-Q-save.s): store outdoor coordinates, call `$83B4`, then `$B724` with inline source `$7E6D`, length `$01CA`, path pointer `$7E38` | Outdoor `Q` saves the 458-byte player record |
| `$9927–$9957` | [Byte-matched object insertion](OUT-object-insert.s): bound coordinates and count, fill four parallel arrays, replace one map cell | Dynamic outdoor objects occupy 80 slots in the saved player record |
| `$9351–$936C` | Loads `$00/$01` into X/Y; four entries decrement or increment one register, then share `$936D` | All four keys were replayed from the same `$00/$01=($27,$21)` snapshot; results are below |
| `$99D1–$99F7` | Bounds X/Y to `$00–$3F`, reads `$6000 + Y×64 + X`, restores Y through a patched immediate operand, then shifts the byte right | All four direction replays reached this lookup; each read raw `$02` and returned tile code `$01` |
| `$90C8–$90DC` | E saves `$00/$01` to `$7E73/$7E74`, calls `$99F8` for the current tile, and admits codes `$04–$07` | On code `$04` at `($1E,$1F)`, runtime reached `$90FF`, chose A=`$10`, and entered `CAS` |
| `$8D6E` | `LDA #$14`; `JMP $8EFA` | Selects `SPA` |
| `$8D61–$8D8D` | [B-command boarding gate](OUT-board-transition.s) | Craft code `$06` selects `SPA`; `$07+` with `$7E75–$7E78` set selects `TM` |
| `$913A–$9169` | Landmark match and state write, statically checked | Completes a positive even-numbered castle quest by storing `$FF` |
| `$9565–$9596` | One-shot `$7EB5` check and `$0F` craft placement, statically checked | After a qualifying `CAS` exit, creates raw `$1E` world tile and clears the request |
| `$9927–$9958` | Dynamic world-object writer, statically checked | Doubles a tile code, saves prior map cell, and writes the new raw tile |

The [landmark quest replay](../tools/verify_out_landmark_quest.py) changed only starting coordinates to a real map tile `(59,3)` and quest byte `$7EA9` from 0 to accepted state 1. Ordinary `E` input reached `$913A`, selected location id 2, and changed that quest byte to `$FF` at `$915F`. This validates one even-quest producer with controlled prerequisites; the normal route to that landmark remains open.

From the first ordinary outdoor Space turn, `Q` mapped through command index `$24` and pointer `$9ACE` to `$92CA`. The save call returned at `$92E0` with carry clear on a disposable `U1.PLAYER` disk. The new `U1.VARS` differed from GEN's initial save only at `$7EDA:00→50` and `$7EE4:95→90`, matching the live record at the save call byte-for-byte. A separate GEN menu `B` reload read this new file at `$6000`, copied all 458 bytes to `$7E6D–$8036`, and reached the OUT handoff. The [save/reload verifier](../tools/verify_out_player_save_reload.py) checks the input, code bytes, file extraction, RAM, and snapshot ancestry. The continuation after the Q save message, additional fields, and failure behavior remain untraced.
| `$8EFA` | Saves pointers, page-copies state, preserves A | Transition helper |
| `$8F1C` | `JMP $88FD` | Common overlay selector |
| `$90FF–$9137` | Sets A to `$10`, `$0C`, or `$08` before `$8EFA` | Selects `CAS`, `TWN`, or `DNG` |

The four direction keys returned through `$89DF → $8995 → $89A1 → $8A6C`:

| Key | Handler | `$00/$01` after command |
| --- | --- | --- |
| `$0B` | `$9357` | `($27,$20)` |
| `$0A` | `$935D` | `($27,$22)` |
| `$15` | `$9363` | `($28,$21)` |
| `$08` | `$9369` | `($26,$21)` |

At the next poll in each replay, `$7EE4` was `$45` (from `$95`) and `$7EDB` was `$01` (from `$00`); health and food were unchanged. These observations establish one-step changes in the live zero-page coordinates and a common turn cost for this starting state. At `$99F6`, the runtime pointer and X register addressed the expected byte in the `$6000` map; a single `LSR A` yielded `$01`. The four paths and values are checked against private snapshots by `tools/verify_out_directions.py`. Terrain restrictions, wraparound, encounters, and the conditions behind module transitions still require separate traces.

A second `$0A` move from `($27,$22)` entered raw tile `$04`/code `$02` at `($27,$23)`; food changed `$C8→$C7` while health stayed unchanged. An 11-move path from the first outdoor input reached raw tile `$08`/code `$04` at `($1E,$1F)` and remained in `OUT` at its next key poll. Pressing `E` there dispatched to `$90C8`; it saved the coordinates, read code `$04`, selected A=`$10` through `$90FF–$9137`, and loaded `CAS`. The entire 5,524-byte `CAS` overlay matched the extracted file at `$8956` before entry. [The route verifier](../tools/verify_out_terrain_entry.py) checks the private snapshots and exact handoff. Other terrain codes and entry conditions remain to test.

The [controlled lethal guard replay](../tools/verify_cas_guard_death.py) returned from `CAS` to selector `$88FD` with A=`$04`, then loaded all 5,230 bytes of `OUT` exactly. It entered `OUT` with saved outdoor coordinates `(30,31)` and zero HP/food. At `$898A`, zero HP selected `$89E8`; `$9461` returned new coordinates `(3,8)`, and the loops at `$8A3A/$8A47` filled HP and food to `$0063` each. The next `$8A6C` poll had those values. The replay changed one private HP byte before lethal subtraction, so this confirms the death branch's behavior for that controlled state. The [player-record comparison](../docs/player-state.md) identifies the six bytes changed across this path and the 452 that matched; other death states and penalties remain open.

From the same 11-move route to the castle tile `(30,31)`, left and down reached `(29,32)`, whose raw tile `$0C` decodes to code `$06`. Pressing `E` selected A=`$0C` at `$9133` and entered `TWN` after its 8,461-byte overlay matched. The [town-route verifier](../tools/verify_out_to_twn.py) checks the exact input and snapshot chain.

The [dungeon-route verifier](../tools/verify_out_to_dng.py) replays 29 moves from the castle tile to raw `$0E`/code `$07` at `(43,15)`. `E` saved those coordinates and reached `$9137` with A=`$08`, then the common loader installed all 10,051 bytes of `DNG` exactly. Its generator and first key poll are described in [DNG](DNG.md).

Reviewed source: [bounded key poll](OUT-key-poll.s) at `$8A6A–$8A75`, [Space handler](OUT-space-handler.s) at `$8A76–$8A7C`, [E gate](OUT-enter-gate.s) at `$90C8–$90DC`, [direction entries](OUT-direction-entry.s) at `$9351–$936C`, [tile lookup](OUT-tile-lookup.s) at `$99D1–$99F7`, [death HP gate](OUT-death-gate.s) at `$898A–$8994`, [resurrection setup](OUT-resurrection-init.s) at `$89E8–$8A1C`, [HP/food fill](OUT-resurrection-fill.s) at `$8A3A–$8A5E`, [space selector](OUT-space-dispatch.s) at `$8D6E–$8D72`, and [location selector](OUT-location-dispatch.s) at `$90FF–$9139`. All reassemble byte-for-byte. The location selector compares the decoded tile code with `$04` and `$06`: `$04` selects `CAS`, `$06` selects `TWN` after updating `$7EB1–$7EB4`, and other values select `DNG`. The `$04`, `$06`, and `$07` cases are runtime confirmed. The `$05` case remains untested.
