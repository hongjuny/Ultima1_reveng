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

Both loops copy **three 256-byte pages** from the selected pointer to `$B400`: 768 bytes in total. Therefore the runtime read windows for slots 0–8 include four bytes from the following packed slot. The last window reaches `$5DEF`, four bytes past the file's `$5DEB` end. The selected castle run found the inherited RAM bytes `FF FF D5 FF` there, unchanged by `TCMAPS` loading, and copied them to `$B6FC–$B6FF`. These are snapshot-specific RAM contents, not part of the file format. The legal slot indices in ordinary play and the complete internal map format remain open.

Runtime confirmation for `CAS` slot 0: after loading `TCMAPS` and `MAPCHARS`, the first castle map copied `$4014–$4313` to `$B400–$B6FF` byte-for-byte before its `$8A27` input poll. The last four copied bytes are the first four bytes of packed slot 1. Slots 1–8 and ordinary selection of slot 9 remain unverified.

A paired [final-slot replay](../tools/trace_tcmaps_last_slot.py) started from the same `CAS` entry, changing only `$7EED` from 0 to 9 before the map selection. At `$89CE`, the selected pointer was `$5AF0`; at copy completion `$89E0`, `$B400–$B6FB` held all 764 file bytes and `$B6FC–$B6FF` held the inherited four RAM bytes. A separate [tail control](../tools/trace_tcmaps_tail_effect.py) zeroed only those four destination bytes at `$89E0`. Both continuations reached the first castle key poll `$8A27` at the same cycle count and CPU state. Their full main RAM differed only at those four addresses. The [verifier](../tools/verify_tcmaps_last_slot.py) checks snapshot ancestry, file match, copied bytes, and the paired difference.

The reviewed `CAS` tile lookup bounds coordinates to 38 columns and 18 rows, giving 684 tile bytes. Its actor arrays start at `$B6AC` and use 16 entries in each of five arrays through `$B6FB`; 684 + 5×16 = 764. This supports treating the last four copied bytes as padding for the 768-byte copy in this castle path. The paired replay establishes no effect **through the first key poll**; it does not prove that no later routine reads `$B6FC–$B6FF`.

Run `python3 tools/extract_data.py` at the repository root to write the ten **packed slots** and a checksum manifest under ignored `build/data/TCMAPS/`. `--check` validates addresses and lengths without writing data. The manifest records how many bytes of each 768-byte runtime copy are present in the source file. The public repository contains the extractor and this structural description, not the map bytes.
