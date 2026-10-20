# Gameplay module dispatch

Status: runtime confirmed through `GEN`, `OUT`, and the `OUT`→`CAS` transition. Other gameplay selectors remain to trace.

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

The first replay confirmed this sequence at `$8975 → $B703 → $897E` and `$88FD (A=$00) → $8907 → $B703 → $890E → $8956`. Both loader returns had carry clear. At their respective return points, `STUPH` and `GEN` matched the entire extracted files. The `GEN` entry snapshot keeps the shared engine at `$7000–$8953` and shows three altered bytes in `STUPH` at `$172A`, `$172D`, and `$175C`; their roles are still open.

The shared entry at `$88F8` performs setup, while `$88FB` sets A to `$04` and selects `OUT` at `$88FD`. Direct jumps to `$88FB` appear in `GEN` (`$8AC0`), `DNG` (`$9725`), `TWN` (`$8ABF`), `CAS` (`$8BFD`), and `SPA` (`$8FAA`). `CAS`'s first-entry left-edge path is now runtime confirmed: `$08` at castle x=0 with `$B6BD=$23` reached `$8BFD`, selected `OUT`, reloaded its 5,230 bytes, and restored outdoor coordinates `($1E,$1F)` at the next input. Other return conditions remain to trace.

`OUT` uses its own transition routine at `$8EFA`. It saves two zero-page bytes at `$7E73–$7E74`, performs a page-copy loop using modified operands, restores A, and jumps to `$88FD` at `$8F1C`. Two callers make the next state visible:

| Call site in `OUT` | Selector in A | Next module |
| --- | ---: | --- |
| `$8D6E` | `$14` | `SPA` |
| `$90FF–$9137` | `$10`, `$0C`, or `$08` | `CAS`, `TWN`, or `DNG` |

The reviewed `$90FF–$9139` source confirms the exact cases: incoming A = `$04` selects `CAS`; A = `$06` updates `$7EB1–$7EB4` and selects `TWN`; all other values select `DNG`. Runtime now establishes that the incoming A is the decoded tile code for the `$04` case. An 11-move outdoor replay reached code `$04` at `($1E,$1F)` without leaving `OUT`; `E` then read that tile, saved the coordinates at `$7E73/$7E74`, and reached `$88FD` with A=`$10`. The selector copied `CAS`, the load returned with carry clear, and all 5,524 bytes matched at `$8956` entry. Codes `$05–$07` and the conditions for other transitions remain to trace.

The `$88FD` selector is a strong boundary for tracing game transitions. For each module, identify the value placed in A before reaching it and record any shared state changes before the jump.
