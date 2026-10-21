# TM — time machine and finale

Overlay range: `$8956–$A910`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | `JMP $8AD7` | Module entry redirects into main routine |
| `$9052` | `JSR $B703`; inline `NIF` at `$9055` | Data file request |

Visible text describes a time-machine sequence and Mondain confrontation. The route into this module, `NIF` format, final encounter logic, and completion path remain untraced.

The main cycle starts at `$8E5E`: it resets the stack, prints a control sequence, then `$8E67` runs local `$9844` and common display `$836E`. A zero HP/food gate jumps to shared `$88F8`; otherwise `$9815` handles input and returns a key. The [40-byte dispatch](TM-command-dispatch.s) at `$8E80–$8EA7` reassembles exactly: it handles the zero-key path locally, passes a nonzero key to common `$82A2`, patches a handler call from the local table `$8EA8`, calls `$8414`, and jumps back to `$8E5E`. `$9815` uses `$15C8` and `$15BF` through `$9827`, unlike the direct `$15C2` polls in several other overlays.

Controlled selection with A=`$18` loaded all 8,123 TM bytes at `$8956`. An initial probe injected PC=`$8E5E` after loading and reached `$9815`, showing that the candidate loop was executable. The full opening sequence has since been replayed; see below.

The controlled OUT B-command transition reaches the real TM entry `$8AD7`. Four shared page prompts at `$87F7 → $881B` each accept Space with A=`$20` at `$881E`, then reach the natural `$8E5E → $9815` main loop. A further Space command decodes to X=`$08`, calls handler `$9801` through the patched `$8E9F`, and returns to the next `$9815`. The source snapshots and replays are described in [turn contracts](../docs/turn-contracts.md). Normal acquisition of the craft and four prerequisite flags, final combat, and victory remain open.
