# File and memory map

Load addresses come from the ProDOS `Aux` field in the disk catalog. The extracted files have no embedded load address header. End addresses below are inclusive. Sizes were checked against the catalog and local files.

| File | Type | Load range | Size | Initial classification |
| --- | --- | --- | ---: | --- |
| `U1.SYSTEM` | SYS | `$2000–$2691` | 1682 | startup program |
| `U1.INTRO` | BIN | `$0800–$11A4` | 2469 | intro code and display data |
| `MAKE.INDATA` | BIN | `$1E00–$5434` | 13877 | intro support, mixed code/data |
| `MI.U1` | BIN | `$7000–$89BC` | 6589 | common engine, tables, loader |
| `GEN` | BIN | `$8956–$AC39` | 8932 | character generation module |
| `OUT` | BIN | `$8956–$9DC3` | 5230 | outdoor module |
| `DNG` | BIN | `$8956–$B098` | 10051 | dungeon module |
| `TWN` | BIN | `$8956–$AA62` | 8461 | town module |
| `CAS` | BIN | `$8956–$9EE9` | 5524 | castle module |
| `SPA` | BIN | `$8956–$B01F` | 9930 | space module |
| `TM` | BIN | `$8956–$A910` | 8123 | time machine/finale module |
| `MAPCHARS` | BIN | `$0800–$0BFF` | 1024 | graphic data candidate |
| `STUPH` | BIN | `$0800–$1FFF` | 6144 | graphics and shared routine table |
| `TCMAPS` | BIN | `$4000–$5DEB` | 7660 | map data candidate |
| `NIF` | BIN | `$4000–$5DFF` | 7680 | data candidate |
| `PRODOS` | SYS | `$2000–$59FF` | 14848 | Apple ProDOS, separate from game code |

The seven gameplay modules have identical load addresses and are mutually exclusive in the main address space. `MI.U1` extends to `$89BC`, so loading a module at `$8956` also replaces its final `$67` bytes. This is a phase change in the loader, not one continuous static memory image. Likewise the data files and intro share load ranges; their contents belong to different moments of execution.

`STUPH` needs special care: much of its early area looks like graphics, but `$1583–$15E5` is a 33-entry jump table used by `MI.U1` and gameplay modules. It is part of the executable game's shared support code.

For Ghidra, import each raw file with the 6502 language and its listed base address. Keep modules in separate programs or separate overlay address spaces. Do not let automatic analysis turn the entire file into code; embedded data and inline strings need manual boundaries.
