# CAS — castle gameplay

Overlay range: `$8956–$9EE9`; entry `$8956`.

Runtime entry confirmed from `OUT`: an 11-move route reached decoded tile `$04` at coordinates `($1E,$1F)`. The `E` command saved those coordinates at `$7E73/$7E74`, selected A=`$10`, copied filename `CAS`, and reached `$8956` after a carry-clear load. All 5,524 overlay bytes matched the local extraction at entry.

The continuation reached the `TCMAPS` request at `$898D`, the `MAPCHARS` request at `$89A3`, the map-copy loop at `$89CE`, the main loop at `$8A31`, and the first key poll at `$8A27` (cycle 57,858,103). Both data files still match the extraction in their loaded memory ranges. The copy placed bytes `$4014–$4313` at `$B400–$B6FF`: 764 bytes of packed record 0 plus the first four bytes of record 1. [The snapshot verifier](../tools/verify_cas_first_input.py) checks the files, copy, and first input. The input commands and castle state changes remain to trace.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898D` | `JSR $B733`; inline `TCMAPS` at `$8990` | Castle map file request |
| `$89A3` | `JSR $B733`; inline `MAPCHARS` at `$89A6` | Character graphic file request |
| `$8BFD` | `JMP $88FB` | Return to `OUT` |

Visible text includes a princess sequence, shops, and combat. The state changes associated with these events remain to trace.

The reviewed [map copy](CAS-map-copy.s) at `$89BB–$89DF` reassembles byte-for-byte. It reads the address table starting at entry 0, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap.
