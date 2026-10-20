# CAS — castle gameplay

Overlay range: `$8956–$9EE9`; entry `$8956`.

Runtime entry confirmed from `OUT`: an 11-move route reached decoded tile `$04` at coordinates `($1E,$1F)`. The `E` command saved those coordinates at `$7E73/$7E74`, selected A=`$10`, copied filename `CAS`, and reached `$8956` after a carry-clear load. All 5,524 overlay bytes matched the local extraction at entry.

The continuation reached the `TCMAPS` request at `$898D`, the `MAPCHARS` request at `$89A3`, the map-copy loop at `$89CE`, the main loop at `$8A31`, and the first key poll at `$8A27` (cycle 57,858,103). Both data files still match the extraction in their loaded memory ranges. The copy placed bytes `$4014–$4313` at `$B400–$B6FF`: 764 bytes of packed record 0 plus the first four bytes of record 1. [The snapshot verifier](../tools/verify_cas_first_input.py) checks the files, copy, and first input.

At that first poll, left key `$08` returned through the command lookup with X=`$06` and called `$8AA8`. The player was at castle coordinate `($00,$09)`; the shared left-edge test at `$8AB3` read `$B6BD=$23`, passed its `>= $05` check, and jumped through `$8BFD → $88FB` to select `OUT` (A=`$04`). The `OUT` loader returned with carry clear and all 5,230 overlay bytes matched before entry. At its next `$8A6C` poll, outdoor coordinates were restored to `($1E,$1F)` and health/food matched the pre-castle snapshot. [The return verifier](../tools/verify_cas_exit_left.py) checks the complete ancestry and state. Other castle commands and left-edge conditions remain to trace.

From the same first poll, right key `$15` dispatched to `$8AA1` and proposed `($01,$09)` at `$8C00`. Collision routine `$9BC0` returned A=`$60`, carry set at `$8C11`, so `$8C29` committed the new x coordinate. The update at `$8C3F` changed `$7EE4` `$45→$44` and `$7EDA` `$00→$10`. Health and food did not change before the next `$8A27` poll. The [right-step verifier](../tools/verify_cas_step_right.py) checks this path. Blocked movement and other castle interactions remain open.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898D` | `JSR $B733`; inline `TCMAPS` at `$8990` | Castle map file request |
| `$89A3` | `JSR $B733`; inline `MAPCHARS` at `$89A6` | Character graphic file request |
| `$8BFD` | `JMP $88FB` | Return to `OUT` |
| `$8A25–$8A30` | Bounded key poll, byte-matched | First input reached at `$8A27` |
| `$8AA8–$8AC0` | Left-key entry and x=0 edge test, byte-matched | `$B6BD=$23` selected `$8BFD` in first-entry replay |
| `$8C00–$8C12` | Candidate coordinates and `$9BC0` collision call, byte-matched | `$15` proposed `($01,$09)`; carry set accepted it |
| `$8C29–$8C4B` | Coordinate commit, screen update, shared turn update, byte-matched | `$00/$01=($01,$09)` and `$7EE4/$7EDA` changed |

Visible text includes a princess sequence, shops, and combat. The state changes associated with these events remain to trace.

The reviewed [map copy](CAS-map-copy.s) at `$89BB–$89DF` reassembles byte-for-byte. It reads the address table starting at entry 0, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap. The [key poll](CAS-key-poll.s), [left-edge exit](CAS-left-edge.s), [movement check](CAS-move-check.s), and [movement commit](CAS-move-commit.s) also reassemble byte-for-byte.
