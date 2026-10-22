# Original SPA space module on macOS

SPA now loads at `$8956` through the original OUT B boarding command and common
selector. The original code builds the space display, navigation/view modes,
starfield, ship/status graphics, motion, fuel costs and firing logic. The native
host adds SPA to its file allowlist and overlay dispatcher; no replacement space
simulation or English/Korean UI is inserted into the game.

In normal play, acquire a space shuttle through the original game, stand on its
tile, and press B. Original acquisition, docking, vehicle and fuel checks remain
active. The app does not supply a free shuttle or alter the player's save.

## Controls and boundaries

- Direction keys retain the original motion/heading behavior and fuel costs.
- V enters the separate flight/combat view; its input table differs from the
  ordinary SPA table. F fires in that view, and V returns to ordinary SPA input
  when the original conditions permit it.
- Landing runs through original position/collision checks and returns via the
  common OUT selector. No universal instant-return key is added.
- Original notices and key waits remain in English and use original rendering.

Ghidra exports byte-checked speculative SPA instruction candidates, as with the
other overlays. The application executes only reached PCs. Rendering, inline
strings and self-modified call operands remain original. Interactive execution
uses the existing 6,000-instruction display budget; timing is approximate.

## Verification and explicit fixtures

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_space.py
python3 tools/check_all.py
```

The private replay starts at the intro, creates/saves a character and enters
OUT through GEN B. It then supplies a **controlled shuttle fixture** by changing
only the current map tile to `$1C` (and ensuring not already aboard), matching
the existing original-emulator boarding probe. B executes the real OUT transition
and reaches SPA's first `$8A5F` input. Natural shuttle purchase/acquisition has
not been replayed as part of this test.

At that first input, both HGR pages match the original controlled reference:
**16,384 bytes** and **107,520 independently checked pixels**. Four independent
trials from the native SPA entry match the original direction/fuel observations:

| Input | Local motion bytes | Heading | Fuel |
| --- | --- | --- | --- |
| Up | `($FE,0)` | 3 | 995 |
| Down | `(2,0)` | 3 | 995 |
| Right | `(0,0)` | 0 | 998 |
| Left | `(0,0)` | 2 | 998 |

Shield remains 1000. The trials also compare all retained state bytes from the
original four-direction report. V enters `$9361` with Fuel 995; F returns through
its view loop with Fuel 985, and nested V reaches `$8A5F` again. This verifies
firing/consumption and mode return, not a natural aimed kill or every outcome.
A separate trial disables capture stops and accepts Right through live polling.

For landing, another **controlled approach fixture** changes only the native
ship's `$6E/$6F` position to an already generated planet's coordinates. Space
then executes original rendering, collision and landing code and loads OUT.
No PC jump or forced return is used. This verifies that landing integrates with
the host loader, not a complete ordinary-key navigation route to the planet.

Capture stops now require both an empty keyboard strobe and empty original key
queue (`$78`). SPA's view renderer can buffer a key before jumping to `$15BF`;
pausing there with a queued key would incorrectly treat an intermediate polling
step as a completed command. Interactive execution continues to use the original
keyboard routines unchanged.

## Remaining validation

Full natural acquisition, navigation, docking/refuelling, aimed kills, progression
and long space sessions need further validation. Their original code is included
but inclusion is not proof of every branch. The remaining unconnected gameplay
overlay is TM (time machine, final encounter and ending). Audio and cycle-accurate
pacing remain pending. Original files, generated Swift, fixture RAM, screenshots
and the application remain private under ignored `build/`.
