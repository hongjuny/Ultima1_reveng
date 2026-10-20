# TWN — town gameplay

Overlay range: `$8956–$AA62`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898B` | `JSR $B733`; inline `TCMAPS` at `$898E` | Town map file request |
| `$89A1` | `JSR $B733`; inline `MAPCHARS` at `$89A4` | Character graphic file request |
| `$8ABF` | `JMP $88FB` | Return to `OUT` |
| `$932F–$9364` | [Byte-matched cost/payment and food credit](TWN-food-purchase.s) | A food-shop path checks two-byte `Coin`, subtracts cost, and adds a two-byte food quantity |

The opening code selects data from the loaded map. The food-shop fragment compares `$7ED4/$7ED5` with cost `$72/$73`; insufficient funds jump to `$9236`. The success path subtracts the cost from that same field and adds `$AA69/$AA6A` to food `$7EE5/$7EE6`. The purchase prompt preceding this path names food and a price. The status display labels `$7ED4/$7ED5` as `Coin`; see the [player state map](../docs/player-state.md). This payment path is statically verified, while its inputs, screen response, and other shop branches remain to trace at runtime.

The reviewed [map copy](TWN-map-copy.s) at `$89B9–$89DD` reassembles byte-for-byte. It reads the address table starting at entry 2, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap.
