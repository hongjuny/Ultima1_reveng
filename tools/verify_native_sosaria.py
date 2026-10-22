#!/usr/bin/env python3
"""Verify native GEN→OUT, four movements, Q save, and fresh-process reload."""
import json
import subprocess
import tempfile
from pathlib import Path
from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram
from verify_outdoor_hgr_palette import expected_column


def main():
    executable = ROOT / 'build/Ultima I.app/Contents/MacOS/UltimaI'
    if not executable.is_file():
        print('PENDING native Sosaria application'); return
    # First-launch B must explain a missing local record, not ask for a disk.
    with tempfile.TemporaryDirectory(prefix='missing-player-', dir=ROOT / 'build') as missing:
        result = subprocess.run([str(executable), '--capture-resume', missing], capture_output=True, text=True)
        assert result.returncode == 1 and 'Saved game did not resume OUT' in result.stderr
        missing_ram = (Path(missing) / 'out-resumed.ram').read_bytes()
        prompt = missing_ram[0x8A36:0x8A54]
        assert prompt == b'No saved game. Create with A. ', 'Missing-record prompt still requests disk media'
        assert not (Path(missing) / 'U1.VARS').exists(), 'B fabricated a player record'
    print('Missing local save: original GEN renderer gives creation guidance, without a disk-swap prompt')
    output = ROOT / 'build/macos-startup/sosaria'
    subprocess.run([str(executable), '--capture-out', str(output)], check=True)
    references = [('out-first-input','out-first-input')]+[
        (f'out-direction-{key:02x}',f'out-direction-{key:02x}') for key in (11,10,21,8)]
    video = pixels = map_bytes = 0
    for name,trace in references:
        report_path = ROOT / f'build/traces/{trace}/handoff.json'
        if not report_path.exists():
            print(f'PENDING original {trace} replay'); continue
        item = json.loads(report_path.read_text())['snapshot']
        path = ROOT / item['path']
        assert describe(path) == {key:item[key] for key in ('size','sha256')}, 'Original snapshot changed'
        original = main_ram(path)
        native = (output / f'{name}.ram').read_bytes()
        point = json.loads((output / f'{name}.json').read_text())
        assert point['overlay'] == 'OUT' and point['pc'] == 0x8A6C
        assert native[:2] == original[:2], f'{name}: coordinates differ'
        assert native[0x6000:0x7000] == original[0x6000:0x7000], f'{name}: world map differs'
        map_bytes += 4096
        assert all(a==b for i,(a,b) in enumerate(zip(native[0x7E6D:0x8037],original[0x7E6D:0x8037]))
                   if i not in (0x7EEF-0x7E6D,0x7EF0-0x7E6D)), f'{name}: player record differs beyond random fields'
        for page in (0x2000,0x4000):
            assert native[page:page+8192] == original[page:page+8192], f'{name}: HGR differs at {page:04X}'
            video += 8192
        rgba = (output / f'{name}.rgba').read_bytes()
        normalized = bytearray(0x6000)
        normalized[0x4000:0x6000] = original[point['page']:point['page']+8192]
        assert len(rgba) == 560*192*4
        for y in range(192):
            for column in range(40):
                for bit,color in enumerate(expected_column(normalized,y,column)):
                    offset = (y*560+column*14+bit)*4
                    assert rgba[offset:offset+4] == color.to_bytes(3,'big')+b'\xff', f'{name}: pixel differs'
                    pixels += 1
    saved = (output / 'U1.VARS').read_bytes()
    at_save = (output / 'out-save.ram').read_bytes()
    assert len(saved) == 458 and saved == at_save[0x7E6D:0x8037], 'Q save differs from live record'
    subprocess.run([str(executable), '--capture-resume', str(output)], check=True)
    resumed = (output / 'out-resumed.ram').read_bytes()
    assert saved == resumed[0x7E6D:0x8037], 'Fresh-process loaded record differs'
    assert resumed[:2] == bytes([saved[0x7E73-0x7E6D],saved[0x7E74-0x7E6D]]), 'Saved position not restored'
    print(f'Native Sosaria: {video} HGR bytes, {pixels} pixels, {map_bytes} map bytes match original; Q save/restart verified')


if __name__ == '__main__':
    main()
