# Startup and module loading

Status: initial static analysis plus runtime traces from `U1.SYSTEM` through the first `U1.INTRO` entry and `MAKE.INDATA` execution. `MI.U1` and later transitions still need runtime confirmation. Addresses refer to the local ProDOS extraction.

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
- `MI.U1` starts with a jump to `$8956`. At `$7E16` it contains zero-terminated names `GEN`, `OUT`, `DNG`, `TWN`, `CAS`, `SPA`, and `TM` in that order. The routine near `$88FD` loads `GEN` and transfers control to `$8956`.
- The initial `MI.U1` loader at `$8956` loads `STUPH` by inline filename, then reaches the module selector at `$88FD` with accumulator value zero. `STUPH` has 33 three-byte jump stubs at `$1583–$15E5`; these are called throughout the common engine.
- The original `MI.U1` bytes at `$8956` form startup/loader code. Each gameplay module is loaded at the same address and overwrites that code. Each module's first bytes are 6502 code; `TM` starts with a jump to `$8AD7`.
- `TWN` and `CAS` refer to `TCMAPS` and `MAPCHARS`. `TM` refers to `NIF`. The exact load conditions need tracing.

## Working interpretation

The common engine keeps shared state and utility routines below `$8956`, with extra routines in `STUPH`. A loader selects one gameplay module according to game state, then enters it at `$8956`. The initial `MI.U1` tail is only needed before the first module load. Calls back into lower shared addresses are expected. This is a hypothesis to verify by tracing the loader and each module's exit paths.

## Next trace targets

1. `U1.INTRO` `$0F41`, `$0B23`, `$0B50`: confirm the early animation key path into `MI.U1` loading; later inspect `$1039` and the special key cases.
2. `$B70C` and `MAKE.INDATA` `$1E03`, `$8700`: classify the loader's run contract, decoder, copied code, and display effects.
3. `MI.U1` `$7E16`, `$88FD–$8955`: name the selection state, loader call, and module return convention; trace the `$1583–$15E5` stubs in `STUPH`.
4. `GEN` `$8956` and `OUT` `$8956`: follow character creation into outdoor play.

The first pass through the module selector is documented in [Gameplay module dispatch](module-dispatch.md).
