#!/usr/bin/env python3
"""Generate private GEN bonus blocks from byte-checked Ghidra instructions."""
import csv
from disassemble import ROOT
from transcribe_startup import translate

build = ROOT / 'build/macos-startup'
data = (ROOT / 'extracted/GEN').read_bytes()
rows = list(csv.DictReader((build / 'GEN-instructions.tsv').open(), delimiter='\t'))
selected = [r for r in rows if 0x8CFA <= int(r['address'],16) < 0x8D3C or 0x8E12 <= int(r['address'],16) < 0x8E54]
pcs = {int(r['address'],16) for r in selected}
for start,end in [(0x8CFA,0x8D3C),(0x8E12,0x8E54)]:
    cursor = start
    while cursor < end:
        row = next((r for r in selected if int(r['address'],16)==cursor), None)
        if row is None: raise ValueError(f'Missing Ghidra instruction at {cursor:04X}')
        raw = bytes.fromhex(row['bytes'])
        if data[cursor-0x8956:cursor-0x8956+len(raw)] != raw: raise ValueError('Ghidra byte mismatch')
        cursor += len(raw)
lines = ['// Private Ghidra translation. Generated locally; do not publish.', 'extension StartupMachine {', 'func characterBonusStep() throws {', 'switch pc {']
for row in selected: lines += translate(row)
lines += ['default: throw StartupFailure.untranslated(pc)', '}', '}', '}']
(build / 'CharacterTranslated.swift').write_text('\n'.join(lines)+'\n')
print(f'Ghidra → Swift: {len(selected)} GEN bonus instructions')
