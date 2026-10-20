# STUPH — shared support and graphics

Load range: `$0800–$1FFF`. Early regions are patterned display data. Later regions contain executable support routines used by the common engine and overlays.

| Range | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$1580–$1582` | Three-byte preface | Meaning open |
| `$1583–$15E5` | 33 consecutive `JMP` stubs, three bytes each | Callable interface |
| `$1583` | `JMP $177F` | First stub; callers in `MI.U1` |
| `$1586` | `JMP $1831` | Second stub |
| `$1589` | `JMP $1679` | Shared file-loader entry used by the `OUT` handoff |
| `$159E` | `JMP $19F3` | Called during module setup |
| `$15B9` | `JMP $1DF1` | Shared random-byte entry used by castle combat |
| `$15E3` | `JMP $1670` | Last stub |
| `$1DF1–$1E17` | [Reviewed 39-byte routine](STUPH-random.s), byte-matched | Mutates 16-byte state at `$1E18–$1E27`; returns byte at `$1E18` |

The jump table makes this file an executable dependency, despite its graphics-heavy beginning. Next: identify each target routine and its callers without treating earlier image data as code.

The random-byte entry `$15B9` jumps to `$1DF1`. The routine starts with the byte at `$1E27`, accumulates it backward through state bytes `$1E26–$1E18` while preserving ADC carry, adds `$1E27` once more into `$1E18`, then increments the 16-byte state backward until the increment does not wrap. It returns the resulting `$1E18` byte. The [reviewed source](STUPH-random.s) reassembles exactly. A castle guard-hit replay returned `$9D`. In a separate controlled replay, changing only `$1E27` from `$A6` to `$59` immediately before the call made the routine return `$02`. The latter is a counterfactual branch test, not an unmodified gameplay observation; the [private verifier](../tools/verify_cas_guard_miss.py) checks that the two intervention snapshots differ in exactly that byte.

The `GEN`→`OUT` replay reached `$1589` after the selector copied `OUT` into `$7E16` and `$B736` copied it to the ProDOS filename buffer `$BA79`. In the saved runtime state, `$BF98 & $30 == $30`, so `$1679` built `/RAM/OUT` at `$1703` and called `$B71E` at `$16AD`. This lookup returned at `$16B2` with `A=$07`, carry set. Execution then reached `$16B9`, where another `$B71E` call uses the relative `OUT` string at `$1709`. A 15-second replay did not reach its `$16C8` return; it paused at `$D388` inside the disk driver's delay loop after about 122 million additional CPU cycles. The buffer at `$BA79` still held relative `OUT`, and the game disk was still mounted. The failure mechanism is not yet established. The a2m disk mount changed the simulated head position from quarter-track 2 to 38; `tools/trace_out_disk_attempt.py --preserve-head` tests that difference with a private snapshot copy.

The controlled replay changed only the two-byte Disk II quarter-track position from 38 back to the pre-swap value 2. The same relative `OUT` read then returned at `$16C8` with `A=$00`, carry clear (cycle 47,118,575); the loader returned at `$16FC` with carry clear and its caller resumed at `$892B` (cycle 47,623,376). All 5230 bytes at `$8956` match the extracted `OUT` file. This establishes the simulated head-position change as the trigger for the failed replay. It does not establish a game-code disk-read defect. The loader also attempted its `/RAM/OUT` cache path before returning; the cache outcome is not yet verified.
