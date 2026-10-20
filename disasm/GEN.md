# GEN — character generation

Overlay range: `$8956–$AC39`; entry `$8956`.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$8956` | Initializes shared state and display | Module entry |
| `$89FD` | Reads input and compares against `#$41` and `#$42` | `A`/`B` menu choice |
| `$8A10–$8A2B` | Previous-character loader, 28 reviewed bytes | Load `/U1.PLAYER/U1.VARS` at `$6000`; check `$01CA` header |
| `$8A5B–$8A7E` | Self-modifying copy, 36 reviewed bytes | Restore 458 bytes `$6000–$61C9` to `$7E6D–$8036` |
| `$8AC3` | Target of the `A` branch | New-character path |
| `$8AEA–$8B24` | Self-modifying loop, 59 reviewed bytes | Copy 136 template bytes from `$904F–$90D6` to `$7E6F–$7EF6` |
| `$8C00–$8C80` | Attribute input loop, 129 reviewed bytes | Six values, remaining-point pool, navigation and acceptance |
| `$8CD0–$8CE0` | Race key validation, 17 reviewed bytes | `A`–`D` stored as 1–4 at `$7ED6` |
| `$8CFA–$8D3B` | Race bonus dispatch, 66 reviewed bytes | Modify attributes by selected race |
| `$8D72–$8D82` | Sex choice, 17 reviewed bytes | `A`/`B` stored as 0/1 at `$7EB7` |
| `$8DEA–$8DFA` | Class choice, 17 reviewed bytes | `A`–`D` stored as 1–4 at `$7ED8` |
| `$8E12–$8E53` | Class bonus dispatch, 66 reviewed bytes | Modify attributes by selected class |
| `$8E83–$8EED` | Name input, 107 reviewed bytes | Validate, edit, and store a name before confirmation |
| `$8F0F–$8F30` | Confirmation dispatch, 34 reviewed bytes | `Y` calls `$B724`; `N` restarts character generation |
| `$8AC0` | `JMP $88FB` | Observed continue path to `OUT` |

The menu text describes new-character and previous-game options. Saving a new character returns to this menu. The later gameplay handoff, remaining attribute semantics, and full player-record layout remain to trace.

The reviewed [menu choice fragment](GEN-menu.s) covers `$89FD–$8A0F` and reassembles byte-for-byte. It shows `A` (`$41`) jumping to `$8AC3`; `B` (`$42`) falls into the continuation code at `$8A10`. Other values repeat the input loop.

The first runtime replay reached the key read at `$89FD` at cycle 32,493,298, before injecting a menu choice. The private snapshot confirms that the 19-byte dispatch still matches the extracted `GEN` file. `tools/verify_gen_menu.py` repeats this check locally.

The `A` replay reached `$8AC3` with `A=$41` at cycle 32,532,365. The next replay reached the first attribute key read at `$8C07` (cycle 33,025,684). At that point `$7EC8`, `$7ECA`, `$7ECC`, `$7ECE`, `$7ED0`, and `$7ED2` are all 10; `$903F` holds 30 unassigned points and `$9041` selects the first attribute. The private snapshots confirm the full 136-byte copy from `$904F–$90D6` to `$7E6F–$7EF6`. The reviewed [copy loop](GEN-initialize-state.s) and [attribute input loop](GEN-attribute-input.s) reassemble byte-for-byte.

The input loop uses `$9041` as a 1–6 selection index and addresses the chosen value at `$7EC6 + 2 × index`. Code `$08` lowers it down to 10 and returns one point; `$15` raises it up to 25 when points remain. Codes `$2F`/`$0A` select the next value, `$0D`/`$0B` the previous one, and `$1B` returns to the main menu. Space proceeds only when the remaining-point count is zero. Replays confirm `$15` changes the first value 10→11 and the pool 30→29; `$08` reverses the change and cannot lower the value below 10. `$2F` and `$0B` move the selection 1→2→1. A replay for the upper bound and space gate is prepared. The meaning and on-screen labels of all six values still need to be tied to their rendering code and observed screen.

The upper-bound replay confirmed that a selected attribute stops at 25; one more `$15` leaves it at 25. Space with 15 points remaining returned to the allocation loop. After the remaining 15 points were assigned, Space reached the race input at `$8CD0` with values `[25, 25, 10, 10, 10, 10]` and `$903F=0`. The displayed choices are `A) Human`, `B) Elf`, `C) Dwarf`, and `D) Bobbit` in the extracted inline text.

