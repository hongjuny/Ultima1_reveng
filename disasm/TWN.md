# TWN — town gameplay

Overlay range: `$8956–$AA62`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$898B` | `JSR $B733`; inline `TCMAPS` at `$898E` | Town map file request; runtime file match |
| `$89A1` | `JSR $B733`; inline `MAPCHARS` at `$89A4` | Character graphic file request; runtime file match |
| `$89CC` | [Self-modifying map copy](TWN-map-copy.s) | First visited town copied 768 bytes from packed record 2 to `$B400–$B6FF` |
| `$8A28` / `$8A1E` | Main loop / first key poll | Reached after map setup |
| `$9257–$926E` | [Byte-matched food-pack price](TWN-food-price.s) | Derives a 1–5 `Coin` price from `$7ED2` in 20-point steps |
| `$8ABF` | `JMP $88FB` | Return to `OUT` |
| `$932F–$9364` | [Byte-matched cost/payment and food credit](TWN-food-purchase.s) | One food pack costs 5 and credits 10 food in the traced state |

The opening code selects data from the loaded map. The food-shop fragment compares `$7ED4/$7ED5` with cost `$72/$73`; insufficient funds jump to `$9236`. The success path subtracts the cost from that same field and adds `$AA69/$AA6A` to food `$7EE5/$7EE6`. The purchase prompt preceding this path names food and a price. The status display labels `$7ED4/$7ED5` as `Coin`; see the [player state map](../docs/player-state.md).

The reviewed [map copy](TWN-map-copy.s) at `$89B9–$89DD` reassembles byte-for-byte. It reads the address table starting at entry 2, patches its own source operand, and copies 768 bytes to `$B400`. The packed pointer stride is only 764 bytes; see [TCMAPS](TCMAPS.md) for the overlap.

The [first town replay](../tools/verify_out_to_twn.py) began on outdoor tile code `$06` at `(29,32)`. `E` selected overlay offset `$0C` at `$9133`; all 8,461 `TWN` bytes matched at `$8956` before entry. `TCMAPS` and `MAPCHARS` both matched their extracted files after loading. At the first `$8A1E` input, `$B400–$B6FF` matched record 2's 764 bytes plus four bytes from record 3. The town-local `$00/$01` position was `(19,17)`, `Coin` was 100, and food was 194. These are observations from this one town entry.

The town row-pointer table `$A96D/$A97F` has offsets `0,38,…,646` for 18 rows, so visible map coordinates use a 38-byte stride. From `(19,17)`, six Up and four Right inputs reached `(23,11)` on tile `$66`. `T` dispatched through the command pointer at `$8A80` to `$9093`, and `$66` selected shop index 1 and Buy handler `$9257`. `B` opened the food quantity input. The [shop verifier](../tools/verify_twn_food_shop.py) checks the pointer tables and every private snapshot in this route.

At `$9257`, the game starts the pack price at 5, subtracts 20 repeatedly from the byte at `$7ED2`, and lowers the price by one for each successful step, with a floor of 1. The price tiers are `0–19→5`, `20–39→4`, `40–59→3`, `60–79→2`, and `80–255→1`. The traced character had `$7ED2=15`, so the observed price was 5. Controlled one-byte changes to `$7ED2` confirmed all four tier boundaries: `19/20→5/4`, `39/40→4/3`, `59/60→3/2`, `79/80→2/1`. The resulting price and its displayed digit matched at `$926F`; the [shop verifier](../tools/verify_twn_food_shop.py) checks each intervention.

Entering quantity `1` and Return made `$AA69/$AA6A=10` food and `$72/$73=5` cost. Normal purchase changed `Coin 100→95` and food `194→204`; both values stayed unchanged when a controlled snapshot set Coin to 4. With Coin set to exactly 5, the purchase succeeded and left Coin 0 and food 204. Each funds-boundary intervention changed only `$7ED4`.

Separate ordinary-input replays of quantities `2`, `6`, and `7` computed costs `10`, `30`, and `35`, credited food `20`, `60`, and `70`, and left `Coin 90/70/65` respectively. Starting from food 194, the resulting values were 214, 254, and 264. The seven-pack path stored food 264 as `$7EE5/$7EE6=($08,$01)` and retained it at the next town input, confirming carry into the high byte. Multi-digit quantities, 16-bit overflow, sell branches, and visual output remain to test.
