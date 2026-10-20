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
| `$15E3` | `JMP $1670` | Last stub |

The jump table makes this file an executable dependency, despite its graphics-heavy beginning. Next: identify each target routine and its callers without treating earlier image data as code.

The `GEN`→`OUT` replay reached `$1589` after the selector copied `OUT` into `$7E16` and `$B736` copied it to the ProDOS filename buffer `$BA79`. In the saved runtime state, `$BF98 & $30 == $30`, so `$1679` built `/RAM/OUT` at `$1703` and reached its first file call at `$16AD`. The code has another file-call branch at `$16B9` using the relative name if the first attempt fails. The return from the first call and the later overlay load are still unobserved; `tools/trace_out_ram_attempt.py` probes the first return.