The reviewed [race choice](GEN-race-choice.s) and [race bonus](GEN-race-bonus.s) fragments reassemble byte-for-byte. The code stores `A`–`D` as 1–4 at `$7ED6`. It adds 5 to `$7ED2` for A, 5 to `$7ECA` for B, 5 to `$7EC8` for C, and for D adds 10 to `$7ED0` while subtracting 5 from `$7EC8`. The A replay confirmed `$7ED6=1` and the sixth value 10→15, then reached **sex selection** at `$8D72`. The B–D bonus effects remain static findings.

The sex menu displays `A) Male` and `B) Female`. Its reviewed [input fragment](GEN-sex-choice.s) stores A as 0 and B as 1 at `$7EB7`. The replay of A confirmed `$7EB7=0` and reached class input at `$8DEA`. The class menu displays `A) Fighter`, `B) Cleric`, `C) Wizard`, and `D) Thief`. An earlier trace label called `$8D72` a class input; the address is the sex input, and the label has been corrected.

The reviewed [class choice](GEN-class-choice.s) and [class bonus](GEN-class-bonus.s) fragments reassemble byte-for-byte. Class IDs 1–4 are stored at `$7ED8`. Fighter adds 10 each to `$7EC8` and `$7ECA`; Cleric adds 10 to `$7ED0`; Wizard adds 10 to `$7ED2`; Thief adds 10 to `$7ECA`. The class-A replay confirmed `$7ED8=1` and `[25,25,10,10,10,15]→[35,35,10,10,10,15]`, then reached name input `$8E83`. The other class effects remain static findings.

The reviewed [name input](GEN-name-input.s) fragment reassembles all 107 bytes at `$8E83–$8EED`. `$9042` counts name characters; `$7EB8–$7EC4` holds at most 13. The first character must be `A`–`Z`; later characters must have code `$20` or higher. Later uppercase letters become lowercase unless the preceding character is a space. `$08` and `$7F` delete the last character; Return is ignored for an empty name and otherwise branches to the confirmation prompt at `$8EEE`. Runtime replay confirmed that `A` raises the length to one, stores `$41` at `$7EB8`, and Return reaches `$8EEE`.

The reviewed [confirmation dispatch](GEN-save-confirm.s) matches all 34 bytes at `$8F0F–$8F30`. It accepts `Y` to call `$B724` with six inline parameter bytes, or `N` to restart character generation at `$8AC3`; other keys repeat the prompt. Carry set after `$B724` branches to `$8F31`; carry clear jumps to `$895B`.

The `Y` replay reached `$B724` and returned at `$8F2C` with `A=$06` and carry set, then branched to `$8F31`. The private game-disk copy remained byte-identical. The helper at `$B770` parses its six inline bytes as source `$7E6D`, length `$01CA` (458), and path pointer `$7E38`. RAM at `$7E38` contains `/U1.PLAYER/U1.VARS`; the helper copied that path to its ProDOS pathname buffer `$BA79`. The error handler prints a player-disk prompt for this error class. This establishes that character persistence uses a separate `U1.PLAYER` volume. `tools/create_player_disk.py` creates a private blank ProDOS volume with that name, and `tools/trace_gen_player_save.py` is prepared to swap it in and retry without changing the original game disk.

The player-disk retry succeeded: `$B724` returned `A=$00` with carry clear at `$8F2C`, then execution reached `$895B`. The disposable `U1.PLAYER` disk gained `U1.VARS`, a 458-byte BIN file with auxiliary address `$7E6D`; its data matches RAM `$7E6D–$8036` byte-for-byte in the post-save snapshot. The blank disk template and original game disk remain unchanged. `tools/verify_gen_player_save.py` repeats the file extraction and comparison. `tools/trace_gen_after_save.py` is prepared to follow `$895B` to the next GEN input.

The continuation reached the menu key read at `$89FD` with the character record unchanged. The reviewed [previous-character loader](GEN-load-player.s) and [record copy](GEN-reload-copy.s) match all 64 original bytes across their ranges. Menu `B` calls `$B721` with inline destination `$6000` and path pointer `$7E38`, tests the first two loaded bytes against `$CA,$01`, then copies 458 bytes into the live record. Runtime replay confirmed carry clear at `$8A1C`, all 458 bytes matching the saved record at `$6000` immediately after loading, acceptance at `$8A5B`, restoration to `$7E6D–$8036` at `$8A7F`, and the `$8AC0` jump toward `$88FB`. `$6000` is reused later in the same path, so the final snapshot checks the restored record at `$7E6D`; the transient load match was checked live. `tools/trace_gen_to_out.py` is prepared to swap back to a private game-disk copy and follow the outgoing selector into `OUT`.
