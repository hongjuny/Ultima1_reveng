# Reviewed assembly address atlas

This index places every **byte-matched, reviewed fragment** at its original Apple II load address. Each link leads to a small, public annotation; full linear listings and binary assets remain private. An unlisted address is **unreviewed**, not proven to be data or unreachable code. Overlapping reviewed fragments count once in the unique-byte total.

Current inventory: **93 fragments, 3946 unique bytes** across 11 modules. These are raw-file bytes, not a percentage of executable code: code and data are mixed.

| Module | Load range | Reviewed fragments | Unique reviewed bytes |
| --- | --- | ---: | ---: |
| [U1.INTRO](#u1intro) | `$0800–$11A4` | 5 | 137 |
| [MAKE.INDATA](#makeindata) | `$1E00–$5434` | 1 | 69 |
| [MI.U1](#miu1) | `$7000–$89BC` | 8 | 321 |
| [STUPH](#stuph) | `$0800–$1FFF` | 5 | 479 |
| [GEN](#gen) | `$8956–$AC39` | 12 | 595 |
| [OUT](#out) | `$8956–$9DC3` | 14 | 492 |
| [DNG](#dng) | `$8956–$B098` | 24 | 682 |
| [TWN](#twn) | `$8956–$AA62` | 3 | 115 |
| [CAS](#cas) | `$8956–$9EE9` | 14 | 464 |
| [SPA](#spa) | `$8956–$B01F` | 3 | 370 |
| [TM](#tm) | `$8956–$A910` | 4 | 222 |

The `$8956` ranges below are **mutually exclusive overlays**. A call at `$8A00` must be interpreted with the loaded module named; these files do not form one combined address space. `MI.U1`'s final `$8956–$89BC` loader tail is overwritten after selection. See the [execution architecture](execution-architecture.md) and [Ghidra call atlas](ghidra-call-atlas.md).

## U1.INTRO

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$0800–$0805` | `$0000–$0005` | 6 | [U1.INTRO-entry.s](../disasm/U1.INTRO-entry.s) |
| `$0B23–$0B4F` | `$0323–$034F` | 45 | [U1.INTRO-animation-key.s](../disasm/U1.INTRO-animation-key.s) |
| `$0B50–$0B69` | `$0350–$0369` | 26 | [U1.INTRO-load-mi.s](../disasm/U1.INTRO-load-mi.s) |
| `$0F23–$0F40` | `$0723–$0740` | 30 | [U1.INTRO-load-support.s](../disasm/U1.INTRO-load-support.s) |
| `$1039–$1056` | `$0839–$0856` | 30 | [U1.INTRO-key-loop.s](../disasm/U1.INTRO-key-loop.s) |

## MAKE.INDATA

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$1EFD–$1F41` | `$00FD–$0141` | 69 | [MAKE.INDATA-copy-init.s](../disasm/MAKE.INDATA-copy-init.s) |

## MI.U1

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$8037–$8042` | `$1037–$1042` | 12 | [MI.U1-inline-byte.s](../disasm/MI.U1-inline-byte.s) |
| `$8062–$8085` | `$1062–$1085` | 36 | [MI.U1-text-control.s](../disasm/MI.U1-text-control.s) |
| `$8119–$8143` | `$1119–$1143` | 43 | [MI.U1-inline-text.s](../disasm/MI.U1-inline-text.s) |
| `$8254–$8265` | `$1254–$1265` | 18 | [MI.U1-bounded-random.s](../disasm/MI.U1-bounded-random.s) |
| `$82E2–$8330` | `$12E2–$1330` | 79 | [MI.U1-turn-update.s](../disasm/MI.U1-turn-update.s) |
| `$837F–$83A8` | `$137F–$13A8` | 42 | [MI.U1-status-values.s](../disasm/MI.U1-status-values.s) |
| `$888D–$88A0` | `$188D–$18A0` | 20 | [MI.U1-death-reset.s](../disasm/MI.U1-death-reset.s) |
| `$88F8–$893E` | `$18F8–$193E` | 71 | [MI.U1-selector.s](../disasm/MI.U1-selector.s) |

## STUPH

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$1C39–$1D63` | `$1439–$1563` | 299 | [STUPH-outdoor-draw.s](../disasm/STUPH-outdoor-draw.s) |
| `$1D64–$1D7E` | `$1564–$157E` | 27 | [STUPH-keyboard-latch.s](../disasm/STUPH-keyboard-latch.s) |
| `$1D7E–$1DD5` | `$157E–$15D5` | 88 | [STUPH-input-dispatch.s](../disasm/STUPH-input-dispatch.s) |
| `$1DD6–$1DF0` | `$15D6–$15F0` | 27 | [STUPH-input-prelude.s](../disasm/STUPH-input-prelude.s) |
| `$1DF1–$1E17` | `$15F1–$1617` | 39 | [STUPH-random.s](../disasm/STUPH-random.s) |

## GEN

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$89FD–$8A0F` | `$00A7–$00B9` | 19 | [GEN-menu.s](../disasm/GEN-menu.s) |
| `$8A10–$8A2B` | `$00BA–$00D5` | 28 | [GEN-load-player.s](../disasm/GEN-load-player.s) |
| `$8A5B–$8A7E` | `$0105–$0128` | 36 | [GEN-reload-copy.s](../disasm/GEN-reload-copy.s) |
| `$8AEA–$8B24` | `$0194–$01CE` | 59 | [GEN-initialize-state.s](../disasm/GEN-initialize-state.s) |
| `$8C00–$8C80` | `$02AA–$032A` | 129 | [GEN-attribute-input.s](../disasm/GEN-attribute-input.s) |
| `$8CD0–$8CE0` | `$037A–$038A` | 17 | [GEN-race-choice.s](../disasm/GEN-race-choice.s) |
| `$8CFA–$8D3B` | `$03A4–$03E5` | 66 | [GEN-race-bonus.s](../disasm/GEN-race-bonus.s) |
| `$8D72–$8D82` | `$041C–$042C` | 17 | [GEN-sex-choice.s](../disasm/GEN-sex-choice.s) |
| `$8DEA–$8DFA` | `$0494–$04A4` | 17 | [GEN-class-choice.s](../disasm/GEN-class-choice.s) |
| `$8E12–$8E53` | `$04BC–$04FD` | 66 | [GEN-class-bonus.s](../disasm/GEN-class-bonus.s) |
| `$8E83–$8EED` | `$052D–$0597` | 107 | [GEN-name-input.s](../disasm/GEN-name-input.s) |
| `$8F0F–$8F30` | `$05B9–$05DA` | 34 | [GEN-save-confirm.s](../disasm/GEN-save-confirm.s) |

## OUT

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$898A–$8994` | `$0034–$003E` | 11 | [OUT-death-gate.s](../disasm/OUT-death-gate.s) |
| `$89E8–$8A1C` | `$0092–$00C6` | 53 | [OUT-resurrection-init.s](../disasm/OUT-resurrection-init.s) |
| `$8A3A–$8A5E` | `$00E4–$0108` | 37 | [OUT-resurrection-fill.s](../disasm/OUT-resurrection-fill.s) |
| `$8A6A–$8A75` | `$0114–$011F` | 12 | [OUT-key-poll.s](../disasm/OUT-key-poll.s) |
| `$8A76–$8A7C` | `$0120–$0126` | 7 | [OUT-space-handler.s](../disasm/OUT-space-handler.s) |
| `$8D61–$8D8D` | `$040B–$0437` | 45 | [OUT-board-transition.s](../disasm/OUT-board-transition.s) |
| `$8D6E–$8D72` | `$0418–$041C` | 5 | [OUT-space-dispatch.s](../disasm/OUT-space-dispatch.s) |
| `$90C8–$90DC` | `$0772–$0786` | 21 | [OUT-enter-gate.s](../disasm/OUT-enter-gate.s) |
| `$90FF–$9139` | `$07A9–$07E3` | 59 | [OUT-location-dispatch.s](../disasm/OUT-location-dispatch.s) |
| `$92CA–$92DF` | `$0974–$0989` | 22 | [OUT-Q-save.s](../disasm/OUT-Q-save.s) |
| `$9351–$936C` | `$09FB–$0A16` | 28 | [OUT-direction-entry.s](../disasm/OUT-direction-entry.s) |
| `$9927–$9957` | `$0FD1–$1001` | 49 | [OUT-object-insert.s](../disasm/OUT-object-insert.s) |
| `$9958–$99C4` | `$1002–$106E` | 109 | [OUT-object-remove.s](../disasm/OUT-object-remove.s) |
| `$99D1–$99F7` | `$107B–$10A1` | 39 | [OUT-tile-lookup.s](../disasm/OUT-tile-lookup.s) |

## DNG

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$8D20–$8D30` | `$03CA–$03DA` | 17 | [DNG-random-cell.s](../disasm/DNG-random-cell.s) |
| `$8D36–$8D98` | `$03E0–$0442` | 99 | [DNG-stair-placement.s](../disasm/DNG-stair-placement.s) |
| `$8DDA–$8DE5` | `$0484–$048F` | 12 | [DNG-key-poll.s](../disasm/DNG-key-poll.s) |
| `$8EBE–$8ECD` | `$0568–$0577` | 16 | [DNG-move-commit.s](../disasm/DNG-move-commit.s) |
| `$93A7–$93C5` | `$0A51–$0A6F` | 31 | [DNG-actor-removal.s](../disasm/DNG-actor-removal.s) |
| `$93C6–$93DC` | `$0A70–$0A86` | 23 | [DNG-respawn-slot.s](../disasm/DNG-respawn-slot.s) |
| `$9437–$9446` | `$0AE1–$0AF0` | 16 | [DNG-actor-encode.s](../disasm/DNG-actor-encode.s) |
| `$963F–$9646` | `$0CE9–$0CF0` | 8 | [DNG-stair-facing.s](../disasm/DNG-stair-facing.s) |
| `$9666–$966F` | `$0D10–$0D19` | 10 | [DNG-stair-gate.s](../disasm/DNG-stair-gate.s) |
| `$9716–$9727` | `$0DC0–$0DD1` | 18 | [DNG-exit-out.s](../disasm/DNG-exit-out.s) |
| `$9728–$972B` | `$0DD2–$0DD5` | 4 | [DNG-ascend-regenerate.s](../disasm/DNG-ascend-regenerate.s) |
| `$972C–$9731` | `$0DD6–$0DDB` | 6 | [DNG-descend-entry.s](../disasm/DNG-descend-entry.s) |
| `$997F–$99A9` | `$1029–$1053` | 43 | [DNG-actor-move-x.s](../disasm/DNG-actor-move-x.s) |
| `$99D6–$9A00` | `$1080–$10AA` | 43 | [DNG-actor-move-y.s](../disasm/DNG-actor-move-y.s) |
| `$9A37–$9A63` | `$10E1–$110D` | 45 | [DNG-monster-hit-roll.s](../disasm/DNG-monster-hit-roll.s) |
| `$9A95–$9ADB` | `$113F–$1185` | 71 | [DNG-monster-damage-roll.s](../disasm/DNG-monster-damage-roll.s) |
| `$9B05–$9B1F` | `$11AF–$11C9` | 27 | [DNG-monster-hp.s](../disasm/DNG-monster-hp.s) |
| `$9C02–$9C10` | `$12AC–$12BA` | 15 | [DNG-spawn-init.s](../disasm/DNG-spawn-init.s) |
| `$9C11–$9C53` | `$12BB–$12FD` | 67 | [DNG-spawn-slot-hp.s](../disasm/DNG-spawn-slot-hp.s) |
| `$9C82–$9C99` | `$132C–$1343` | 24 | [DNG-spawn-map.s](../disasm/DNG-spawn-map.s) |
| `$9CBC–$9CD1` | `$1366–$137B` | 22 | [DNG-damage-bound.s](../disasm/DNG-damage-bound.s) |
| `$9D32–$9D48` | `$13DC–$13F2` | 23 | [DNG-map-access.s](../disasm/DNG-map-access.s) |
| `$A41F–$A431` | `$1AC9–$1ADB` | 19 | [DNG-map-write.s](../disasm/DNG-map-write.s) |
| `$A432–$A448` | `$1ADC–$1AF2` | 23 | [DNG-candidate-position.s](../disasm/DNG-candidate-position.s) |

## TWN

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$89B9–$89DD` | `$0063–$0087` | 37 | [TWN-map-copy.s](../disasm/TWN-map-copy.s) |
| `$9257–$926E` | `$0901–$0918` | 24 | [TWN-food-price.s](../disasm/TWN-food-price.s) |
| `$932F–$9364` | `$09D9–$0A0E` | 54 | [TWN-food-purchase.s](../disasm/TWN-food-purchase.s) |

## CAS

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$89BB–$89DF` | `$0065–$0089` | 37 | [CAS-map-copy.s](../disasm/CAS-map-copy.s) |
| `$8A25–$8A30` | `$00CF–$00DA` | 12 | [CAS-key-poll.s](../disasm/CAS-key-poll.s) |
| `$8AA8–$8AC0` | `$0152–$016A` | 25 | [CAS-left-edge.s](../disasm/CAS-left-edge.s) |
| `$8C00–$8C12` | `$02AA–$02BC` | 19 | [CAS-move-check.s](../disasm/CAS-move-check.s) |
| `$8C29–$8C4B` | `$02D3–$02F5` | 35 | [CAS-move-commit.s](../disasm/CAS-move-commit.s) |
| `$8CC9–$8CF6` | `$0373–$03A0` | 46 | [CAS-attack-ray.s](../disasm/CAS-attack-ray.s) |
| `$8D08–$8D2B` | `$03B2–$03D5` | 36 | [CAS-attack-hit-roll.s](../disasm/CAS-attack-hit-roll.s) |
| `$8D46–$8D83` | `$03F0–$042D` | 62 | [CAS-attack-damage.s](../disasm/CAS-attack-damage.s) |
| `$9951–$9980` | `$0FFB–$102A` | 48 | [CAS-guard-hit-roll.s](../disasm/CAS-guard-hit-roll.s) |
| `$998F–$99A5` | `$1039–$104F` | 23 | [CAS-guard-damage-roll.s](../disasm/CAS-guard-damage-roll.s) |
| `$99CB–$99E0` | `$1075–$108A` | 22 | [CAS-guard-player-hp.s](../disasm/CAS-guard-player-hp.s) |
| `$9BC0–$9BD8` | `$126A–$1282` | 25 | [CAS-collision-wrapper.s](../disasm/CAS-collision-wrapper.s) |
| `$9BD9–$9BFD` | `$1283–$12A7` | 37 | [CAS-map-tile-check.s](../disasm/CAS-map-tile-check.s) |
| `$9BFE–$9C22` | `$12A8–$12CC` | 37 | [CAS-actor-lookup.s](../disasm/CAS-actor-lookup.s) |

## SPA

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$8A5F–$8A7A` | `$0109–$0124` | 28 | [SPA-key-dispatch.s](../disasm/SPA-key-dispatch.s) |
| `$8FAD–$9099` | `$0657–$0743` | 237 | [SPA-direction-controls.s](../disasm/SPA-direction-controls.s) |
| `$A154–$A1BC` | `$17FE–$1866` | 105 | [SPA-fuel-status.s](../disasm/SPA-fuel-status.s) |

## TM

| RAM address | File offset | Bytes | Reviewed source |
| --- | --- | ---: | --- |
| `$8E80–$8EA7` | `$052A–$0551` | 40 | [TM-command-dispatch.s](../disasm/TM-command-dispatch.s) |
| `$98E3–$9935` | `$0F8D–$0FDF` | 83 | [TM-flee-regeneration.s](../disasm/TM-flee-regeneration.s) |
| `$9936–$9970` | `$0FE0–$101A` | 59 | [TM-flee-movement.s](../disasm/TM-flee-movement.s) |
| `$99BF–$99E6` | `$1069–$1090` | 40 | [TM-retaliation-damage.s](../disasm/TM-retaliation-damage.s) |
