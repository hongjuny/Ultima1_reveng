# Player record: observed persistence through death

`GEN` loads the 458-byte `U1.VARS` record from `$6000–$61C9` and copies it to `$7E6D–$8036`. This page tracks that live memory range for one **controlled** castle death. The trace starts at the `CAS` attack-handler return, changes only the player's low HP byte `$7EC6` from `$96` to `$0A` before a known `$0F` guard hit, then follows the shared death path and the `OUT` resurrection path to the first outdoor key poll.

| Record byte | Before intervention | Selector `$88FD` | First OUT input `$8A6C` | Observed source of change |
| --- | ---: | ---: | ---: | --- |
| `$7E7A` | `$01` | `$01` | `$00` | `OUT` `$8A17` clears it |
| `$7E7B` | `$01` | `$01` | `$00` | `OUT` `$8A14` clears it |
| `$7E84` | `$02` | `$02` | `$00` | `OUT` `$8A0E–$8A13` clears table entries `$7E84–$7E92` |
| `$7EC6` | `$96` | `$00` | `$63` | Intervention `$96→$0A`; guard damage borrows; shared death reset clears HP; `OUT` refills it to 99 |
| `$7ED4` | `$64` | `$00` | `$00` | Shared death reset clears the two-byte field `$7ED4/$7ED5` |
| `$7EE5` | `$C3` | `$00` | `$63` | Shared death reset clears food; `OUT` refills it to 99 |

These are **the only six changed bytes** in this record between the pre-intervention snapshot and the first resurrected input: the other 452 bytes match. At the intermediate selector snapshot, the changes are `$7EC6`, `$7ED4`, and `$7EE5`; the three `$7E7A/$7E7B/$7E84` changes occur later in `OUT`. The high bytes `$7EC7`, `$7ED5`, and `$7EE6` are zero at all three checkpoints. The comparison and snapshot ancestry are checked by [`tools/verify_resurrection_record.py`](../tools/verify_resurrection_record.py).

The shared [`MI.U1` death reset](../disasm/MI.U1-death-reset.s) at `$888D–$88A0` explicitly zeros `$7ED4/$7ED5`, `$7EE5/$7EE6`, and `$7EC6/$7EC7`. The [`OUT` setup](../disasm/OUT-resurrection-init.s) clears `$7E79–$7E7B` and a table while choosing a new position; its [`HP/food loops`](../disasm/OUT-resurrection-fill.s) raise the low bytes to `$63`. In this replay, the new outdoor coordinates were `(3,8)`.

Known field meanings: `$7EC6/$7EC7` are HP and `$7EE5/$7EE6` are food in the traced paths. `$7E7A` contributes to attack damage, but its complete meaning is not established. The role of `$7E7B`, `$7E84`, and `$7ED4/$7ED5` is still being resolved; the latter is a two-byte resource value used by other code. No claim about all possible death states follows from this one replay. Future port work needs ordinary-play death traces and tests with nonzero high bytes, inventory, quests, equipment, and other state fields.
