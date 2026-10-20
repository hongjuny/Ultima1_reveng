# MI.U1 — shared engine and module loader

Load range: `$7000–$89BC`. A gameplay overlay at `$8956` replaces the final `$67` bytes.

## Confirmed regions

| Range | Classification | Evidence |
| --- | --- | --- |
| `$7000` | Entry jump | `JMP $8956` |
| `$7E16–$7E31` | Null-terminated overlay filename table | `GEN`, `OUT`, `DNG`, `TWN`, `CAS`, `SPA`, `TM` |
| `$88F8–$893E` | Overlay selection and transfer | Decoded below |
| `$8956–$89BC` | Initial loader tail | Loads `STUPH`, then enters selector with A = 0 |

## Selector disassembly

| Address | Instruction or data | Effect |
| --- | --- | --- |
| `$88F8` | `JSR $8870` | Shared setup; effect still under study |
| `$88FB` | `LDA #$04` | Selects `OUT` when entering here |
| `$88FD` | `LDX #$FF`; `TXS` | Resets stack |
| `$8900` | `CMP #$19`; `BCS $8907` | Out-of-range value takes `GEN` path |
| `$8904` | `TAX`; `BNE $8913` | Nonzero A becomes filename-table offset |
| `$8907` | `JSR $B703`; inline `GEN` | Requests character-generation module |
| `$890E` | `BCS $8907`; `JMP $8956` | Retry on carry; otherwise enter overlay |
| `$8913–$891E` | Copy from `$7E16,X` to `$7E16,Y` until zero | Move chosen name to table start |
| `$8920` | `JSR $8414`; `JSR $B736`; inline address `$7E16` | Setup and file request; `$B736` semantics pending |
| `$892B–$893B` | Calls `$7DCC`, `$7E05`, `$8331`, `$8151`, `$83A9` | Retry and post-load setup |
| `$893C` | `JMP $8956` | Enter selected overlay |

The valid names begin at byte offsets `$00`, `$04`, `$08`, `$0C`, `$10`, `$14`, and `$18`. The code accepts intermediate nonzero values too; whether they can arise during play remains open.

The initial loader at `$8975` calls `$B703` with inline filename `STUPH`. After installing shared support, it executes `LDA #$00` at `$89B8` and `JMP $88FD` at `$89BA`. Next: trace `$B703` and `$B736`, and label the common state at `$7E00`.

The reviewed source for `$88F8–$893E` is [MI.U1-selector.s](MI.U1-selector.s). Run `python3 tools/verify_disasm.py` from the repository root to reassemble it and compare its bytes with the locally supplied `MI.U1` file.
