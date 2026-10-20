# TWN — town gameplay

Overlay range: `$8956–$AA62`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898B` | `JSR $B733`; inline `TCMAPS` at `$898E` | Town map file request; runtime file match |
| `$89A1` | `JSR $B733`; inline `MAPCHARS` at `$89A4` | Character graphic file request; runtime file match |
| `$89CC` | [Self-modifying map copy](TWN-map-copy.s) | First visited town copied 768 bytes from packed record 2 to `$B400–$B6FF` |
| `$8A28` / `$8A1E` | Main loop / first key poll | Reached after map setup |
| `$8ABF` | `JMP $88FB` | Return to `OUT` |
| `$932F–$9364` | [Byte-matched cost/payment and food credit](TWN-food-purchase.s) | A food-shop path checks two-byte `Coin`, subtracts cost, and adds a two-byte food quantity |

The opening code selects data from the loaded map. The food-shop fragment compares `$7ED4/$7ED5` with cost `$72/$73`; insufficient funds jump to `$9236`. The success path subtracts the cost from that same field and adds `$AA69/$AA6A` to food `$7EE5/$7EE6`. The purchase prompt preceding this path names food and a price. The status display labels `$7ED4/$7ED5` as `Coin`; see the [player state map](../docs/player-state.md). This payment path is statically verified, while its inputs, screen response, and other shop branches remain to trace at runtime.

The reviewed [map copy](TWN-map-copy.s) at `$89B9–$89DD` reassembles byte-for-byte. It reads the address table starting at entry 2, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap.

The [first town replay](../tools/verify_out_to_twn.py) began on outdoor tile code `$06` at `(29,32)`. `E` selected overlay offset `$0C` at `$9133`; all 8,461 `TWN` bytes matched at `$8956` before entry. `TCMAPS` and `MAPCHARS` both matched their extracted files after loading. At the first `$8A1E` input, `$B400–$B6FF` matched record 2's 764 bytes plus four bytes from record 3. The town-local `$00/$01` position was `(19,17)`, `Coin` was 100, and food was 194. These are observations from this one town entry.
