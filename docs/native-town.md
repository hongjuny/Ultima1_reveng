# Original town entry on macOS

The application now loads and executes TWN through the original OUT E command.
The original renderer draws the English town name, town map, NPCs, command text,
and status panel. Movement/collision and return to Sosaria execute in original
TWN/MI.U1/STUPH code; no replacement town simulation is introduced.

## Controls and verified route

From the initial outdoor position `(39,33)`, press Up twice, Left ten times,
then Down once. This reaches the town tile at `(29,32)`; press E to enter
Britain. This route starts from a newly created character, not an arbitrary
saved position. The neighboring tile `(30,31)` is a castle and requires the CAS
overlay, which is now connected; see [castle entry](native-castle.md).

The town entrance is local `(19,17)`. Up moves into town. Walking Down off the
southern map edge returns to Sosaria at the saved outdoor position `(29,32)`.
The application uses the existing original keyboard mapping and English game
screens. Q saving remains available after returning outdoors.

## Loading contracts

Ghidra exports byte-checked TWN execution candidates into ignored build output.
The native dispatcher selects TWN at `$8956` while keeping MI.U1/STUPH resident.
The common file loader can now request either OUT or TWN.

TWN calls `$B733` with inline `TCMAPS` and `MAPCHARS` filenames. This service
sets the original pathname buffer; it does **not** load immediately. TWN then
passes its destination through STUPH `$158C` and the existing `$B721` host file
service. TCMAPS loads at `$4000`; MAPCHARS loads at `$B000`, despite its file
auxiliary address being `$0800`. Both files remain private application resources.
The original town code selects and copies 768 bytes from packed map record 2
into `$B400–$B6FF`, including four bytes from the next 764-byte record.

## Verification

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_town.py
python3 tools/check_all.py
```

The native replay begins at the introduction, creates/saves a character, enters
Sosaria through GEN B, walks the 13-key route without changing coordinates or
loading reference RAM, and presses E. It compares the outdoor town-tile checkpoint
and the first town input with independently recorded original Apple II states:

- Both HGR pages match at both checkpoints: **32,768 bytes**.
- Independent raster comparison matches **215,040 output pixels**.
- All 768 town-map/actor bytes match the original initial town record.
- The loaded MAPCHARS bytes match the local original file at `$B000`.
- Up reaches `(19,16)` through both capture-controlled and live polling paths.
- Down twice from there returns to OUT at `(29,32)` and restores the world map.

Later movement is not claimed to match every reference pixel: the existing Up
reference differs by one NPC-state byte and twelve HGR bytes, while player
coordinates and static town tiles agree. NPC updates depend on runtime/random
state and pacing. The application executes the original NPC code; aligning its
input timing and random state with each original replay remains separate work.

The app now covers town entry, basic movement and outdoor return. Full shop,
conversation, combat and all-town validation are not established by this test.
Castles are also connected; see [castle entry](native-castle.md). Dungeons are now connected; see [dungeon entry](native-dungeon.md). Space and
time-machine overlays remain outside this app build.
Audio and cycle-accurate timing are still pending. Generated source, original
assets, captures and the application bundle remain under ignored `build/`.
