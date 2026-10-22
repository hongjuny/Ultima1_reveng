# Ultima I — native macOS startup

From the repository root on macOS:

```sh
python3 tools/build_macos_app.py
open "build/Ultima I.app"
```

The first build uses the installed Ghidra and Swift compiler. Keep the locally
extracted `U1.INTRO`, `MAKE.INDATA`, `MI.U1`, `STUPH`, `GEN`, `OUT`, `TWN`, `CAS`, `DNG`, `SPA`, `TCMAPS`, and `MAPCHARS` in `extracted/`. Use `--ghidra` to refresh
the startup analysis. The generated Swift, application bundle, original assets,
and captured frames stay under ignored `build/`.

The native app presents the Origin splash, runs the original intro animation,
and holds a complete Ultima I title frame. The toolbar and Playback menu provide
pause, skip to title, replay (Command-R), and fullscreen (Command-F).
Press Return/Space on the title or use the person toolbar button to create a
character through GEN's original Apple II menu. The original English screens,
font renderer, cursor and keyboard routines cover allocation, race, sex, class,
name, confirmation and local saving. Choose B in GEN to load the saved character
and enter Sosaria. Arrow keys move, Space passes, and Q saves. Press E on a town
tile to enter its original TWN screen, or on a castle tile to enter CAS.
Dungeon tiles now enter DNG's original first-person view; use K at the entrance
ladder to return outdoors. Saving with Q is allowed outdoors, as in the original.
SPA is connected: B boards an acquired shuttle, V opens its separate flight
view, and F fires there. See [space integration and test fixtures](../docs/native-space.md).
See [dungeon entry and saves](../docs/native-dungeon.md).
Walk out through a town/castle map exit to return outdoors. See
[castle entry](../docs/native-castle.md) for verified controls and scope.
See [town entry and a verified route](../docs/native-town.md),
[Sosaria entry](../docs/native-sosaria.md) for validation and current scope, and
[character creation](../docs/native-character-creation.md) for translation boundaries
and save-format limitations.

The address-preserving Swift blocks come from Ghidra's instruction export,
including the support code relocated to `$8700`. The native host supplies file
loading, an event loop, and HGR-to-CoreGraphics rendering. Every translated PC
retains its original identity and an unknown instruction stops with an explicit
error. The underlying data is decoded and the scene is constructed at runtime.

Reproduce the original title checkpoint and compare the native application:

```sh
python3 tools/run_runtime.py --no-check trace_startup_title_reference.py
python3 tools/verify_native_startup.py
python3 tools/verify_native_character.py
python3 tools/verify_native_sosaria.py
python3 tools/verify_native_town.py
python3 tools/verify_native_castle.py
python3 tools/verify_native_dungeon.py
python3 tools/verify_native_space.py
```

The reference capture uses the established private emulator snapshots. Only its
nested delay routine is replaced by its equivalent register/flag exit state;
screen construction and animation state remain original. The application loads
its original files directly and does not consume reference snapshots.
See [the startup translation report](../docs/native-startup.md) for addresses,
validation results, and remaining boundaries.
