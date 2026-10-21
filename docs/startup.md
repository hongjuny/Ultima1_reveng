# Startup and module loading

Status: runtime traces from `U1.SYSTEM` through `U1.INTRO`, `MAKE.INDATA`, `MI.U1`, `STUPH`, and the first `GEN` entry. Later gameplay transitions still need runtime confirmation. Addresses refer to the local ProDOS extraction.

The supplied WOZ reaches ProDOS's `$21D4` error loop after `GET_PREFIX` returns `A=$27`. The block-equivalent `.po` image boots through to `U1.SYSTEM`; the discrepancy needs investigation before claiming faithful WOZ emulation.

```mermaid
flowchart TD
  P[ProDOS] --> S[U1.SYSTEM at $2000]
  S --> I[U1.INTRO at $0800]
  I --> D[MAKE.INDATA at $1E00]
  I --> M[MI.U1 at $7000]
  M --> H[STUPH at $0800: shared routines]
  H --> G[GEN at $8956]
  M --> O[OUT / DNG / TWN / CAS / SPA / TM at $8956]
```

## Confirmed observations

- `U1.SYSTEM` begins with a jump to `$2088`. Its header names `U1.INTRO`. A memory-verified capture from the block-equivalent image reached `$2088` with the extracted `U1.SYSTEM` code (`78 A9`). After setup at `$21A0`, execution took the startup-file branch at `$21D6`; the live header still named `U1.INTRO`. It reached `$2220`, transferred through `$0136`, and entered `U1.INTRO` at `$0800`. The intro's first jump reached `$0F23`. At `$0800`, the memory bytes matched the extracted `U1.INTRO`.
- `U1.INTRO` begins with jumps to `$0F23` and `$0F41`. At `$0F23`, a loader call uses the inline filename `MAKE.INDATA`. Another code path near `$0B50` uses the inline filename `MI.U1`.
- The `$0F23` path called `$B70C` and returned to `$0F37` with carry clear, then reached `$0F41`. The loader's indirect entry was `$1E00`. The `MAKE.INDATA` entry copied `$2000–$27FF` to `$8700–$8EFF` and `$27BD–$4DBC` to `$6000–$85FF`; both destination ranges matched the file exactly in the private snapshot. The original `$2000` range had been reused before return.
- `$0800` enters the `MAKE.INDATA` request path; `$0803` enters at `$0F41` after that request. During the animation, `$0B23–$0B4F` polls the keyboard and sends ordinary keys to `$0B50`. A later loop at `$1039–$1056` also polls and calls `$0B50`. That routine requests `MI.U1` for key values other than `$9B`; `$9B` takes a separate wait-for-next-key path.
- In the private replay, ASCII `A` at `$0B23` appeared as `$C1` at `$0B50`. Execution reached `$B70C`, `MI.U1` `$7000`, then its first loader at `$8956`. All 6589 bytes at `$7000` matched the extracted file at entry, and the intro remained resident at `$0800`. The reproducible report and snapshots are kept under ignored `build/traces/intro-to-engine/`; `tools/verify_intro_to_engine.py` checks them locally.
- The next replay reached `$8975 → $B703 → $897E` for `STUPH`; all 6144 bytes matched the extraction immediately after loading at `$0800`. The selector at `$88FD` received `A=$00` and reached `$8907 → $B703 → $890E` for `GEN`; all 8932 bytes matched at `$8956` before entry. Both loader returns had carry clear. At the `GEN` entry snapshot, the shared `MI.U1` range `$7000–$8953` still matches, while `STUPH` has three changed bytes at `$172A`, `$172D`, and `$175C`. Their purpose remains to analyze.
- The first `GEN` menu key read was reached at `$89FD` (cycle 32,493,298). Its reviewed 19-byte dispatch remains unchanged in the private menu snapshot. The `A` choice reached the new-character entry at `$8AC3` with `A=$41` (cycle 32,532,365).
- The new-character path reached `$8C07` before its first attribute input. Its 136-byte template copy from `$904F–$90D6` to `$7E6F–$7EF6` matches the private before/after snapshots. Six values at `$7EC8–$7ED2` start at 10, with 30 points at `$903F` to distribute.
- A replay assigned all 30 points, confirmed the per-attribute cap of 25 and the Space gate while points remained, then reached the race key read at `$8CD0`. The six values were `[25, 25, 10, 10, 10, 10]` in address order.
- Race choice `A` set `$7ED6=1` and increased the sixth value 10→15 before reaching the sex input at `$8D72`. The class input is later at `$8DEA`; the initial runtime label for `$8D72` was corrected.
- Sex choice `A` stored zero at `$7EB7` and reached the class input at `$8DEA`. The following class bonus code and name input remain to be observed at runtime.
- `MI.U1` starts with a jump to `$8956`. At `$7E16` it contains zero-terminated names `GEN`, `OUT`, `DNG`, `TWN`, `CAS`, `SPA`, and `TM` in that order. The routine near `$88FD` loads `GEN` and transfers control to `$8956`.
- The initial `MI.U1` loader at `$8956` loads `STUPH` by inline filename, then reaches the module selector at `$88FD` with accumulator value zero. `STUPH` has 34 three-byte jump stubs at `$1583–$15E8`; these are called throughout the common engine.
- The original `MI.U1` bytes at `$8956` form startup/loader code. Each gameplay module is loaded at the same address and overwrites that code. Each module's first bytes are 6502 code; `TM` starts with a jump to `$8AD7`.
- `TWN` and `CAS` refer to `TCMAPS` and `MAPCHARS`. `TM` refers to `NIF`. The exact load conditions need tracing.

## Working interpretation

The common engine keeps shared state and utility routines below `$8956`, with extra routines in `STUPH`. A loader selects one gameplay module according to game state, then enters it at `$8956`. The initial `MI.U1` tail is only needed before the first module load. Calls back into lower shared addresses are expected. This is a hypothesis to verify by tracing the loader and each module's exit paths.

## Next trace targets

1. `U1.INTRO` `$1039` and the special key cases: inspect the paths beyond the confirmed early animation key transition.
2. `$B70C` and `MAKE.INDATA` `$1E03`, `$8700`: classify the loader's run contract, decoder, copied code, and display effects.
3. `MI.U1` `$88FD–$8955`: name the later selection states and module return convention, and inspect the `$1583–$15E8` stubs in `STUPH`.
4. `GEN` `$8956`, menu key read `$89FD`, and `OUT` `$8956`: follow character creation into outdoor play.

The first pass through the module selector is documented in [Gameplay module dispatch](module-dispatch.md).
