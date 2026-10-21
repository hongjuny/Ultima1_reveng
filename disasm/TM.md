# TM — time machine and finale

Overlay range: `$8956–$A910`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | `JMP $8AD7` | Module entry redirects into main routine |
| `$9052` | `JSR $B703`; inline `NIF` at `$9055` | Data file request |

Visible text describes a time-machine sequence and Mondain confrontation. The route into this module, `NIF` format, final encounter logic, and completion path remain untraced.

The static main-cycle candidate starts at `$8E5E`: it resets the stack, prints a control sequence, then `$8E67` runs local `$9844` and common display `$836E`. A zero HP/food gate jumps to shared `$88F8`; otherwise `$9815` handles input and returns a key. The [40-byte dispatch](TM-command-dispatch.s) at `$8E80–$8EA7` reassembles exactly: it handles the zero-key path locally, passes a nonzero key to common `$82A2`, patches a handler call from the local table `$8EA8`, calls `$8414`, and jumps back to `$8E5E`. `$9815` uses `$15C8` and `$15BF` through `$9827`, unlike the direct `$15C2` polls in several other overlays. Natural entry into this loop and its presentation are pending.

Controlled selection with A=`$18` loaded all 8,123 TM bytes at `$8956`. Its entry animation did not reach `$8E5E` during a 15-second turbo replay. A separate probe injected PC=`$8E5E` after loading and reached `$9815`; this confirms that code path is executable with the saved player state, but does not establish a natural route through the opening sequence. See [turn contracts](../docs/turn-contracts.md).

The controlled OUT B-command transition now reaches the real TM entry `$8AD7`, then shared page prompt `$87F7` and key read `$881B`. A Space key returns A=`$20` at `$881E` and takes the accepted path `$882A`. The next prompt and natural `$8E5E` loop remain unobserved after a prolonged replay. The source snapshot and replay are described in [turn contracts](../docs/turn-contracts.md).
