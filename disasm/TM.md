# TM — time machine and finale

Overlay range: `$8956–$A910`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | `JMP $8AD7` | Module entry redirects into main routine |
| `$9052` | `JSR $B703`; inline `NIF` at `$9055` | Data file request |

Visible text describes a time-machine sequence and Mondain confrontation. The controlled route into this module, its main loop, gem action, directional attack, and ending gate have now been traced. The full naturally acquired four-gem route and `NIF` structure remain open.

The main cycle starts at `$8E5E`: it resets the stack, prints a control sequence, then `$8E67` runs local `$9844` and common display `$836E`. A zero HP/food gate jumps to shared `$88F8`; otherwise `$9815` handles input and returns a key. The [40-byte dispatch](TM-command-dispatch.s) at `$8E80–$8EA7` reassembles exactly: it handles the zero-key path locally, passes a nonzero key to common `$82A2`, patches a handler call from the local table `$8EA8`, calls `$8414`, and jumps back to `$8E5E`. `$9815` uses `$15C8` and `$15BF` through `$9827`, unlike the direct `$15C2` polls in several other overlays.

Controlled selection with A=`$18` loaded all 8,123 TM bytes at `$8956`. An initial probe injected PC=`$8E5E` after loading and reached `$9815`, showing that the candidate loop was executable. The full opening sequence has since been replayed; see below.

The controlled OUT B-command transition reaches the real TM entry `$8AD7`. Four shared page prompts at `$87F7 → $881B` each accept Space with A=`$20` at `$881E`, then reach the natural `$8E5E → $9815` main loop. A further Space command decodes to X=`$08`, calls handler `$9801` through the patched `$8E9F`, and returns to the next `$9815`. The source snapshots and replays are described in [turn contracts](../docs/turn-contracts.md).

From that controlled entry, ten East inputs moved the player `(4,5)→(14,5)` through `$96C4`. The last move reduced player HP `150→109`; Mondain remained at 1000 HP. `G` then dispatched to `$94D6`, set `$95AB:0→1` at `$951A`, and returned to input with player HP 28 and Mondain at `(15,5)`. The HP loss is measured at input boundaries; the exact damage substeps have not been isolated. The [private trace verifier](../tools/verify_tm_victory_gate.py) checks every move, handler, state, and snapshot link.

`A` calls `$8EDC`, which asks for a direction through `$916F→$9815`. With East as the second key, the adjacent target was hit at `$8F80` and Mondain HP fell `1000→970`. `$8FEE` handles lethal damage, marks phase `$7EF2=$FF`, and checks `$95AB` at `$901D`. A controlled replay changed only Mondain HP from 1000 to 1 before the same two keys. With the destroyed-gem flag retained, the branch reached victory `$9034`; changing that flag to zero in a separate control reached `$9033` instead. From `$9034`, execution requested `NIF` at `$9052→$B703`, returned at `$9059`, and the full 7680 bytes at `$4000` matched the extracted file. These controls prove the gate and load path, not an uninterrupted 1000-HP battle or full ending display.

After the load, `$9073–$9093` moved **8192** bytes `$4000–$5FFF → $6000–$7FFF` exactly and cleared the source range to zero. The `NIF` file supplies the first 7680 bytes; the last 512 come from preexisting `$5E00–$5FFF` RAM, with 232 nonzero bytes in this run. The move overwrites the normal `$7E00` game state region as the ending begins. Execution reached animation `$90AA`, then final keyboard wait `$9132`. Space led to `$914D → $912F`, returning to that wait. The source and destination ranges, overread count, clearing, and key loop are checked by the same [verifier](../tools/verify_tm_victory_gate.py). The origin and visual use of the extra 512 bytes need further study.
