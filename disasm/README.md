# File-by-file disassembly

Each page records **verified instruction ranges and evidence**, using the original Apple II address as the key. The full `da65` listing for each file is generated locally under ignored `build/disassembly/`; it is an unreviewed linear interpretation and contains original data bytes. Pages here grow as code/data boundaries are checked. An absent range means *not yet analyzed*, not empty or unreachable.

| Phase | Files | Current status |
| --- | --- | --- |
| Startup | [U1.SYSTEM](U1.SYSTEM.md), [U1.INTRO](U1.INTRO.md), [MAKE.INDATA](MAKE.INDATA.md) | `U1.INTRO` entry, key loop, and two file requests reassembled |
| Shared engine | [MI.U1](MI.U1.md), [STUPH](STUPH.md) | Module selector and support jump table identified |
| Gameplay | [GEN](GEN.md), [OUT](OUT.md), [DNG](DNG.md), [TWN](TWN.md), [CAS](CAS.md), [SPA](SPA.md), [TM](TM.md) | Entry/transition evidence; most routines pending |
| Data | `MAPCHARS`, `TCMAPS`, `NIF` | Format analysis pending |
| Operating system | `PRODOS` | External dependency, not game disassembly |

## Recording convention

- **Instruction**: confirmed from bytes at the named load address.
- **Data**: a table, inline filename, display text, or graphic region. Do not interpret it as code merely because `da65` printed a mnemonic.
- **Inferred**: a hypothesis about gameplay or a callee's behavior; provide the address that motivated it.
- **Open**: a branch, indirect jump, or data format needing another trace.

For each routine, record its entry address, callers, outgoing calls/jumps, state read/written, and return behavior. The [dependency map](../docs/dependency-map.md) records cross-file edges; these pages hold the local evidence.
