# MAKE.INDATA

Load range: `$1E00–$5434`. Intro support file with mixed code and data.

| Address | Disassembly / evidence | Interpretation |
| --- | --- | --- |
| `$1E00` | `JMP $1F17`; loader's indirect target `$BAF2` held `$1E00` | Executed file entry |
| `$1E03` | Decoder called by `$1F17`; reads from `$49EC` | Output format and bounds remain to classify |
| `$1EFD–$1F16` | Page copy helper, reconstructed and byte matched | Copies `$FF` pages from `X:Y` source to A-selected destination page |
| `$1F17–$1F41` | Initial setup, reconstructed and byte matched | Copies two payload ranges, calls `$1E03`, `$8700`, then `$1F5C` |
| `$1F5C` | Writes `$4000–$5FFF` and video soft switches | Display setup; timing and exact effects pending |

`U1.INTRO` calls `$B70C` at `$0F28` with this inline filename. The live loader at `$B70C` jumps to `$B7D8`, later calls `$B801`, and `$B801` jumps indirectly through `$BAF2`. At the successful return, `$BAF2=$1E00`, the carry flag is clear, and execution continues at `$0F41`. The memory at `$1E00–$1FFF` still matches the first 512 file bytes.

The code copies original file bytes `$2000–$27FF` to `$8700–$8EFF` (2048 bytes), then `$27BD–$4DBC` to `$6000–$85FF` (9728 bytes). Both destination ranges match the file byte for byte in the private post-load snapshot. The original `$2000` location differs from the file after the routine returns because this range is reused for display/work memory. This explains the earlier whole-file mismatch at `$2000`; a post-execution image cannot be compared directly with the file loaded at `$1E00`.

Reviewed source: [copy helper and initial setup](MAKE.INDATA-copy-init.s). It reassembles exactly for `$1EFD–$1F41`. The decoder, relocated `$8700` code, graphics data, and return effects remain to analyze. Do not treat the linear draft as continuous code.
