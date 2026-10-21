#!/usr/bin/env python3
"""Generate private address-preserving Swift blocks from Ghidra startup TSVs."""
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

from disassemble import ROOT

BUILD = ROOT / "build/macos-startup"
SOURCES = (("U1.INTRO", 0x0800, ROOT / "extracted/U1.INTRO"),
           ("MAKE.INDATA", 0x1E00, ROOT / "extracted/MAKE.INDATA"),
           ("INTRO.RELOC", 0x8700, BUILD / "INTRO.RELOC"))


def operand(row):
    raw = bytes.fromhex(row["bytes"])
    text = row["operands"].lower()
    if text.startswith("#"): return None, "byteOperand()"
    if text == "a": return "a", "a"
    if text.startswith("(") and text.endswith(",x)"):
        address = "zpWord(byteOperand() &+ x)"
    elif text.startswith("(") and text.endswith("),y"):
        address = "(zpWord(byteOperand()) + Int(y)) & 0xFFFF"
    elif text.endswith(",x"):
        address = ("Int(byteOperand() &+ x)" if len(raw) == 2 else
                   "(wordOperand() + Int(x)) & 0xFFFF")
    elif text.endswith(",y"):
        address = ("Int(byteOperand() &+ y)" if len(raw) == 2 else
                   "(wordOperand() + Int(y)) & 0xFFFF")
    else:
        address = "Int(byteOperand())" if len(raw) == 2 else "wordOperand()"
    return address, f"read({address})"


def translate(row):
    pc = int(row["address"], 16)
    raw = bytes.fromhex(row["bytes"])
    name = row["mnemonic"].upper()
    address, value = operand(row)
    next_pc = pc + len(raw)
    tail = f"; pc = 0x{next_pc:04X}"
    if name in ("LDA", "LDX", "LDY"):
        body = f"{name[-1].lower()} = nz({value})" + tail
    elif name in ("STA", "STX", "STY"):
        body = f"write({address}, {name[-1].lower()})" + tail
    elif name in ("AND", "ORA", "EOR"):
        op = {"AND": "&", "ORA": "|", "EOR": "^"}[name]
        body = f"a = nz(a {op} {value})" + tail
    elif name in ("ADC", "SBC"):
        body = f"{name.lower()}({value})" + tail
    elif name in ("CMP", "CPX", "CPY"):
        register = {"CMP": "a", "CPX": "x", "CPY": "y"}[name]
        body = f"compare({register}, {value})" + tail
    elif name == "BIT": body = f"bit({value})" + tail
    elif name in ("INC", "DEC"):
        op = "&+" if name == "INC" else "&-"
        body = f"write({address}, nz({value} {op} 1))" + tail
    elif name in ("INX", "INY", "DEX", "DEY"):
        register = name[-1].lower(); op = "&+" if name.startswith("IN") else "&-"
        body = f"{register} = nz({register} {op} 1)" + tail
    elif name in ("TAX", "TAY", "TXA", "TYA", "TSX", "TXS"):
        source, target = {"TAX": ("a", "x"), "TAY": ("a", "y"),
                          "TXA": ("x", "a"), "TYA": ("y", "a"),
                          "TSX": ("sp", "x"), "TXS": ("x", "sp")}[name]
        body = f"{target} = " + (source if name == "TXS" else f"nz({source})") + tail
    elif name in ("ASL", "LSR", "ROL", "ROR"):
        kind = ("ASL", "LSR", "ROL", "ROR").index(name)
        shifted = f"shift({value}, kind: {kind})"
        body = (f"a = {shifted}" if address == "a" else f"write({address}, {shifted})") + tail
    elif name in ("CLC", "SEC", "CLI", "SEI", "CLD", "SED", "CLV"):
        mask = {"CLC": 1, "SEC": 1, "CLI": 4, "SEI": 4, "CLD": 8, "SED": 8, "CLV": 64}[name]
        body = f"setFlag({mask}, {'true' if name.startswith('SE') else 'false'})" + tail
    elif name in ("BNE", "BEQ", "BCC", "BCS", "BMI", "BPL", "BVC", "BVS"):
        condition = {"BNE": "!flag(2)", "BEQ": "flag(2)", "BCC": "!flag(1)",
                     "BCS": "flag(1)", "BMI": "flag(0x80)", "BPL": "!flag(0x80)",
                     "BVC": "!flag(0x40)", "BVS": "flag(0x40)"}[name]
        body = f"branch({condition})"
    elif name == "JSR": body = "jsr()"
    elif name == "JMP":
        if row["operands"].startswith("("):
            body = "let target = wordOperand(); pc = Int(read(target)) | Int(read((target & 0xFF00) | ((target + 1) & 255))) << 8"
        else: body = "pc = wordOperand()"
    elif name == "RTS": body = "rts()"
    elif name == "PHA": body = "push(a)" + tail
    elif name == "PLA": body = "a = nz(pop())" + tail
    elif name == "PHP": body = "push(p | 0x30)" + tail
    elif name == "PLP": body = "p = pop() | 0x20" + tail
    elif name == "NOP": body = f"pc = 0x{next_pc:04X}"
    else: body = f'throw StartupFailure.unsupported("{name} at ${pc:04X}")'
    lines = [f"        case 0x{pc:04X}: // {row['program']} {name} {row['operands']}"]
    # $0Fxx switches this JSR to RTS; operands elsewhere also change at runtime.
    if pc == 0x0A5E:
        lines.append("            if memory[pc] == 0x60 { rts(); return }")
    lines.append(f"            guard memory[pc] == 0x{raw[0]:02X} else {{ throw StartupFailure.modifiedInstruction(pc, 0x{raw[0]:02X}, memory[pc]) }}")
    lines.append("            " + body)
    return lines


