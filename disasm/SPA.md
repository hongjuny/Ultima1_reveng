# SPA — space gameplay

Overlay range: `$8956–$B01F`; entry `$8956`.

Entry code reads shared values near `$7EEF–$7EF0`. Visible text covers shield, fuel, docking, navigation, and spacecraft. At `$8FAA`, a direct `JMP $88FB` returns through the common `OUT` path. Resource formulas, navigation state, and the link to the time-machine sequence remain to trace.

Static control-flow review identifies the main-cycle at `$8A53`: it calls `$15C2` at `$8A5F`, processes a nonzero key with `$A1BD`, calls the shared command decoder `$82A2`, then branches into a module-local handler table at `$91D3` through a patched jump at `$8AA4`. `$8AB3` advances movement/state and several branches return to `$8A53`. The [28-byte input prefix](SPA-key-dispatch.s) reassembles exactly against `SPA`. Handler effects and exit conditions still need an emulator trace.

Controlled runtime selection with A=`$14` at common `$88FD` loaded all 9,930 bytes at `$8956` and reached `$8A53` and `$8A5F` without a PC jump after entry. This confirms the loop and input site in the current saved-player state. The natural `OUT` vehicle/launch condition, command effects, and exit remain to trace; see [turn contracts](../docs/turn-contracts.md).

A second controlled replay sent the real OUT B key after changing only the current world tile to craft code `$06`. It passed `$8D6E`, loaded SPA with all bytes matching, and reached `$8A53`. This confirms the B-command transition mechanism; the ordinary acquisition and placement of this craft remain unknown.

From that entry, Space returned through `$8A62`, decoded to X=`$08`, jumped via patched `$8AB0` to handler `$9207`, and reached `$8AB3 → $8A53 → $8A5F` for the next input. See the [first SPA turn](../docs/turn-contracts.md). Other movement, fuel, shield, docking, and exit rules remain to trace.

## Direction controls and fuel: byte-matched static contract

[Direction handlers and delta tables](SPA-direction-controls.s) match all 237 bytes at `$8FAD–$9099`. The shared key table sends Up, Down, Right, Left to `$8FAD`, `$900E`, `$904E`, `$9074` respectively. `$923F` indexes the four direction deltas. Up adds `(0,-1),(+2,0),(0,+1),(-2,0)` to `$928A/$928B`; Down adds the opposite vectors. Each coordinate passes through `$8FFC`, which leaves the signed byte within `-8..+8` and clamps values outside that interval to `$F8` or `$08`. This is a bound on these **local coordinates**, not evidence of the universe's map size. The caller must keep `$923F` in `0..3`; this fragment does not enforce the index bound.

Right writes `($923F+1)&3` to `$923E`; Left writes `$923F-1` with `0→3` wrap. Both reset `$928E` and route to `$8AB8`. Up refuses movement when `$9240` is nonzero, calling the `$15CB` sound vector before `$8BB5`; Right and Left take the same gate without that sound call. Down has no `$9240` gate in its entry and clears `$9240` and `$928E` after coordinate update. The meanings of `$9240` and the distinction between current `$923F` and pending `$923E` heading need runtime verification. These handlers also call `$8119` with three inline display bytes; those bytes are not 6502 instructions.

[Fuel debit and status refresh](SPA-fuel-status.s) match another 105 bytes at `$A154–$A1BC`. A direction move calls `$A154` with A=`5`; a turn uses A=`2`. The routine subtracts A from little-endian `$7EE9/$7EEA`, clamps an underflow to zero, and zeroes `$928E` when fuel reaches zero. The nearby status label says `Shld|Fuel`; the redraw reads `$7EEB/$7EEC` first and `$7EE9/$7EEA` second, supporting **Shield** and **Fuel** respectively as a static interpretation. It then reads `$7EE7/$7EE8` and Coin `$7ED4/$7ED5`. The third resource's label and meaning remain open. A move/turn's full visible effect, fuel insufficiency behavior before handler entry, and status timing still need emulator replay; the byte-matched source alone does not establish them.
