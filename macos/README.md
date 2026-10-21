# Ultima I — native macOS startup

From the repository root on macOS:

```sh
python3 tools/build_macos_app.py
open "build/Ultima I.app"
```

The first build uses the installed Ghidra and Swift compiler. Keep the locally
extracted `U1.INTRO` and `MAKE.INDATA` in `extracted/`. Use `--ghidra` to refresh
the startup analysis. The generated Swift, application bundle, original assets,
and captured frames stay under ignored `build/`.

The native app presents the Origin splash, runs the original intro animation,
and holds a complete Ultima I title frame. The toolbar and Playback menu provide
pause, skip to title (Return), replay (Command-R), and fullscreen (Command-F).
This version implements the startup scene. Character creation and gameplay are
the next translation units.

The address-preserving Swift blocks come from Ghidra's instruction export,
including the support code relocated to `$8700`. The native host supplies file
loading, an event loop, and HGR-to-CoreGraphics rendering. Every translated PC
retains its original identity and an unknown instruction stops with an explicit
error. The underlying data is decoded and the scene is constructed at runtime.

Reproduce the original title checkpoint and compare the native application:

```sh
python3 tools/run_runtime.py --no-check trace_startup_title_reference.py
python3 tools/verify_native_startup.py
```

The reference capture uses the established private emulator snapshots. Only its
nested delay routine is replaced by its equivalent register/flag exit state;
screen construction and animation state remain original. The application loads
its two original files directly and does not consume reference snapshots.
See [the startup translation report](../docs/native-startup.md) for addresses,
validation results, and remaining boundaries.