def main():
    pages = defaultdict(list); seen = set(); counts = {}; inputs = {}
    for name, base, source in SOURCES:
        data = source.read_bytes(); inputs[name] = hashlib.sha256(data).hexdigest()
        rows = list(csv.DictReader((BUILD / f"{name}-instructions.tsv").open(), delimiter="\t"))
        if name == "U1.INTRO":
            alternate = BUILD / "U1.INTRO-alternates.tsv"
            if alternate.is_file():
                rows += list(csv.DictReader(alternate.open(), delimiter="\t"))
        counts[name] = 0
        for row in rows:
            pc = int(row["address"], 16); raw = bytes.fromhex(row["bytes"])
            # Support's original $2000 payload relocates before execution.
            if name == "MAKE.INDATA" and pc >= 0x2000: continue
            if data[pc-base:pc-base+len(raw)] != raw:
                raise ValueError(f"{name}: Ghidra bytes differ at ${pc:04X}")
            if pc in seen: raise ValueError(f"overlapping startup PC ${pc:04X}")
            seen.add(pc); pages[pc >> 8].append(row); counts[name] += 1
    lines = ["// Generated locally from Ghidra; contains original program details. Do not publish.",
             "extension StartupMachine {", "    func translatedStep() throws {", "        switch pc >> 8 {"]
    for page in sorted(pages): lines.append(f"        case 0x{page:02X}: try stepPage{page:02X}()")
    lines += ["        default: throw StartupFailure.untranslated(pc)", "        }", "    }"]
    for page, rows in sorted(pages.items()):
        lines += [f"    private func stepPage{page:02X}() throws {{", "        switch pc {"]
        for row in sorted(rows, key=lambda r: int(r["address"], 16)): lines += translate(row)
        lines += ["        default: throw StartupFailure.untranslated(pc)", "        }", "    }"]
    lines += ["}", ""]
    (BUILD / "StartupTranslated.swift").write_text("\n".join(lines))
    (BUILD / "translation-manifest.json").write_text(json.dumps(
        {"source_sha256": inputs, "candidate_instructions": counts,
         "total_candidate_instructions": len(seen)}, indent=2) + "\n")
    print(f"Ghidra → Swift: {len(seen)} startup instruction candidates")


if __name__ == "__main__":
    main()
