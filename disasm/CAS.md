# CAS — castle gameplay

Overlay range: `$8956–$9EE9`; entry `$8956`.

Runtime entry confirmed from `OUT`: an 11-move route reached decoded tile `$04` at coordinates `($1E,$1F)`. The `E` command saved those coordinates at `$7E73/$7E74`, selected A=`$10`, copied filename `CAS`, and reached `$8956` after a carry-clear load. All 5,524 overlay bytes matched the local extraction at entry.

The continuation reached the `TCMAPS` request at `$898D`, the `MAPCHARS` request at `$89A3`, the map-copy loop at `$89CE`, the main loop at `$8A31`, and the first key poll at `$8A27` (cycle 57,858,103). Both data files still match the extraction in their loaded memory ranges. The copy placed bytes `$4014–$4313` at `$B400–$B6FF`: 764 bytes of packed record 0 plus the first four bytes of record 1. [The snapshot verifier](../tools/verify_cas_first_input.py) checks the files, copy, and first input.

At that first poll, left key `$08` returned through the command lookup with X=`$06` and called `$8AA8`. The player was at castle coordinate `($00,$09)`; the shared left-edge test at `$8AB3` read `$B6BD=$23`, passed its `>= $05` check, and jumped through `$8BFD → $88FB` to select `OUT` (A=`$04`). The `OUT` loader returned with carry clear and all 5,230 overlay bytes matched before entry. At its next `$8A6C` poll, outdoor coordinates were restored to `($1E,$1F)` and health/food matched the pre-castle snapshot. [The return verifier](../tools/verify_cas_exit_left.py) checks the complete ancestry and state. Other castle commands and left-edge conditions remain to trace.

From the same first poll, right key `$15` dispatched to `$8AA1` and proposed `($01,$09)` at `$8C00`. Collision routine `$9BC0` returned A=`$60`, carry set at `$8C11`, so `$8C29` committed the new x coordinate. The update at `$8C3F` changed `$7EE4` `$45→$44` and `$7EDA` `$00→$10`. Health and food did not change before the next `$8A27` poll. The [right-step verifier](../tools/verify_cas_step_right.py) checks this path.

Two `$0A` keys from the first poll tested both sides of a wall. The first reached `($00,$0A)` on tile `$60`: `$9BC0` returned A=`$60`, carry set, and `$8C29` committed the step. The second proposed `($00,$0B)` on tile `$40`: `$9BC0` returned A=`$40`, carry clear, and the branch at `$8C13` kept the player at `($00,$0A)`. Both paths reached the common turn update `$8C3F`. For the blocked input, `$7EE4` changed `$44→$43` and `$7EDA` `$10→$20`; health and food remained stable through the next poll. The [two-step verifier](../tools/verify_cas_blocked_down.py) checks the snapshots, branch path, map bytes, and state. Other castle interactions and occupant collision outcomes remain open.

The [tile check](CAS-map-tile-check.s) at `$9BD9–$9BFD` bounds x to 0–37 and y to 0–17, patches a row address from tables `$9EA8/$9EBA`, and compares the map byte with `$60`. A byte below `$60` returns with carry clear; a byte at least `$60` continues to the later occupant scan at `$9BFE`. The two observed tiles follow these paths. The `$40` result alone does not describe all possible collision causes.

From the accepted right-step snapshot at `($01,$09)`, three `$0B` inputs moved to `($01,$08)`, then `($01,$07)`, then attempted `($01,$06)`. The last target's map tile was `$60`, but actor slot 2 in `$B6BC/$B6CC` also held `($01,$06)`, with type `$03` in `$B6AC`. The collision routine returned A=`$33` (`$30 + type`) and carry clear at `$8C11`. The blocked branch `$8C13` kept the player at `($01,$07)` and still reached turn update `$8C3F`: `$7EE4` `$42→$41`, `$7EDA` `$30→$40`, with health/food unchanged. The [actor collision verifier](../tools/verify_cas_occupied_tile.py) checks this three-input ancestry and both the map and actor table in the private snapshots.

The byte-matched [actor lookup](CAS-actor-lookup.s) at `$9BFE–$9C22` scans 16 slots from index 15 down to 0 after the tile threshold passes. A matching x/y pair stores its index at `$9E36` and returns `$30 + type` with carry clear. With no matching actor, it restores the tile byte to A and returns carry set. The [collision wrapper](CAS-collision-wrapper.s) at `$9BC0–$9BD8` passes through a carry-clear failure and, on carry set, also compares the proposed coordinate with the current coordinate before accepting it. The occupied-tile replay confirms slot 2's match; the remaining actor types and their interactions require separate traces.

From `(1,7)` facing the same actor, command `A` (`$41`) dispatched through pointer-table offset `$0C` to `$8C56`. Its direction prompt accepted Up (`$0B`), and the scan at `$8CC9` tested `(1,6)`. The collision result A=`$33` selected the actor branch at `$8D08` and retained actor index 2. The first hit roll was `$85`, below the threshold `$80 + $7ECA` = `$A3`, so execution reached `$8D27` and the damage path `$8D71`. Actor HP at `$B6DE/$B6EE` fell from `$01F4` to `$01DA` (26) by the handler return `$8A59`. Player HP was still `$0096` at that point, then was `$0087` at the next `$8A27` poll. The actor remained at `(1,6)`, player at `(1,7)`, food and the watched turn bytes unchanged. The [attack verifier](../tools/verify_cas_attack.py) checks both private snapshots and the return checkpoint. Alternative hit/miss outcomes remain to trace.

