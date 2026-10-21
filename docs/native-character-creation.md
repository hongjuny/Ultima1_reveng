# Original Apple II character creation on macOS

The application now executes the original introduction → MI.U1 → STUPH → GEN
path and displays GEN's own HGR output. The earlier AppKit wizard has been
removed. Game text, font pixels, frames, attribute layout and screen transitions
come from the original local binaries. Application menus are English.

Return/Space at the completed title enters the original GEN menu. Choose A to
generate a character. Follow its original English instructions: arrows allocate
attributes, Space advances after all points are spent, A–D choose race/class,
A–B choose sex, Return finishes the name, and Y confirms saving. Escape returns
to GEN's menu during allocation. No native form or translated in-game text is
inserted between these screens.

## Execution and translation

Ghidra's PseudoDisassembler exports candidates at every byte in MI.U1, STUPH and
GEN, including possible overlapping instruction entries. These are speculative
candidates, **not a claim that data bytes are code**. The generator checks their
bytes against each original file. Only runtime-reached PCs execute. Identical
address-parametric bodies share a Swift switch arm; each retains an explicit PC
and opcode guard. Unknown execution stops with an error.

The native application executes the original font renderer, inline text reader,
self-modifying page writes, allocation rules, race/class arithmetic, name input,
confirmation, and the STUPH random-byte routine. Packed-decimal ADC/SBC now
support the original decimal number formatting. The interactive event loop runs
the original keyboard latch, buffering, cursor and blocking polling routines.
AppKit supplies the window and physical keys; CoreGraphics displays the original
HGR memory in a 4:3 viewport with nearest-neighbor scaling.

Host boundaries are resource loading (`$B70C/$B703`), monitor HOME (`$FC58`, text
page clear) and local saving (`$B724`). Disk timing and slot hardware are not
emulated. Sound accesses are counted but audio output is not yet connected.
Execution pacing uses instruction budgets and is not cycle-accurate.

## Saving and current boundary

GEN's original Y path supplies its own 458-byte record and save parameters.
The host writes `~/Library/Application Support/UltimaI/Characters/U1.VARS`, then
returns to GEN's original menu. As with the original single player record, a
later confirmed save replaces this file. Earlier prototype UUID-directory
records remain untouched. Continue-game/outdoor entry is not implemented yet;
this change covers original character creation and saving.

## Verification

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_character.py
python3 tools/verify_native_startup.py
open "build/Ultima I.app"
```

A headless original-input replay captures menu, allocation, race, sex, class,
name, confirmation and the post-save menu, without loading reference RAM into
the application. Six independently recorded original checkpoints match both
8192-byte HGR pages exactly: **98,304 video bytes**. An independent raster model
also matches **645,120 output pixels**. The matching checkpoints are GEN menu,
initial attributes, race, sex, class and initial name entry. Confirmation and
post-save screenshots are captured but are not part of that six-screen pixel
comparison.

The Human/Male/Fighter `A` record matches 456 original save bytes. The other two
bytes at `$7EEF–$7EF0` come from the now-executed original random routine; their
values depend on input timing and state. Reference captures stop at `$15BF`
before input so they align with existing original snapshots. A separate check
disables those stops and runs the real polling loop, accepting A then Right.
40,000 valid packed-decimal ADC/SBC cases verify numeric results and carry.

Generated Swift, candidate listings, raw assets, RAM captures, pixel files,
original record data and the built application remain private under `build/`.
GUI window interaction still requires a normal macOS user session; headless
execution validates the code, rendering and input paths without WindowServer.
