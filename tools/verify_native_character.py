#!/usr/bin/env python3
"""Compare original-rendered native GEN screens and saved record to Apple II replays."""
import json
import subprocess
from disassemble import ROOT
from baseline import describe
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.exists():
        print('PENDING native GEN app'); return
    output = ROOT / 'build/macos-startup/gen-original'
    subprocess.run([str(executable), '--capture-gen', str(output)], check=True)
    references = [('menu','gen-menu'), ('attributes','gen-first-input'),
                  ('race','gen-attribute-completion'), ('sex','gen-race-a'),
                  ('class','gen-sex-a'), ('name','gen-class-a')]
    matching = pixels = 0
    for name,trace in references:
        report_file = ROOT / f'build/traces/{trace}/handoff.json'
        if not report_file.exists():
            print(f'PENDING original {trace} replay'); continue
        report = json.loads(report_file.read_text())
        item = report['snapshot']; path = ROOT / item['path']
        assert describe(path) == {k:item[k] for k in ('size','sha256')}, 'Original snapshot changed'
        original = main_ram(path)
        native = (output / f'{name}.ram').read_bytes()
        for page in (0x2000,0x4000):
            assert native[page:page+8192] == original[page:page+8192], f'{name}: original HGR bytes differ on {page:04X}'
            matching += 8192
        rgba = (output / f'{name}.rgba').read_bytes()
        normalized = bytearray(0x6000)
        normalized[0x4000:0x6000] = original[0x2000:0x4000]
        for y in range(192):
            for col in range(40):
                for bit,color in enumerate(expected_column(normalized,y,col)):
                    offset = (y*560+col*14+bit)*4
                    assert rgba[offset:offset+4] == color.to_bytes(3,'big')+b'\xff', f'{name}: raster differs'
                    pixels += 1
    report_file = ROOT / 'build/traces/gen-player-save/handoff.json'
    if report_file.exists():
        item = json.loads(report_file.read_text())['snapshot']; path = ROOT / item['path']
        assert describe(path) == {k:item[k] for k in ('size','sha256')}
        original = main_ram(path)[0x7E6D:0x8037]
        native = (output / 'U1.VARS').read_bytes()
        assert len(native) == len(original) == 458
        excluded = {0x7EEF-0x7E6D,0x7EF0-0x7E6D}
        assert all(a==b for i,(a,b) in enumerate(zip(native,original)) if i not in excluded), 'GEN save differs beyond random state'
    print(f'Native original GEN: {matching} HGR bytes and {pixels} pixels match; creation/save completed')


if __name__ == '__main__':
    main()
