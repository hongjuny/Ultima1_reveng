# STUPH — shared support and graphics

Load range: `$0800–$1FFF`. Early regions are patterned display data. Later regions contain executable support routines used by the common engine and overlays.

| Range | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$1580–$1582` | Three-byte preface | Meaning open |
| `$1583–$15E5` | 33 consecutive `JMP` stubs, three bytes each | Callable interface |
| `$1583` | `JMP $177F` | First stub; callers in `MI.U1` |
| `$1586` | `JMP $1831` | Second stub |
| `$159E` | `JMP $19F3` | Called during module setup |
| `$15E3` | `JMP $1670` | Last stub |

The jump table makes this file an executable dependency, despite its graphics-heavy beginning. Next: identify each target routine and its callers without treating earlier image data as code.
