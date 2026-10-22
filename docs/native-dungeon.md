# Original dungeon entry on macOS

DNG now participates in the native overlay pipeline. E on a dungeon tile enters
the original first-person view, floor generation, input and movement routines.
The view is built by original DNG/MI.U1/STUPH code and displayed through the same
HGR renderer as the introduction, outdoor map, towns and castles.

The existing outdoor Q save remains at:
`~/Library/Application Support/UltimaI/Characters/U1.VARS`.
It is one 458-byte original-format player record. A later confirmed save replaces
it; application rebuilds do not delete it. GEN B reads it after restarting.
DNG's original Q handler says saving is only allowed outdoors; this port retains
that restriction. Use the entrance ladder's K command to return outdoors before
saving. There is no added automatic dungeon snapshot save.

## Integration and controls

The native file host can load DNG at `$8956`, and the runtime overlay dispatcher
executes Ghidra-generated, byte-checked DNG instruction candidates. No new host
movement, floor-generation or perspective-drawing algorithm is substituted.
The DNG file ends at `$B098`; the original generator creates the 11×11 working
map at `$B099–$B111` beyond the file payload.

At first entry, depth is 1, local position is `(1,1)` and facing is `(0,+1)`.
Up advances. The other arrow keys retain the original facing behavior (the
first-entry Right/Left outcomes face `(-1,0)`/`(+1,0)`, and Down faces `(0,-1)`).
K operates a ladder; on the initial entrance tile and initial facing it returns
to Sosaria. Deeper-floor ladder behavior and full combat are not established by
this integration test.

## Verification

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_dungeon.py
python3 tools/check_all.py
```

The replay creates and saves a character, loads it through GEN B, walks from
`(39,33)` to the castle tile `(30,31)`, then follows the existing 29-move route
to dungeon tile `(43,15)` and presses E. It uses ordinary keys and no reference
RAM or coordinate injection. Four independently recorded original checkpoints
match both HGR pages exactly: the outdoor dungeon tile, first dungeon input,
first forward move and post-K outdoor return. This checks **65,536 video bytes**
and **430,080 pixels** against an independent raster implementation.

The native floor has the original 11×11 bounds, wall border, entrance ladder,
depth and initial local coordinates. The shared random stream produces different
actor positions and one random content tile than the older reference: seven
initial map bytes differ even though the tested views match. Full generated-map
identity is therefore not claimed. The original random and generator routines
execute; no reference map is copied into the application.

Independent input trials verify the four initial movement/facing outcomes.
A separate trial disables capture stops and advances through the interactive
6,000-instruction polling budget, reaching `(1,2)` after Up. Q leaves the save
count unchanged and returns through the original outdoors-only message path.
Restoring the native entrance state for an independent K trial returns through
the common OUT loader and restores outdoor `(43,15)` and its world map.

These tests cover entry, selected first-floor controls, the save restriction and
outdoor return. They do not claim validation of every generated floor, monster,
spell, attack, ladder condition or quest. Space is also connected; see [SPA integration](native-space.md). TM remains
unconnected. Audio and cycle-accurate pacing remain pending. Original
assets, generated Swift, map data, player records and captured frames remain
private under ignored `build/`.
