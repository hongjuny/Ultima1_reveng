# File-by-file disassembly

Each page records **verified instruction ranges and evidence**, using the original Apple II address as the key. The full `da65` listing for each file is generated locally under ignored `build/disassembly/`; it is an unreviewed linear interpretation and contains original data bytes. Pages here grow as code/data boundaries are checked. An absent range means *not yet analyzed*, not empty or unreachable.

The [assembly address atlas](../docs/assembly-atlas.md) locates every reviewed fragment within its original file. The [Ghidra call atlas](../docs/ghidra-call-atlas.md) places candidate functions and cross-module calls into the game loop; Ghidra output is a lead for review, not byte-matched or runtime proof.
The [memory and zero-page atlas](../docs/memory-and-zero-page.md) records which scratch addresses are reused across scenes and where automatic code/data classification is still unresolved.

| Phase | Files | Current status |
| --- | --- | --- |
| Startup | [U1.SYSTEM](U1.SYSTEM.md), [U1.INTRO](U1.INTRO.md), [MAKE.INDATA](MAKE.INDATA.md) | `U1.SYSTEM` startup handoff, `U1.INTRO` entry, both key polls, two file requests, and `MAKE.INDATA` page copy setup reassembled |
| Shared engine | [MI.U1](MI.U1.md), [STUPH](STUPH.md) | Module selector, 34 support vectors, keyboard latch, and inline text-output chain identified; one glyph's screen-memory write traced |
| Gameplay | [GEN](GEN.md), [OUT](OUT.md), [DNG](DNG.md), [TWN](TWN.md), [CAS](CAS.md), [SPA](SPA.md), [TM](TM.md) | All six gameplay overlays have a traced first command turn. `SPA`/`TM` entry used controlled craft/map/flag values; ordinary acquisition and full rule coverage remain open |
| Data | [MAPCHARS](MAPCHARS.md), [TCMAPS](TCMAPS.md), [NIF](NIF.md), generated [U1.VARS](U1.VARS.md) | `MAPCHARS` 128×8 scanline planes and castle font swap traced; `TCMAPS` packed slots and final-copy padding observed; `NIF` packed rows and final HGR page matched; `U1.VARS` save image and initial fields verified |
| Operating system | `PRODOS` | External dependency, not game disassembly |

## Recording convention

- **Instruction**: confirmed from bytes at the named load address.
- **Data**: a table, inline filename, display text, or graphic region. Do not interpret it as code merely because `da65` printed a mnemonic.
- **Inferred**: a hypothesis about gameplay or a callee's behavior; provide the address that motivated it.
- **Open**: a branch, indirect jump, or data format needing another trace.

For each routine, record its entry address, callers, outgoing calls/jumps, state read/written, and return behavior. The [dependency map](../docs/dependency-map.md) records cross-file edges; these pages hold the local evidence.

For the macOS port, also record input timing, Apple II hardware effects, data format, and an emulator scenario that can confirm the interpretation. The [fidelity inventory](../docs/porting-fidelity.md) tracks these requirements across modules.
