# Analysis log

## 2026-10-20 — Inventory and first control-flow pass

- Checked all 16 extracted file sizes against the ProDOS catalog.
- Verified that files contain their memory image directly, without a four-byte BIN header.
- Located startup jumps and inline filenames with hex inspection and `da65`.
- Identified the shared `$8956` load address for seven mutually exclusive gameplay modules.
- Corrected `STUPH`'s classification after finding its 33-entry executable jump table at `$1583–$15E5` and the loader call that installs it.
- Traced the `$88FD` selector's name table and its initial `GEN` path; identified an `OUT` exit that returns to it.
- Mapped direct returns from `GEN`, `DNG`, `TWN`, `CAS`, and `SPA` into `OUT`, plus `OUT` selector values for space, castle, town, and dungeon transitions.
- Added a local listing generator. Its output is an unreviewed aid, not a reconstructed source or a publication artifact.

Unknowns: the precise ProDOS loader semantics used by these files, module selection rules, persistent state layout, and data encodings. Future entries should cite addresses and distinguish observations from inferences.

## 2026-10-20 — File-by-file record and dependency map

- Added a page for each executable game file, with known entry/transition addresses and explicit open ranges.
- Separated file requests, callable shared routines, and mutually exclusive overlays in the dependency map.
- Reconstructed the `MI.U1` selector at `$88F8–$893E` as ca65 source. Reassembly matches all 71 bytes of the supplied extraction.
- Reconstructed four `U1.INTRO` fragments: two entry vectors, the key loop, and both inline file requests. Reassembly matches all 92 bytes across those ranges.
- Reconstructed `GEN`'s 19-byte menu choice and `OUT`'s 64 bytes of space/location dispatch. Reassembly matches all three fragments; the known selector cases now have confirmed instruction boundaries.

## 2026-10-20 — Porting fidelity and data extraction

- Adopted byte, static, runtime, and hypothesis evidence levels for the eventual macOS port.
- Decoded `TCMAPS`'s 20-byte pointer table into ten contiguous 764-byte packed slots and added a local extractor with checksums.
- Reassembled the `TWN` and `CAS` self-modifying map copy loops. Each copies 768 bytes from a selected slot, overlapping the next slot by four bytes; the final loop reads four bytes past the file payload. The value and use of those last bytes remain to trace.

## 2026-10-20 — Stage 0 extraction baseline

- Recorded the local WOZ image, all 16 extracted files, tool versions, and a pinned a2m build in an ignored baseline manifest.
- Independently re-extracted the WOZ with CiderPress II and confirmed all 16 files match `extracted/` byte for byte.
- Added one command for the available local checks and a boot-snapshot capture script.
- Built a2m 3.0.0 at commit `d863ad98487639445db16134d260221839cb72e9`. Headless WOZ mounting starts, but the current agent sandbox denies localhost socket binding, so `$2088` runtime capture and replay remain pending in a normal local terminal.
- A first local-terminal run of `capture_boot.py` timed out. Source inspection showed a2m parses `--break=2088` as decimal; the script now installs `break-exec $2088` through the control port and preserves the primary failure when stopping a2m. Runtime confirmation still awaits a successful rerun.
- The corrected capture succeeded in a normal local terminal: `PC=$2088` at frame 310, cycle 5,270,292, with the same CPU state after restoring the local snapshot. The combined local checks passed. Prepared the next private trace from `$2088` to `U1.INTRO` entry addresses `$0800` and `$0F23`.
- The first startup trace waited for `$0800` and timed out. It did not record the PC at timeout, so no conclusion about the actual handoff follows. Revised the trace to observe `$2220`, `$0136`, then either `$0800` or `$0803`, and to print CPU/runtime state if a milestone is missed.
- The revised trace timed out before `$2220`; after a forced pause, PC was `$21D4` and the CPU had executed about 20.6 million cycles. `$21D4` lies in the operand of `JMP $0133`, following the inline “Can't find a startup file” message. The script now breaks at the preceding `$21A0` setup point and both sides of the `$2006` test at `$21D3/$21D6`, and records the live header and low-memory code before continuing.
- The next run also missed `$21A0` and paused at the same `$21D4`/cycle count. Direct control-port execution is unavailable in the agent sandbox (`Operation not permitted` on localhost socket bind). Source inspection showed that a2m's `load-state` RPC waits for completion; the trace now uses that RPC instead of startup `--sna`, confirms paused state and the `SEI` byte at `$2088`, then steps one instruction to `$2089` before installing later breakpoints. This change is pending a local-terminal run.
