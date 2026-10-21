# First observed dungeon monster attack

This is one ordinary-play attack after moving east to local dungeon position `(3,1)`. The [private replay verifier](../tools/verify_dng_monster_turn.py) checks the input ancestry, CPU checkpoints, player HP, damage bytes, and independent next-poll RAM. It does not establish the attack behavior of every monster or depth.

## Hit decision

The shared turn routine `$98EC` reached monster attack `$9A0A`. The [byte-matched hit fragment](../disasm/DNG-monster-hit-roll.s) at `$9A37–$9A63` calculates an 8-bit threshold:

```text
threshold = (($7ECC >> 1) + 8 * $7E7B + $38) & $FF
hit branch at $9A72 when random_byte >= threshold
```

In the observed snapshot, `$7ECC=10` and `$7E7B=1`, giving `$45`. The call to shared random-byte routine `$15B9` returned `$A6`, so the comparison selected the hit path. The meanings of the two threshold inputs, other thresholds, and ordinary-play miss frequency remain to verify.

A controlled replay stopped immediately before that random call and changed only RNG state byte `$1E27` from `$F5` to `$22`. The next random byte changed `$A6→$00`; `$00` is below `$45`, so execution entered the miss branch at `$9A64`. At the next input, HP was still `$0096` versus `$0094` in the ordinary hit replay. Local position `(3,1)` and the entire 11×11 map matched between the two replays. This proves the branch outcome for the controlled state; it does not measure the frequency of misses in ordinary play.

## Damage and HP

The ordinary damage path at `$9A95` initializes a bound with `$A506`, then calls `$9CBC` to add `$A60D[$A506]` once per `$A4FE`. In this observed state those values were `1`, `1`, and `1`, producing bound `$0002`. The [byte-matched draw loop](../disasm/DNG-monster-damage-roll.s) calls `$15B9` and rejects a draw that is at least the bound. The first observed draw `$53` was rejected; the accepted draw `$01` became damage `$0002` after adding one.

The [byte-matched subtraction](../disasm/DNG-monster-hp.s) at `$9B05–$9B1F` applies the two-byte damage to `$7EC6/$7EC7`. HP changed `$0096→$0094`, and the next input poll retained `$0094`. A later blocked movement input from `(3,1)` was followed by HP `$0092` at its next poll; that second attack's roll was not individually captured.

The code at `$9A72–$9A94` has several special branches before the ordinary draw. Larger bounds and 16-bit random handling also need runtime tests. The observed attack and controlled miss establish both threshold outcomes for this state only.
