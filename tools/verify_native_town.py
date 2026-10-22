#!/usr/bin/env python3
"""Verify the original-rendered native town entry, movement, and OUT return."""
import json
import subprocess
from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native town app'); return
    output = ROOT / 'build/macos-startup/town'
    subprocess.run([str(executable),'--capture-town',str(output)],check=True)
    count = pixels = 0
    for name,trace in [('town-tile','out-route-to-06/step-13'),('town-first-input','twn-first-input')]:
        report = ROOT / f'build/traces/{trace}/handoff.json'
        if not report.exists():
            print(f'PENDING original {trace} reference'); continue
        item = json.loads(report.read_text())['snapshot']; path = ROOT / item['path']
        assert describe(path) == {k:item[k] for k in ('size','sha256')}
        original = main_ram(path)
        native = (output / f'{name}.ram').read_bytes()
        point = json.loads((output / f'{name}.json').read_text())
        assert native[:2] == original[:2]
        assert native[0xB400:0xB700] == original[0xB400:0xB700], 'Town map/actor record differs'
        for base in (0x2000,0x4000):
            assert native[base:base+8192] == original[base:base+8192], f'{name}: HGR page differs'
            count += 8192
        normalized = bytearray(0x6000)
        normalized[0x4000:0x6000] = original[point['page']:point['page']+8192]
        rgba = (output / f'{name}.rgba').read_bytes()
        for y in range(192):
            for column in range(40):
                for bit,color in enumerate(expected_column(normalized,y,column)):
                    offset = (y*560+column*14+bit)*4
                    assert rgba[offset:offset+4] == color.to_bytes(3,'big')+b'\xff'
                    pixels += 1
    entered = (output / 'town-first-input.ram').read_bytes()
    assert entered[0:2] == bytes([19,17])
    assert entered[0xB000:0xB400] == (ROOT / 'extracted/MAPCHARS').read_bytes()
    maps = (ROOT / 'extracted/TCMAPS').read_bytes()
    start = int.from_bytes(maps[4:6],'little')-0x4000
    assert entered[0xB400:0xB700] == maps[start:start+768]
    for name in ('town-up','town-live'):
        ram = (output / f'{name}.ram').read_bytes()
        assert ram[0:2] == bytes([19,16]), f'{name}: movement failed'
    # NPC updates are timing/random-state dependent after the first input; no
    # claim of exact full-frame matching is made for those later frames.
    exited = (output / 'town-exit.ram').read_bytes()
    point = json.loads((output / 'town-exit.json').read_text())
    assert point['overlay'] == 'OUT' and point['pc'] == 0x8A6C
    assert exited[:2] == exited[0x7E73:0x7E75] == bytes([29,32])
    assert exited[0x6000:0x7000] == (output / 'town-tile.ram').read_bytes()[0x6000:0x7000]
    print(f'Native town: {count} original HGR bytes and {pixels} pixels match entry route; original movement and OUT return verified')


if __name__ == '__main__':
    main()
