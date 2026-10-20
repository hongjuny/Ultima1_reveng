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
- Correction: the next local-terminal run found `AC 0F` at `$2088` after restore. These bytes match the extracted `PRODOS` image, whereas `U1.SYSTEM` begins `78 A9` there. The earlier PC-only snapshot captured ProDOS, so the asserted game-entry runtime confirmation and the `$21D4` error-path interpretation above are retracted. The capture now compares the loaded `U1.SYSTEM` header and entry bytes before saving and after restoring. A fresh game-entry capture remains pending.
- The memory-verified capture skipped the ProDOS `$2088` hit, then timed out at `$21D4`. Static inspection of extracted ProDOS identifies `$21D4` as its self-loop after a `RELOCATION / CONFIGURATION ERROR` message. This places the failure in ProDOS initialization, before `U1.SYSTEM`. CiderPress copied all 280 blocks of the supplied WOZ to a private `.po` image without errors; its catalog matches the original. The capture script now records ProDOS MLI return states and retries booting that block-equivalent image if WOZ boot fails. Runtime success of the converted image remains unverified.
- The retry established the split: WOZ boot returned `A=$27` from ProDOS `GET_PREFIX` and entered its `$21C3` error path; the block-equivalent `.po` boot reached `U1.SYSTEM` `$2088` at frame 524, cycle 8,915,922. Memory at `$2000–$200F` and `$2088–$2097` matched the extracted `U1.SYSTEM` before and after snapshot restore. The private baseline now records the actual boot medium. The cause of the WOZ-only failure and the game-to-intro handoff remain open.
- The next private trace restored the verified game snapshot, stepped `SEI`, then hit `U1.SYSTEM` `$21A0` and the startup-file branch at `$21D6` (`Y=$08`; live header `U1.INTRO`). It then hit `$2220`, low-memory `$0136`, `U1.INTRO` `$0800`, and `$0F23`. Memory at `$0800` matched the extracted intro. A private snapshot at `$0F23` anchors the next support-file trace; no keyboard input was injected.
- The support-file trace hit `$B70C`, returned at `$0F37` with carry clear, and reached `$0F41`. Its initial whole-file comparison differed first at `$2000`. Offline inspection of the private snapshot and byte-matched `MAKE.INDATA` `$1EFD–$1F41` code explained this: the file executes through loader pointer `$BAF2=$1E00`, copies 2048 bytes from `$2000–$27FF` to `$8700–$8EFF` and 9728 bytes from `$27BD–$4DBC` to `$6000–$85FF`, then reuses its original load area. Both copied ranges match the extraction exactly. Added a snapshot verifier so the relocation claim can be repeated without publishing binary data.
- The first intro-to-engine trace waited 15 seconds for `$1039` but paused at `$0A0F` inside the intro's drawing code (cycle 39,986,816). The extracted code shows an earlier animation keyboard poll at `$0B23`; ordinary keys branch from there to `$0B50`. Reassembled `$0B23–$0B4F` byte-for-byte and moved the next trace's breakpoint to this first poll. The screen-construction wait now uses 8 MHz turbo with periodic CPU progress reports.
- The next run reached `$0B23` at cycle 24,815,855, but missed `$0B50` and timed out at `$160F` after 147,340,528 cycles. Inspection of a2m's `RUNTIME_COMMAND_PASTE_TEXT` handler showed the cause: the control-port `key` command resumes execution as it injects a key. The trace had installed its dispatch breakpoint only after issuing `key`. It now arms `$0B50`, `$B70C`, `$7000`, and `$8956` while paused at the poll, then sends the key and waits for the first transition. This correction awaits a local-terminal run.
- The corrected replay reached `$0B50` with `A=$C1` 1308 cycles after the first `$0B23` poll, then `$B70C` 14 cycles later. `MI.U1` entered at `$7000` (cycle 27,292,722), and its startup loader at `$8956` three cycles later. The private snapshot contains all 6589 bytes of `MI.U1` unchanged at `$7000`, while `U1.INTRO` is still present at `$0800`. Added a local snapshot verifier and prepared the next replay through `STUPH` and `GEN`; those loads are not yet observed.
