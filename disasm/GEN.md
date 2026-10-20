# GEN — character generation

Overlay range: `$8956–$AC39`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | Initializes shared state and display | Module entry |
| `$89FD` | Reads input and compares against `#$41` and `#$42` | `A`/`B` menu choice |
| `$8AC3` | Target of the `A` branch | New-character path |
| `$8AC0` | `JMP $88FB` | Observed continue path to `OUT` |

The menu text describes new-character and previous-game options. The completion route from the new-character path, attribute generation rules, and save format remain to trace.

The reviewed [menu choice fragment](GEN-menu.s) covers `$89FD–$8A0F` and reassembles byte-for-byte. It shows `A` (`$41`) jumping to `$8AC3`; `B` (`$42`) falls into the continuation code at `$8A10`. Other values repeat the input loop.

The first runtime replay reached the key read at `$89FD` at cycle 32,493,298, before injecting a menu choice. The private snapshot confirms that the 19-byte dispatch still matches the extracted `GEN` file. `tools/verify_gen_menu.py` repeats this check locally.

The `A` replay reached `$8AC3` with `A=$41` at cycle 32,532,365. `tools/verify_gen_new_character.py` checks that snapshot and the branch-entry bytes. Static inspection of the subsequent code shows a self-modifying copy loop around `$8AE9–$8B25` and another key read at `$8C07` after on-screen instructions. The copy's actual source, destination, and state effects still need runtime confirmation.
