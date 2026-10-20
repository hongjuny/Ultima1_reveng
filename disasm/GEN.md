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
