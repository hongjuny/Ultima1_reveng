# TWN — town gameplay

Overlay range: `$8956–$AA62`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898B` | `JSR $B733`; inline `TCMAPS` at `$898E` | Town map file request |
| `$89A1` | `JSR $B733`; inline `MAPCHARS` at `$89A4` | Character graphic file request |
| `$8ABF` | `JMP $88FB` | Return to `OUT` |

The opening code selects data from the loaded map; the map index, trading rules, and combat behavior remain to trace.
