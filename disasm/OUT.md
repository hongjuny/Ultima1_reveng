# OUT — outdoor gameplay

Overlay range: `$8956–$9DC3`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | Reads `$7E73–$7E74` into zero-page pointers | Module entry/state restore |
| `$8D6E` | `LDA #$14`; `JMP $8EFA` | Selects `SPA` |
| `$8EFA` | Saves pointers, page-copies state, preserves A | Transition helper |
| `$8F1C` | `JMP $88FD` | Common overlay selector |
| `$90FF–$9137` | Sets A to `$10`, `$0C`, or `$08` before `$8EFA` | Selects `CAS`, `TWN`, or `DNG` |

The conditions behind these transitions and the outdoor movement/combat routines remain to trace. This module is the hub for the game-state graph.

Reviewed source: [space selector](OUT-space-dispatch.s) at `$8D6E–$8D72`, and [location selector](OUT-location-dispatch.s) at `$90FF–$9139`. Both reassemble byte-for-byte. The latter compares incoming A with `$04` and `$06`: `$04` selects `CAS`, `$06` selects `TWN` after updating `$7EB1–$7EB4`, and other values select `DNG`. The meaning of incoming A is still open.
