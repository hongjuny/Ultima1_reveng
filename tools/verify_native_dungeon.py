#!/usr/bin/env python3
"""Verify native DNG entry, perspective rendering, movement/facing and ladder exit."""
import json
import subprocess
from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native dungeon app'); return
    output = ROOT / 'build/macos-startup/dungeon'
    subprocess.run([str(executable),'--capture-dungeon',str(output)],check=True)
    video = pixels = 0
    refs = [('dungeon-tile','out-route-to-07/step-29'),('dungeon-first-input','dng-first-input'),
            ('dungeon-up','dng-after-up'),('dungeon-exit','dng-to-out')]
    for name,trace in refs:
        report = ROOT / f'build/traces/{trace}/handoff.json'
        if not report.exists():
            print(f'PENDING original {trace} reference'); continue
        item = json.loads(report.read_text())['snapshot']; path = ROOT / item['path']
        assert describe(path) == {k:item[k] for k in ('size','sha256')}
        original = main_ram(path)
        native = (output / f'{name}.ram').read_bytes()
        point = json.loads((output / f'{name}.json').read_text())
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
    entered = (output / 'dungeon-first-input.ram').read_bytes()
    assert entered[0xA4E8:0xA4EA] == bytes([1,1]) and entered[0xA506] == 1
    grid = entered[0xB099:0xB112]
    assert len(grid) == 121 and grid[12] == 8
    assert all(grid[y*11+x] == 1 for y in range(11) for x in range(11) if x in (0,10) or y in (0,10))
    for key,xy,facing in [(11,[1,2],[0,1]),(10,[1,1],[0,255]),(21,[1,1],[255,0]),(8,[1,1],[1,0])]:
        ram = (output / f'dungeon-direction-{key:02x}.ram').read_bytes()
        assert ram[0xA4E8:0xA4EA] == bytes(xy) and ram[0xA4EC:0xA4EE] == bytes(facing)
    assert (output / 'dungeon-live.ram').read_bytes()[0xA4E8:0xA4EA] == bytes([1,2])
    exited = (output / 'dungeon-exit.ram').read_bytes()
    point = json.loads((output / 'dungeon-exit.json').read_text())
    assert point['overlay'] == 'OUT' and point['pc'] == 0x8A6C
    assert exited[:2] == exited[0x7E73:0x7E75] == bytes([43,15])
    assert exited[0x6000:0x7000] == (output / 'dungeon-tile.ram').read_bytes()[0x6000:0x7000]
    print(f'Native dungeon: {video} original HGR bytes and {pixels} pixels match; four directions, live input and K exit verified')


if __name__ == '__main__':
    main()
