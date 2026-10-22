# Original Apple II speaker on macOS

The native app now sends the original `$C030` speaker latch transitions to
AVAudioEngine/AVAudioPlayerNode as mono 48 kHz floating-point PCM. Reads and
writes both toggle the latch. No replacement effect library or music is added.
The original STUPH dispatcher, queues and SPA code still choose and execute sounds.

## Timing and rendering

An independent 1.023 MHz audio clock counts NMOS 6502 base instruction cycles,
taken branches, branch page crossings and indexed-read page penalties. Each
speaker access records the current audio clock. Sampling integrates the one-bit
level across each sample interval, including multiple transitions; a DC blocker
lets a constant latched level decay to silence. Output amplitude is bounded.

The existing game instruction budgets and 60 Hz display timer are unchanged.
This preserves the current fast gameplay. Sound uses CPU time rather than the
number of display frames, so pitch is not tied to the faster game tempo.

This is not complete bus-cycle emulation: accesses are timestamped at instruction
completion, dummy bus accesses are not modeled, host file service time is omitted,
and collapsed intro waits do not contribute cycles. When fast execution produces
more than 250 ms of queued audio, pending playback is cleared to prevent long
input-to-sound delay. Silent leading/trailing samples are omitted from scheduled
buffers. These policies favor responsive play; they do not guarantee a globally
cycle-synchronized audiovisual recording.

## Controls and lifecycle

**Game → Mute Sound** (`Command-M`) toggles host output. Original sound logic
continues while muted. Pause, restart, test-session changes, return to the normal
game and error dialogs clear queued audio. Skip to Title discards skipped audio.
Test-session construction is silent; playback starts with the interactive session.

## Verification

```sh
python3 tools/build_macos_app.py
python3 tools/verify_native_audio.py
python3 tools/check_all.py
```

The headless test executes original STUPH code, without an audio device:

- ID `$0E`: 16 transitions, exactly 6,441 cycles between transitions.
- ID `$10`: 50 transitions, exactly 1,666 cycles between transitions.
- These two timing results match prior independent original-emulator measurements
  documented in [shared services](shared-services.md).
- All nine IDs traverse the original stack dispatcher, produce finite nonzero PCM
  and return normally. These are controlled calls, not nine gameplay-event replays.
- Both read and write access paths reach the same speaker latch.

Private WAV files and JSON reports are written under
`build/macos-startup/audio/`. They are not published. Headless validation checks
code and PCM; actual speaker output and perceived volume need listening in the
normal macOS app session.

Apple API reference: [AVAudioPlayerNode](https://developer.apple.com/documentation/avfaudio/avaudioplayernode).
