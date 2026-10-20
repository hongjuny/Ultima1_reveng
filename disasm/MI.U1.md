# MI.U1 — shared engine and module loader

Load range: `$7000–$89BC`. A gameplay overlay at `$8956` replaces the final `$67` bytes.

## Confirmed regions

| Range | Classification | Evidence |
| --- | --- | --- |
| `$7000` | Entry jump | `JMP $8956` |
| `$7E16–$7E31` | Null-terminated overlay filename table | `GEN`, `OUT`, `DNG`, `TWN`, `CAS`, `SPA`, `TM` |
| `$7E53–$7E6C` | 26-byte shared command-key table | Four direction codes, Space, `$01`, and 20 letter keys; `P` absent |
| `$82A2` | Shared command lookup | Normalizes input through `$827D`, scans `$7E53–$7E6C`; misses return carry set |
| `$82E2–$8330` | Decimal-mode state update | Uses `$7E4F/$7E50` as amount bytes, subtracts from `$7EE4`, conditionally reduces `$7EE5/$7EE6`, adds to `$7EDA` with carry into following bytes |
| `$888D–$88A0` | [Death reset](MI.U1-death-reset.s) | Clears three two-byte player fields before `OUT` resurrection |
| `$88F8–$893E` | Overlay selection and transfer | Decoded below |
| `$8956–$89BC` | Initial loader tail | Loads `STUPH`, then enters selector with A = 0 |

## Selector disassembly

| Address | Instruction or data | Effect |
| --- | --- | --- |
| `$88F8` | `JSR $8870` | Shared death/setup path; the traced lethal branch clears HP, food, and `$7ED4/$7ED5` |
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

The live `OUT` `P` input returned `$50` from its key poll, then `$82A2` returned with carry set and `X=$FF`; the caller skipped its handler call. The original 26-byte command table is `0B 0A 15 08 20 01 41 42 43 44 45 46 47 48 49 4B 4E 4F 51 52 53 54 55 56 58 5A`. Space (`$20`) is present at index 4, while `P` (`$50`) is absent. The meaning of each accepted key requires its handler to be traced.

The separate Space replay returned from `$82A2` with carry clear and `X=$08`, twice its table index. In `OUT`, the handler pointer at `$9AAA+8` is `$8A76`. That handler loads `Y=$05`, `A=$50`, then jumps to `$82E2`. Runtime confirmed the shared routine changed `$7EE4` from `$95` to `$90` and `$7EDA` from `$00` to `$50`, while `$7EE5/$7EE6` and health stayed unchanged at the handler return. The byte-matched [shared update](MI.U1-turn-update.s) uses `SED` for decimal arithmetic. Its subtraction path decrements the two-byte food value only when `$7EE4` borrows and food is nonzero; its addition path carries from `$7EDA` into later bytes. The meaning of the complete `$7EDA` counter still needs cross-checking against visible game time.

The initial loader at `$8975` calls `$B703` with inline filename `STUPH`. After installing shared support, it executes `LDA #$00` at `$89B8` and `JMP $88FD` at `$89BA`. Next: trace `$B703` and `$B736`, and label the common state at `$7E00`.

The [controlled death record comparison](../docs/player-state.md) tracks all 458 live `U1.VARS` bytes across selector entry and the first resurrected `OUT` input. It found six changed bytes for that path; the other 452 matched.

Reviewed source: [module selector](MI.U1-selector.s) at `$88F8–$893E`, [death reset](MI.U1-death-reset.s) at `$888D–$88A0`, and [decimal update](MI.U1-turn-update.s) at `$82E2–$8330`. Run `python3 tools/verify_disasm.py` from the repository root to reassemble these against the local `MI.U1` extraction.
