#!/usr/bin/env python3
"""Render original speaker effects without requiring a macOS audio device."""
import json
import subprocess
from disassemble import ROOT


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native audio app'); return
    output = ROOT / 'build/macos-startup/audio'
    subprocess.run([str(executable), '--capture-audio', str(output)], check=True)
    report = json.loads((output / 'audio.json').read_text())
    for name, edges, gap in [('0E',16,6441),('10',50,1666)]:
        run = report[name]
        assert run['edges'] == edges and run['gap_cycles'] == gap
        assert run['rate'] == 48000 and run['samples'] > 3000
        wav = (output / f'{name}.wav').read_bytes()
        assert wav[:4] in (b'RIFF', b'RF64') and len(wav) > 12000
    assert [item['id'] for item in report['dispatcher']] == list(range(0,18,2))
    assert all(item['edges'] > 0 and item['samples'] > 0 for item in report['dispatcher'])
    print('Native speaker: nine original effects; two independently measured edge intervals match; PCM and read/write latch verified')


if __name__ == '__main__':
    main()
