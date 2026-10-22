# Original castle entry on macOS

CAS is now included in the native application's original overlay pipeline.
Press E on a castle tile to enter. The original CAS code renders the castle,
actors, English text and status panel, processes movement/talk, and returns to
Sosaria through the original map exit. Existing U1.VARS saves remain compatible.

The first reference castle is reached from a new character's `(39,33)` outdoor
position with Up twice and Left nine times, to `(30,31)`. E enters at local
`(0,9)`. Right enters the castle; Left from the entrance returns to Sosaria.
The separate town tile at `(29,32)` still selects TWN.

CAS uses the same native file-wrapper contracts already established for TWN:
`$B733` sets the inline filename, and STUPH's explicit-destination load places
TCMAPS at `$4000` and MAPCHARS at `$B000`. The original map-copy routine selects
and copies the packed castle record into `$B400–$B6FF`. Ghidra's private export
and byte checks generate address-preserving CAS execution candidates; runtime
execution selects CAS in the overlay dispatcher.

## Verification

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_castle.py
python3 tools/check_all.py
```

The replay creates/saves a character, enters Sosaria, walks to the castle, and
presses E without loading reference RAM or changing coordinates. It compares
the outdoor castle-tile and initial castle-input checkpoints with existing
original Apple II snapshots:

- Both HGR pages match at both checkpoints: **32,768 bytes**.
- Independent raster comparison matches **215,040 output pixels**.
- The initial 768-byte castle map/actor record matches the original state.
- Right moves from `(0,9)` to `(1,9)` through the original collision path.
- A separate walking trial reaches the king tile `(31,6)` using 38 ordinary
  direction inputs. T opens the king dialogue; S executes service acceptance
  and changes quest byte `$7EAF` from 0 to 1.
- A separate entrance trial exits Left, loads OUT again, restores `(30,31)` and
  the original world map.

The independent trials restore only their own native-generated entrance state.
The king route itself uses ordinary keys, unlike the older original-emulator
branch test that injected king coordinates. Later NPC/dialogue frames are
captured but are not claimed to match every reference pixel or cycle.

This verifies entry, selected movement/talk/service behavior and outdoor return.
It does not establish all castle quests, combat, rescue sequences, or every
castle variant. Original NPC/quest logic executes rather than being replaced.
Dungeons are now connected; see [dungeon entry](native-dungeon.md). Space and
time-machine overlays remain outside the native app build.
Audio and cycle-accurate pacing remain pending. Original assets, generated code,
application bundles and captures stay private under ignored `build/`.
