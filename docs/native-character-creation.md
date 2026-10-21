# Native character creation

The title now connects to an AppKit character creation wizard. Return/Space on
the title, or the person button in the toolbar, opens it. Creation follows GEN:
attribute allocation → race → sex → class → name → confirmation → save.

## Translation boundary

Ghidra analyzes GEN in the private Startup project. `transcribe_character.py`
checks the exported bytes against the local GEN file, requires complete
instruction coverage of `$8CFA–$8D3B` and `$8E12–$8E53`, and generates 60
address-preserving Swift instructions. `CharacterSession` executes those original
race/class bonus blocks, stopping at `$8D3C` and `$8E54`. Redrawing a page rebuilds
from the allocation, so bonuses cannot accumulate.

The native host replaces GEN's text drawing, keyboard polling and ProDOS save
calls. It implements the reviewed attribute input rules (`$8C00–$8C80`), name
rules (`$8E83–$8EEB`), and wizard transitions explicitly. It does not execute the
whole GEN overlay or the MI.U1/STUPH initialization path. This distinction is
intentional and should remain visible when extending the port.

Attributes begin at 10, with 30 points to spend and a pre-bonus cap of 25.
Their original order is Strength, Agility, Stamina, Charisma, Wisdom,
Intelligence, corroborated by the MI.U1 text table. Race IDs are 1–4, sex 0–1,
and class IDs 1–4. The name occupies at most 13 ASCII bytes, begins with a letter,
and follows the original capitalization rule.

## Persistence and scope

The host copies GEN's 136-byte initial template from `$904F` to `$7E6F`, overlays
identity and allocated attributes, and writes a 458-byte `U1.VARS` record with
its `$01CA` header. Each creation gets a new directory under
`~/Library/Application Support/UltimaI/Characters/<UUID>/`, avoiding accidental
replacement of an earlier character. These are locally generated records.

The Human/Male/Fighter replay matches 456 of 458 original saved bytes. The two
remaining bytes, `$7EEF–$7EF0`, are initialized by GEN `$8E57/$8E5D` through
random-byte service `$15B9`; this host uses two system-random bytes instead.
The original random algorithm and engine initialization still need integration
before enabling outdoor entry or save import. The saved page explicitly
marks Sosaria entry as the next implementation stage. No continue-game button is
presented yet.

## Verification

```sh
python3 tools/build_macos_app.py
"build/Ultima I.app/Contents/MacOS/UltimaI" --check-character build/macos-startup/character-checks
python3 tools/verify_native_startup.py
```

The headless character checks exercise allocation limits, pool exhaustion, all
16 race/class combinations through generated instructions, repeat rendering,
name normalization, and record identity offsets. Original runtime snapshots
remain available for cross-checking the Human/Male/Fighter path. GUI interaction
should also be checked in a normal macOS session; the tool execution environment
cannot register an AppKit application with WindowServer.
