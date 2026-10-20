# GEN — character generation

Overlay range: `$8956–$AC39`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | Initializes shared state and display | Module entry |
| `$89FD` | Reads input and compares against `#$41` and `#$42` | `A`/`B` menu choice |
| `$8AC3` | Target of the `A` branch | New-character path |
| `$8AEA–$8B24` | Self-modifying loop, 59 reviewed bytes | Copy 136 template bytes from `$904F–$90D6` to `$7E6F–$7EF6` |
| `$8C00–$8C80` | Attribute input loop, 129 reviewed bytes | Six values, remaining-point pool, navigation and acceptance |
| `$8AC0` | `JMP $88FB` | Observed continue path to `OUT` |

The menu text describes new-character and previous-game options. The completion route from the new-character path, attribute generation rules, and save format remain to trace.

The reviewed [menu choice fragment](GEN-menu.s) covers `$89FD–$8A0F` and reassembles byte-for-byte. It shows `A` (`$41`) jumping to `$8AC3`; `B` (`$42`) falls into the continuation code at `$8A10`. Other values repeat the input loop.

The first runtime replay reached the key read at `$89FD` at cycle 32,493,298, before injecting a menu choice. The private snapshot confirms that the 19-byte dispatch still matches the extracted `GEN` file. `tools/verify_gen_menu.py` repeats this check locally.

The `A` replay reached `$8AC3` with `A=$41` at cycle 32,532,365. The next replay reached the first attribute key read at `$8C07` (cycle 33,025,684). At that point `$7EC8`, `$7ECA`, `$7ECC`, `$7ECE`, `$7ED0`, and `$7ED2` are all 10; `$903F` holds 30 unassigned points and `$9041` selects the first attribute. The private snapshots confirm the full 136-byte copy from `$904F–$90D6` to `$7E6F–$7EF6`. The reviewed [copy loop](GEN-initialize-state.s) and [attribute input loop](GEN-attribute-input.s) reassemble byte-for-byte.

The input loop uses `$9041` as a 1–6 selection index and addresses the chosen value at `$7EC6 + 2 × index`. Code `$08` lowers it down to 10 and returns one point; `$15` raises it up to 25 when points remain. Codes `$2F`/`$0A` select the next value, `$0D`/`$0B` the previous one, and `$1B` returns to the main menu. Space proceeds only when the remaining-point count is zero. These rules are established statically; runtime replay of a single `$15` increase is prepared next. The meaning and on-screen labels of all six values still need to be tied to their rendering code and observed screen.
