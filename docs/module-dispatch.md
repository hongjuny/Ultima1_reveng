# Gameplay module dispatch

Status: static trace of `MI.U1` and one exit path in `OUT`; runtime confirmed through `MI.U1` entry, with its `STUPH` and `GEN` loads pending.

`MI.U1` stores null-terminated module names starting at `$7E16`. Their byte offsets are the likely selector values:

| Value in A | Name | Entry after load |
| ---: | --- | --- |
| `$00` | `GEN` | `$8956` |
| `$04` | `OUT` | `$8956` |
| `$08` | `DNG` | `$8956` |
| `$0C` | `TWN` | `$8956` |
| `$10` | `CAS` | `$8956` |
| `$14` | `SPA` | `$8956` |
| `$18` | `TM` | `$8956` |

At `$88FD`, `MI.U1` resets the stack pointer. A value of zero or at least `$19` takes the `GEN` load path. For values from `$01` through `$18`, the routine treats A as a byte offset into the name table, copies the selected null-terminated name to `$7E16`, and invokes the file loader with that address. After several shared setup calls it jumps to `$8956`. The named offsets above align exactly with the table; whether all intermediate values can occur needs runtime verification.

The initial `MI.U1` entry at `$7000` jumps to `$8956`. This first version of `$8956` loads `STUPH`, sets up shared support state, and reaches `$88FD` with A = 0, selecting `GEN`. The loaded `GEN` file then replaces this loader code at `$8956`.

The shared entry at `$88F8` performs setup, while `$88FB` sets A to `$04` and selects `OUT` at `$88FD`. Direct jumps to `$88FB` appear in `GEN` (`$8AC0`), `DNG` (`$9725`), `TWN` (`$8ABF`), `CAS` (`$8BFD`), and `SPA` (`$8FAA`). These are observed routes back to outdoor play. The conditions that reach each jump still need tracing.

`OUT` uses its own transition routine at `$8EFA`. It saves two zero-page bytes at `$7E73–$7E74`, performs a page-copy loop using modified operands, restores A, and jumps to `$88FD` at `$8F1C`. Two callers make the next state visible:

| Call site in `OUT` | Selector in A | Next module |
| --- | ---: | --- |
| `$8D6E` | `$14` | `SPA` |
| `$90FF–$9137` | `$10`, `$0C`, or `$08` | `CAS`, `TWN`, or `DNG` |

The meaning of the saved bytes and the gameplay conditions behind these selections remain open. The reviewed `$90FF–$9139` source confirms the exact cases: incoming A = `$04` selects `CAS`; A = `$06` updates `$7EB1–$7EB4` and selects `TWN`; all other values select `DNG`. Incoming A likely encodes a location type, but that interpretation needs confirmation.

The `$88FD` selector is a strong boundary for tracing game transitions. For each module, identify the value placed in A before reaching it and record any shared state changes before the jump.