The post-handler call at `$8A59` entered `$9804` with `$9E2A=$01`. This replay selected the guard response at `$9933`, then the hit branch `$998F`: random A=`$9D` was at least the computed threshold `$45` in `$72`. The damage roll stored `$0F` in `$73`, below bound `$14`. At `$99CB` player HP was still `$96`; the `STA $7EC6` at `$99D1` changed it to `$87`, observed at `$99D4`. The response then returned to the next castle key poll with the same CPU and 64 KB RAM as the earlier attack trace. The [guard verifier](../tools/verify_cas_guard_retaliation.py) checks every checkpoint, the source snapshot, and the reproduced final RAM. This confirms the guard response as the source of the 15 HP loss in this replay. Other guard outcomes and broader actor AI remain open.

The [guard hit-roll fragment](CAS-guard-hit-roll.s) at `$9951–$9980` computes a threshold from `$7ECC`, eight successive additions of `$7E7B`, and `$38`, preserving carry across ADC operations. The [damage-roll fragment](CAS-guard-damage-roll.s) at `$998F–$99A5` repeatedly draws a nonzero byte below `$14 + 4×$7EC7` in this code path. The [HP fragment](CAS-guard-player-hp.s) at `$99CB–$99E0` subtracts that byte from the player's two-byte HP and branches to the death path on borrow. All three fragments reassemble byte-for-byte.

Three attack fragments reassemble byte-for-byte: the [directional scan](CAS-attack-ray.s) at `$8CC9–$8CF6` advances by `$04/$05` and accepts actor result codes `$30–$35`; the [hit roll](CAS-attack-hit-roll.s) at `$8D08–$8D2B` compares a random byte with `$80 + $7ECA`; the [damage calculation](CAS-attack-damage.s) at `$8D46–$8D83` builds a bound with `$7EC8` and three successive `ADC $7E7A` operations, draws a nonzero byte below that bound, and subtracts it from the selected actor's HP. The ADC chain preserves carry between operations. In this replay the subtraction was 26; other weapon values and actor states still need testing.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898D` | `JSR $B733`; inline `TCMAPS` at `$8990` | Castle map file request |
| `$89A3` | `JSR $B733`; inline `MAPCHARS` at `$89A6` | Character graphic file request |
| `$8BFD` | `JMP $88FB` | Return to `OUT` |
| `$8A25–$8A30` | Bounded key poll, byte-matched | First input reached at `$8A27` |
| `$8AA8–$8AC0` | Left-key entry and x=0 edge test, byte-matched | `$B6BD=$23` selected `$8BFD` in first-entry replay |
| `$8C00–$8C12` | Candidate coordinates and `$9BC0` collision call, byte-matched | `$15` proposed `($01,$09)`; carry set accepted it |
| `$8C29–$8C4B` | Coordinate commit, screen update, shared turn update, byte-matched | `$00/$01=($01,$09)` and `$7EE4/$7EDA` changed |
| `$9BD9–$9BFD` | Row lookup, bounds, tile threshold, byte-matched | Tile `$40` returned carry clear at the wall; `$60` continued to occupant scan |
| `$9BFE–$9C22` | 16-slot actor lookup, byte-matched | Slot 2/type 3 at `(1,6)` returned A=`$33`, carry clear |
| `$9BC0–$9BD8` | Collision result wrapper, byte-matched | Carry-clear result blocks movement; carry-set result gets current-position check |
| `$8CC9–$8CF6` | Directional attack scan, byte-matched | Up selected actor slot 2 at `(1,6)` |
| `$8D08–$8D2B` | Actor type and hit roll, byte-matched | `$85 < $A3` selected hit path |
| `$8D46–$8D83` | Damage roll and HP subtraction, byte-matched | Actor HP fell by 26 |
| `$9951–$9980` | Guard hit threshold and roll, byte-matched | `$9D >= $45` selected hit path |
| `$998F–$99A5` | Guard damage bound and nonzero roll, byte-matched | `$0F` selected below `$14` |
| `$99CB–$99E0` | Player HP subtraction, byte-matched | `$99D1` stored `$96→$87` |
| `$8C13–$8C28` | Collision-failure message and jump to `$8C3F` | Blocked movement still consumes a turn in this replay |

Visible text includes a princess sequence, shops, and combat. The state changes associated with these events remain to trace.

The reviewed [map copy](CAS-map-copy.s) at `$89BB–$89DF` reassembles byte-for-byte. It reads the address table starting at entry 0, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap. The [key poll](CAS-key-poll.s), [left-edge exit](CAS-left-edge.s), [movement check](CAS-move-check.s), [tile check](CAS-map-tile-check.s), [actor lookup](CAS-actor-lookup.s), [collision wrapper](CAS-collision-wrapper.s), and [movement commit](CAS-move-commit.s) also reassemble byte-for-byte.
