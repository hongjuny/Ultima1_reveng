#!/usr/bin/env python3
"""Private Ghidra candidates for live MI.U1/STUPH/GEN execution, including overlaps.

Candidates are NOT code classification: only runtime-reached PCs execute.
Identical address-parametric instruction bodies share one Swift switch arm.
"""
import csv
from collections import defaultdict
from disassemble import ROOT
from transcribe_startup import translate

build = ROOT / 'build/macos-startup'
lines = ['// Generated locally from Ghidra. Do not publish.', 'extension StartupMachine {']
for name,base in [('MI.U1',0x7000),('STUPH',0x0800),('GEN',0x8956),('OUT',0x8956),('TWN',0x8956),('CAS',0x8956),('DNG',0x8956),('SPA',0x8956)]:
    raw = (ROOT / 'extracted' / name).read_bytes()
    groups = defaultdict(list)
    rows = csv.DictReader((build / f'{name}-runtime.tsv').open(), delimiter='\t')
    count = 0
    for row in rows:
        pc = int(row['address'],16)
        if name == 'STUPH' and pc < 0x1583: continue
        data = bytes.fromhex(row['bytes'])
        assert raw[pc-base:pc-base+len(data)] == data, f'{name} bytes at {pc:04X}'
        emitted = translate(row)
        body = emitted[-1].strip().replace(f'pc = 0x{pc+len(data):04X}',f'pc = (pc + {len(data)}) & 0xFFFF')
        # Unsupported candidate bytes remain explicit runtime failures.
        if body.startswith('throw ') or 'None' in body: continue
        groups[(data[0],body)].append(pc); count += 1
    method = name.replace('.','')
    lines += [f'func step{method}() throws {{', 'switch pc {']
    for (opcode,body),pcs in groups.items():
        lines += ['case '+', '.join(f'0x{pc:04X}' for pc in pcs)+':',
                  f'guard memory[pc] == 0x{opcode:02X} else {{ throw StartupFailure.modifiedInstruction(pc, 0x{opcode:02X}, memory[pc]) }}',body]
    lines += ['default: throw StartupFailure.untranslated(pc)', '}', '}']
    print(f'{name}: {count} speculative Ghidra candidates, {len(groups)} shared instruction bodies')
lines += ['}']
(build / 'GameFlowTranslated.swift').write_text('\n'.join(lines)+'\n')
