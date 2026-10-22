# TM connection and isolated playable test sessions

All gameplay overlays are now connected, including TM and its NIF ending data.
This is integration coverage, not proof of every gameplay branch or complete
modernization. Exact timing and broader ordinary-play validation remain.
Original speaker output is now connected; see [native audio](native-audio.md).

## Test without acquiring a shuttle

The native application's **Test** menu provides:

- **Space Flight (Temporary Save)**: create a separate original GEN character,
  provide a shuttle fixture, and execute the original OUT B transition into SPA.
- **Time Machine (Temporary Save)**: create a separate character, supply the
  time-machine/four-gem fixture, and execute OUT B into TM's original opening.
- **Return to Game**: restore the actual machine that was suspended before
  testing, including its unsaved in-memory progress and paused/running state.

There is also a Space Test toolbar button. These are explicit application test
controls; the game canvas, text, input and rendering remain original. The title
bar identifies the temporary session. Space advances TM's original opening
pages. Restart Intro deliberately starts a fresh normal session; use Return to
Game when preserving the suspended game is intended.

Test sessions do not read or overwrite the actual player record at
`~/Library/Application Support/UltimaI/Characters/U1.VARS`. They use a unique
macOS temporary directory, `UltimaI-Test-<UUID>/U1.VARS`. Every file service,
including Q after returning outdoors, uses that test directory. Switching between
SPA and TM tests retains the initially suspended actual game. A test character's
progress is separate and is not merged into normal play.

The setup uses original GEN allocation/race/class/name/save/load code, then
prepares only the explicit vehicle/qualification fixture. Ordinary game purchase
and qualification requirements are not changed. The interactive TM test also
keeps the original combat parameters.

## TM implementation

TM loads at `$8956`, retains its original entry `$8AD7`, four page prompts,
main loop/input `$8E5E/$9815`, movement, gem and attack logic. It uses the same
Ghidra-generated address-preserving execution as the other overlays. The host
loads NIF at `$4000` when requested through `$B703`.

The ending's original copy moves 8192 bytes into `$6000–$7FFF`, overwriting the
normal resident engine/player region as the original does. The ending then
runs its own TM/STUPH animation and final input loop. NIF has 7680 row-packed
image bytes; the copied inherited 512-byte tail is not consumed by that final
192-row image. The host does not replace the ending with a screenshot.

## Verification

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_test_sessions.py
python3 tools/check_all.py
```

The headless verifier invokes the same test-session constructor as the menus.
SPA accepts a Right input through live polling. TM accepts all four opening-page
Spaces, reaches its main loop at `(4,5)`, and moves Right to `(5,5)`.
Both HGR pages at SPA test entry, TM opening entry and TM first main input match
independent original snapshots: **49,152 bytes**.

A separate automated ending probe raises temporary player HP to 3000 to survive
the short approach, walks to the gem, and invokes original G. It lowers Mondain
HP to 1 before ordinary A/direction input. This controlled branch test reaches
the original victory, NIF load, animation and final input `$9132`; all **7680
NIF image bytes** match their final HGR scanline positions. It is not an ordinary
full-health victory and does not change interactive test or real-save combat.

The verifier compares the actual player file before and after the complete run
and confirms it is unchanged. Generated characters, fixture RAM, original
assets, ending captures and the built application remain private under `build/`
for CLI tests or the temporary session directory for menu use. Actual AppKit
menu/window interaction still needs a normal macOS session; tool execution tests
the constructor, code, input, rendering and save isolation headlessly.
