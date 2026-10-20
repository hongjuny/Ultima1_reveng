# OUT — outdoor gameplay

Overlay range: `$8956–$9DC3`; entry `$8956`.

The `GEN`→`OUT` handoff loaded all 5230 bytes into `$8956–$9DC3`, confirmed against the extracted file in paused runtime snapshots. The common selector returned from `$7DCC` at `$892E`, reached its final jump at `$893C`, and entered `OUT` at `$8956` (cycle 47,824,422). This successful load required preserving the Disk II head position across the emulator's player-to-game disk swap; see [STUPH](STUPH.md).

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | Reads `$7E73–$7E74` into zero-page pointers | Module entry/state restore |
| `$898A` | Reached after initial page copy with `$B600` nonzero | Initialization continued |
| `$89A1` | Main outdoor loop; calls `$836E`, then checks `$7EC6–$7EC7` and `$7EE5–$7EE6` | Health/food gate; reached at cycle 48,111,821 |
| `$8A6A–$8A75` | 12-byte bounded poll: `X=$80`, call STUPH `$15C5` (`JMP $1DA3`), decrement X on zero, return A in X | First outdoor input call reached at `$8A6C`; health `$0096`, food `$00C8` |
| `$89CB–$89DF` | Calls shared `$82A2` command lookup; carry set skips the selected handler | `P` (`$50`) took the skip branch at `$89DF`; health and food unchanged at that checkpoint |
| `$8A76–$8A7C` | `LDY #$05`; `LDA #$50`; `JMP $82E2` | Space handler: `$7EE4` `$95→$90`, `$7EDA` `$00→$50` at return; health and food unchanged |
| `$9351–$936C` | Loads `$00/$01` into X/Y; four entries decrement or increment one register, then share `$936D` | All four keys were replayed from the same `$00/$01=($27,$21)` snapshot; results are below |
| `$8D6E` | `LDA #$14`; `JMP $8EFA` | Selects `SPA` |
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

At the next poll in each replay, `$7EE4` was `$45` (from `$95`) and `$7EDB` was `$01` (from `$00`); health and food were unchanged. These observations establish one-step changes in the live zero-page coordinates and a common turn cost for this starting state. The four paths and values are checked against private snapshots by `tools/verify_out_directions.py`. Terrain restrictions, wraparound, encounters, and the conditions behind module transitions still require separate traces.

Reviewed source: [bounded key poll](OUT-key-poll.s) at `$8A6A–$8A75`, [Space handler](OUT-space-handler.s) at `$8A76–$8A7C`, [direction entries](OUT-direction-entry.s) at `$9351–$936C`, [space selector](OUT-space-dispatch.s) at `$8D6E–$8D72`, and [location selector](OUT-location-dispatch.s) at `$90FF–$9139`. All reassemble byte-for-byte. The location selector compares incoming A with `$04` and `$06`: `$04` selects `CAS`, `$06` selects `TWN` after updating `$7EB1–$7EB4`, and other values select `DNG`. The meaning of incoming A is still open.
