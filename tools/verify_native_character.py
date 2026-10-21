#!/usr/bin/env python3
"""Check native GEN rules and compare its record with the original save replay."""
import json
from pathlib import Path
import subprocess
from disassemble import ROOT
from baseline import describe
from verify_intro_support import main_ram


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.exists():
        print('PENDING native character app'); return
    output = ROOT / 'build/macos-startup/character-checks'
    subprocess.run([str(executable), '--check-character', str(output)], check=True)
    report_path = ROOT / 'build/traces/gen-player-save/handoff.json'
    if not report_path.exists():
        print('PENDING original GEN save replay comparison'); return
    report = json.loads(report_path.read_text())
    snapshot = report['snapshot']
    path = Path(snapshot['path'])
    assert describe(path) == {k:snapshot[k] for k in ('size','sha256')}, 'Original snapshot changed'
    original = main_ram(path)[0x7E6D:0x8037]
    native = (output / 'U1.VARS').read_bytes()
    assert len(native) == len(original) == 458
    random_offsets = {0x7EEF-0x7E6D, 0x7EF0-0x7E6D}
    differences = [hex(0x7E6D+i) for i,(a,b) in enumerate(zip(native,original)) if a!=b and i not in random_offsets]
    assert not differences, f'Unexpected record differences: {differences}'
    print('Native GEN: 456 record bytes match original; 2 random-service bytes supplied by host')


if __name__ == '__main__':
    main()
