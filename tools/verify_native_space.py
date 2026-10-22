#!/usr/bin/env python3
"""Check original SPA boarding, rendering, direction costs, view/fire and landing."""
import json
import subprocess
from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native space app'); return
    output = ROOT / 'build/macos-startup/space'
    subprocess.run([str(executable),'--capture-space',str(output)],check=True)
    initial = (output / 'space-first-input.ram').read_bytes()
    point = json.loads((output / 'space-first-input.json').read_text())
    assert point['overlay'] == 'SPA' and point['pc'] == 0x8A5F
    def fuel(ram): return int.from_bytes(ram[0x7EE9:0x7EEB],'little')
    assert fuel(initial) == 1000 and initial[0x7E7C] == 6
    ref = ROOT / 'build/traces/out-board-transitions/probe.json'
    pixels = video = 0
    if ref.is_file():
        item = json.loads(ref.read_text())['spa']['snapshot']; path = ROOT / item['path']
        assert describe(path) == {k:item[k] for k in ('size','sha256')}
        original = main_ram(path)
        for base in (0x2000,0x4000):
            assert initial[base:base+8192] == original[base:base+8192], 'SPA entry HGR differs'
            video += 8192
        normalized = bytearray(0x6000)
        normalized[0x4000:0x6000] = original[point['page']:point['page']+8192]
        rgba = (output / 'space-first-input.rgba').read_bytes()
        for y in range(192):
            for column in range(40):
                for bit,color in enumerate(expected_column(normalized,y,column)):
                    offset = (y*560+column*14+bit)*4
                    assert rgba[offset:offset+4] == color.to_bytes(3,'big')+b'\xff'
                    pixels += 1
    else:
        print('PENDING original controlled SPA reference')
    report = ROOT / 'build/traces/spa-direction-controls/handoff.json'
    for name,key,xy,heading,cost in [('up',11,[254,0],3,5),('down',10,[2,0],3,5),
                                     ('right',21,[0,0],0,2),('left',8,[0,0],2,2)]:
        ram = (output / f'space-direction-{key:02x}.ram').read_bytes()
        assert ram[0x928A:0x928C] == bytes(xy) and ram[0x923F] == heading
        assert fuel(ram) == 1000-cost and ram[0x7EEB:0x7EED] == initial[0x7EEB:0x7EED]
        if report.is_file():
            expected = json.loads(report.read_text())['runs'][name]['next_input']
            assert all(ram[int(address[1:],16)] == value for address,value in expected.items())
    view = (output / 'space-view.ram').read_bytes()
    fire = (output / 'space-fire.ram').read_bytes()
    assert fuel(view) == 995 and fuel(fire) == 985
    assert json.loads((output / 'space-view-exit.json').read_text())['pc'] == 0x8A5F
    live = (output / 'space-live.ram').read_bytes()
    assert live[0x923F] == 0 and fuel(live) == 998
    landed = json.loads((output / 'space-landed.json').read_text())
    assert landed['overlay'] == 'OUT' and landed['pc'] == 0x8A6C
    print(f'Native SPA: {video} original HGR bytes and {pixels} pixels match; boarding, directions/fuel, view/fire and controlled landing verified')


if __name__ == '__main__':
    main()
