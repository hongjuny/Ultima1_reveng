# MAKE.INDATA

Load range: `$1E00–$5434`. Intro support file with mixed code and data.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$1E00` | `JMP $1F17` | File entry |
| `$1E03` onward | Early 6502 instructions, followed by large patterned regions | Mixed file; boundaries pending |

Its name is passed to a file request by `U1.INTRO` at `$0F28`. The purpose of the entry routine and the large data regions are open. Do not use the linear draft as a continuous code listing.
