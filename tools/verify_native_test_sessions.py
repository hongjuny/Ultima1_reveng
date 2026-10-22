#!/usr/bin/env python3
"""Verify isolated playable SPA/TM test sessions and the original TM ending path."""
import json
import subprocess
from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram


def original(item):
    path = ROOT / item['path']
    assert describe(path) == {k:item[k] for k in ('size','sha256')}
    return main_ram(path)


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native test-session app'); return
    output = ROOT / 'build/macos-startup/test-sessions'
    subprocess.run([str(executable),'--capture-test-sessions',str(output)],check=True)
    for module in ('SPA','TM'):
        saved = (output / module / 'U1.VARS').read_bytes()
        assert len(saved) == 458 and saved[:2] == b'\xca\x01'
        assert saved[0x4B:0x51] == b'Tester', 'Test session did not use its own character'
    refs = []
    boarding = ROOT / 'build/traces/out-board-transitions/probe.json'
    if boarding.is_file():
        report = json.loads(boarding.read_text())
        refs += [('SPA-test.ram', report['spa']['snapshot']),('TM-test.ram',report['tm']['snapshot'])]
    main_report = ROOT / 'build/traces/tm-intro-pages/probe.json'
    if main_report.is_file(): refs += [('TM-main.ram',json.loads(main_report.read_text())['snapshot'])]
    video = 0
    for name,item in refs:
        expected = original(item)
        native = (output / name).read_bytes()
        for base in (0x2000,0x4000):
            assert native[base:base+8192] == expected[base:base+8192], f'{name}: original HGR differs'
            video += 8192
    main_ram_bytes = (output / 'TM-main.ram').read_bytes()
    right = (output / 'TM-right.ram').read_bytes()
    assert main_ram_bytes[:2] == bytes([4,5]) and right[:2] == bytes([5,5])
    ending = (output / 'TM-ending.ram').read_bytes()
    nif = (ROOT / 'extracted/NIF').read_bytes()
    assert len(nif) == 7680
    for y in range(192):
        address = 0x2000+(y&7)*0x400+((y>>3)&7)*0x80+(y>>6)*40
        assert ending[address:address+40] == nif[y*40:y*40+40], f'NIF ending row {y} differs'
    print(f'Isolated SPA/TM test sessions: {video} original HGR bytes match; TM input and 7680 NIF ending bytes verified; real save unchanged')


if __name__ == '__main__':
    main()
