# TCMAPS — town and castle map records

Load range: `$4000–$5DEB`; file length 7660 bytes.

## Verified container layout

The first 20 bytes hold ten little-endian absolute addresses. They are spaced 764 bytes apart; the packed payload has ten contiguous 764-byte slots. The last slot ends exactly at the end of the file.

| Slot | Address range | Packed size |
| ---: | --- | ---: |
| 0 | `$4014–$430F` | 764 |
| 1 | `$4310–$460B` | 764 |
| 2 | `$460C–$4907` | 764 |
| 3 | `$4908–$4C03` | 764 |
| 4 | `$4C04–$4EFF` | 764 |
| 5 | `$4F00–$51FB` | 764 |
| 6 | `$51FC–$54F7` | 764 |
| 7 | `$54F8–$57F3` | 764 |
| 8 | `$57F4–$5AEF` | 764 |
| 9 | `$5AF0–$5DEB` | 764 |

At `TWN` `$89BC/$89C2`, indexed reads use `$4004,X` and `$4005,X`, beginning with pointer-table entry 2. At `CAS` `$89BE/$89C4`, corresponding reads use `$4000,X` and `$4001,X`, beginning with entry 0. The pointers patch instruction operands in self-modifying copy loops.

Both loops copy **three 256-byte pages** from the selected pointer to `$B400`: 768 bytes in total. Therefore the runtime read windows for slots 0–8 include four bytes from the following packed slot. The last window reaches `$5DEF`, four bytes past the file's `$5DEB` end. What occupies `$5DEC–$5DEF` in memory after loading is unverified; a macOS port must not invent these bytes without tracing whether the game uses them. The legal slot index ranges and the internal map format remain open.

Runtime confirmation for `CAS` slot 0: after loading `TCMAPS` and `MAPCHARS`, the first castle map copied `$4014–$4313` to `$B400–$B6FF` byte-for-byte before its `$8A27` input poll. The last four copied bytes are the first four bytes of packed slot 1. Other slot selections and the out-of-file read for the final slot remain unverified.

Run `python3 tools/extract_data.py` at the repository root to write the ten **packed slots** and a checksum manifest under ignored `build/data/TCMAPS/`. `--check` validates addresses and lengths without writing data. The manifest records how many bytes of each 768-byte runtime copy are present in the source file. The public repository contains the extractor and this structural description, not the map bytes.
