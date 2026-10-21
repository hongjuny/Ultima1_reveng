# SPA — space gameplay

Overlay range: `$8956–$B01F`; entry `$8956`.

Entry code reads shared values near `$7EEF–$7EF0`. Visible text covers shield, fuel, docking, navigation, and spacecraft. At `$8FAA`, a direct `JMP $88FB` returns through the common `OUT` path. Resource formulas, navigation state, and the link to the time-machine sequence remain to trace.

Static control-flow review identifies the main-cycle at `$8A53`: it calls `$15C2` at `$8A5F`, processes a nonzero key with `$A1BD`, calls the shared command decoder `$82A2`, then branches into a module-local handler table at `$91D3` through a patched jump at `$8AA4`. `$8AB3` advances movement/state and several branches return to `$8A53`. The [28-byte input prefix](SPA-key-dispatch.s) reassembles exactly against `SPA`. Handler effects and exit conditions still need an emulator trace.

Controlled runtime selection with A=`$14` at common `$88FD` loaded all 9,930 bytes at `$8956` and reached `$8A53` and `$8A5F` without a PC jump after entry. This confirms the loop and input site in the current saved-player state. The natural `OUT` vehicle/launch condition, command effects, and exit remain to trace; see [turn contracts](../docs/turn-contracts.md).
