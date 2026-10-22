#!/usr/bin/env python3
"""Check native CAS entry, original rendering, walking, king service and OUT return."""
import json
import subprocess
from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native castle app'); return
    output = ROOT / 'build/macos-startup/castle'
    subprocess.run([str(executable),'--capture-castle',str(output)],check=True)
    video = pixels = 0
    for name,trace in [('castle-tile','out-route-to-04/step-11'),('castle-first-input','cas-first-input')]:
        report = ROOT / f'build/traces/{trace}/handoff.json'
        if not report.exists():
            print(f'PENDING original {trace} reference'); continue
        item = json.loads(report.read_text())['snapshot']; path = ROOT / item['path']
        assert describe(path) == {k:item[k] for k in ('size','sha256')}
        original = main_ram(path)
        native = (output / f'{name}.ram').read_bytes()
        point = json.loads((output / f'{name}.json').read_text())
        assert native[:2] == original[:2]
        assert native[0xB400:0xB700] == original[0xB400:0xB700]
        for base in (0x2000,0x4000):
            assert native[base:base+8192] == original[base:base+8192], f'{name}: HGR differs'
            video += 8192
        normalized = bytearray(0x6000)
        normalized[0x4000:0x6000] = original[point['page']:point['page']+8192]
        rgba = (output / f'{name}.rgba').read_bytes()
        for y in range(192):
            for column in range(40):
                for bit,color in enumerate(expected_column(normalized,y,column)):
                    offset = (y*560+column*14+bit)*4
                    assert rgba[offset:offset+4] == color.to_bytes(3,'big')+b'\xff'
                    pixels += 1
    entered = (output / 'castle-first-input.ram').read_bytes()
    assert entered[:2] == bytes([0,9])
    assert entered[0xB000:0xB400] == (ROOT / 'extracted/MAPCHARS').read_bytes()
    maps = (ROOT / 'extracted/TCMAPS').read_bytes()
    start = int.from_bytes(maps[:2],'little')-0x4000
    assert entered[0xB400:0xB700] == maps[start:start+768]
    assert (output / 'castle-right.ram').read_bytes()[:2] == bytes([1,9])
    king = (output / 'castle-king.ram').read_bytes()
    assert king[:2] == bytes([31,6]) and king[0xB400+6*38+31] == 0x6C
    service = (output / 'castle-service.ram').read_bytes()
    assert entered[0x7EAF] == 0 and service[0x7EAF] == 1
    exited = (output / 'castle-exit.ram').read_bytes()
    point = json.loads((output / 'castle-exit.json').read_text())
    assert point['overlay'] == 'OUT' and point['pc'] == 0x8A6C
    assert exited[:2] == exited[0x7E73:0x7E75] == bytes([30,31])
    assert exited[0x6000:0x7000] == (output / 'castle-tile.ram').read_bytes()[0x6000:0x7000]
    print(f'Native castle: {video} original HGR bytes and {pixels} pixels match entry route; movement, king service and OUT return verified')


if __name__ == '__main__':
    main()
