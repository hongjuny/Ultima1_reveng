# TWN — town gameplay

Overlay range: `$8956–$AA62`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898B` | `JSR $B733`; inline `TCMAPS` at `$898E` | Town map file request |
| `$89A1` | `JSR $B733`; inline `MAPCHARS` at `$89A4` | Character graphic file request |
| `$8ABF` | `JMP $88FB` | Return to `OUT` |

The opening code selects data from the loaded map; the map index, trading rules, and combat behavior remain to trace.

The reviewed [map copy](TWN-map-copy.s) at `$89B9–$89DD` reassembles byte-for-byte. It reads the address table starting at entry 2, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap.
