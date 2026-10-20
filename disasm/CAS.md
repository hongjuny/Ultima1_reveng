# CAS — castle gameplay

Overlay range: `$8956–$9EE9`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898D` | `JSR $B733`; inline `TCMAPS` at `$8990` | Castle map file request |
| `$89A3` | `JSR $B733`; inline `MAPCHARS` at `$89A6` | Character graphic file request |
| `$8BFD` | `JMP $88FB` | Return to `OUT` |

Visible text includes a princess sequence, shops, and combat. The state changes associated with these events remain to trace.

The reviewed [map copy](CAS-map-copy.s) at `$89BB–$89DF` reassembles byte-for-byte. It reads the address table starting at entry 0, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap.
