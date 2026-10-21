# Native Sosaria entry

The macOS application follows the original GEN B path: load the saved player
record, validate its `$01CA` header, copy `$6000–$61C9` into `$7E6D–$8036`, select
OUT through `$88FB/$88FD`, then execute OUT's initialization and main loop.
The game draws its own status panel, world tiles, avatar and command text through
MI.U1/STUPH. No native map widgets, replacement fonts or translated text are used.

## Running

```sh
python3 tools/build_macos_app.py
open "build/Ultima I.app"
```

At the title press Return/Space. In GEN, use A to create and save a character,
then B to continue the saved game. A previously saved character can be loaded
with B after restarting the application. The record lives at
`~/Library/Application Support/UltimaI/Characters/U1.VARS`.

Arrow keys move in Sosaria; Space passes a turn; Q saves through the original
outdoor command handler. The original keyboard dispatch and game loop execute
without host-side movement or terrain rules. The interactive outdoor scheduler
uses 6,000 translated instructions per display tick, rather than the faster
intro/GEN budget. This is approximate pacing, not a cycle-accurate claim.

## Translation and host boundaries

OUT is analyzed by Ghidra in the private Startup project and receives the same
byte-checked speculative instruction export as the resident modules. Runtime
execution selects the currently loaded GEN or OUT overlay at `$8956`; MI.U1 and
STUPH remain resident. Inline strings, self-modifying operand updates, map
preparation and tile drawing execute in the translated original code.

The native host implements these file-wrapper contracts:

| Entry | Inline arguments | Native action |
| --- | --- | --- |
| `$B736` | Filename pointer (2 bytes) | Populate the original Pascal pathname buffer at `$BA79` |
| `$B721` | Destination and filename pointer (4 bytes) | Read U1.VARS into the requested RAM range |
| `$B71E` | Filename pointer (2 bytes) | Load OUT at its original auxiliary address `$8956` |
| `$B724` | Source, length and filename pointer (6 bytes) | Persist the player record, then resume the original caller |

The host returns a cache miss for `/RAM/` lookups; it does not implement a RAM
disk or Disk II hardware. Local file loads replace disk reads while the common
selector and STUPH load control flow remain original. Loader return flags and
inline argument skipping follow the observed callers. The host does not inject
reference RAM, world maps or reference screenshots into the running app.

## Verified behavior

```sh
python3 tools/verify_native_sosaria.py
python3 tools/check_all.py
```

A private headless replay starts at the intro, creates and saves an original
GEN character, chooses B, and reaches OUT input at `$8A6C`. Four movement trials
start independently from that native checkpoint. They match existing Apple II
replays for the first input and all four directions:

- Both HGR pages match exactly at all five checkpoints: **81,920 video bytes**.
- An independent raster model matches **537,600 output pixels**.
- All five 4,096-byte world maps match: **20,480 map bytes**.
- Coordinates and 456 player-record bytes match; two original random-generated
  fields at `$7EEF/$7EF0` are timing-dependent and excluded from that comparison.
- Space returns through the main loop; Q writes all 458 record bytes exactly.
- A second native process chooses GEN B and restores all 458 saved bytes and
  the saved outdoor position.
- A separate trial disables capture stops and accepts Up through the actual
  timer-budgeted polling/viewport-rendering path.

The original starting coordinates `(39,33)` become `(39,32)`, `(39,34)`,
`(40,33)` and `(38,33)` for Up, Down, Right and Left respectively. The per-trial
RAM, active page, PNG and RGBA outputs remain under ignored
`build/macos-startup/sosaria/`.

## Current scope

This connects character persistence and outdoor entry, rendering, four-direction
movement, passing and saving. It does not establish that every OUT command or
long gameplay sequence is correct. Entering a town, castle, dungeon, space or
time-machine overlay is the next integration work; those overlays are not yet
included in this app. Unsupported module requests stop with an English error.
Audio is still not connected, and CPU timing is approximate. Original data,
generated translations and the application bundle remain private.
