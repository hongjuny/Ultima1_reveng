# First dungeon map: observed memory format

This page describes the first dungeon reached from outdoor tile `(43,15)` in this disk version. The private replays and byte comparisons are checked by [`verify_dng_generation.py`](../tools/verify_dng_generation.py) and [`verify_dng_directions.py`](../tools/verify_dng_directions.py). The generator's rules for other entrances and levels remain open.

## Storage and indexing

`DNG` ends at `$B098`. Its entry code copies a 121-byte template from file-backed `$A619–$A691` into writable `$B099–$B111`. The [map reader](../disasm/DNG-map-access.s) at `$9D32` and [writer](../disasm/DNG-map-write.s) at `$A41F` both use the address formula `$B099 + 11*y + x`. Each source fragment reassembles to the exact extracted bytes. The runtime map is therefore an 11×11 row-major array for this path; `$B099–$B111` is generated state beyond the `DNG` file payload.

At `$8C87`, the entire working array matches the template. At `$8CBB`, 35 cells differ from the template. By the first main-loop entry `$8DE6`, another 10 cells differ from the `$8CBB` state. The resulting map is unchanged at the first key poll. In this observed map, all 40 border cells are `$01`, and the starting `(1,1)` cell is `$08`. The complete array remains in ignored private snapshots, not this public repository.

## First generator seed

The `$8C5D` entry code initializes two state bytes before generating the map:

```text
$A504 = (($7EED << 3) XOR outdoor_x[$7E73] XOR $A506) & $FF
$A505 = ((outdoor_y[$7E74] << 2) XOR $7E6F) & $FF
```

For the observed entry, `$7EED=$0B`, outdoor coordinates are `(43,15)`, `$7E6F=0`, and `$A506=1`. The seed is `$72,$3C` after template copy. It evolves to `$A7,$C4` at `$8CBB` and `$01,$28` at `$8DE6`. The meanings of `$7EED` and `$7E6F`, and the complete random sequence, still need tracing. These observations establish one concrete seed and map, not a general generator specification.

## Movement evidence

The [candidate routine](../disasm/DNG-candidate-position.s) at `$A438` adds facing `$A4EC/$A4ED` to local position `$A4E8/$A4E9`. The direction keys and Space were replayed independently from the same first poll:

| Input | Local position at next poll | Facing at next poll | Handler |
| --- | --- | --- | --- |
| Up `$0B` | `(1,2)` | `(0,+1)` | `$8E95` |
| Down `$0A` | `(1,1)` | `(0,-1)` | `$8E48` |
| Right `$15` | `(1,1)` | `(-1,0)` | `$8E5B` |
| Left `$08` | `(1,1)` | `(+1,0)` | `$8E78` |
| Space `$20` | `(1,1)` | `(0,+1)` | `$8F8C` |

With facing `(-1,0)`, Up read `$01` at `(0,1)` and took the blocked path `$8EA7`; position stayed `(1,1)`. With facing `(+1,0)`, Up read `$00` at `(2,1)`, took `$8EBE`, and moved to `(2,1)`. HP and food stayed unchanged through the next poll in each replay. Thus `$01` blocks and `$00` admits movement in these tested cases. The meaning of other cell values, visual rendering, encounters, stairs, and per-turn costs remains open.
