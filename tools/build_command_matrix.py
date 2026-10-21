#!/usr/bin/env python3
"""Map the shared 26-key decoder to six overlay handler pointer tables."""

import argparse
from pathlib import Path
import sys

from disassemble import FILES, ROOT


OUTPUT = ROOT / "docs/command-dispatch-matrix.md"
KEY_ADDRESS = 0x7E53
KEYS = bytes.fromhex("0b 0a 15 08 20 01 41 42 43 44 45 46 47 48 49 4b 4e 4f 51 52 53 54 55 56 58 5a")
TABLES = {
    "OUT": (0x9AAA, 0x89D0),
    "CAS": (0x8A5F, 0x8A4A),
    "TWN": (0x8A56, 0x8A41),
    "DNG": (0x8E14, 0x8DFF),
    "SPA": (0x91D3, 0x8AA4),
    "TM": (0x8EA8, 0x8E93),
}
KEY_NAMES = {0x0B: "Up", 0x0A: "Down", 0x15: "Right",
             0x08: "Left", 0x20: "Space", 0x01: "Ctrl-A"}


def render():
    engine = (ROOT / "extracted/MI.U1").read_bytes()
    start = KEY_ADDRESS - FILES["MI.U1"][0]
    if engine[start:start + len(KEYS)] != KEYS:
        raise ValueError("shared command table differs from reviewed decoder")
    targets = {}
    summary = []
    for module, (address, lookup) in TABLES.items():
        base, size, _ = FILES[module]
        data = (ROOT / "extracted" / module).read_bytes()
        if len(data) != size:
            raise ValueError(f"{module}: extracted size differs")
        offset = address - base
        if offset < 0 or offset + 52 > size:
            raise ValueError(f"{module}: pointer table outside file")
        lookup_offset = lookup - base
        if data[lookup_offset:lookup_offset + 3] != bytes((0xBD, address & 0xFF, address >> 8)):
            raise ValueError(f"{module}: command dispatch does not read expected table")
        values = [int.from_bytes(data[offset + 2*i:offset + 2*i + 2], "little")
                  for i in range(26)]
        for target in values:
            if not (0x7000 <= target < 0x8956 or base <= target < base + size):
                raise ValueError(f"{module}: handler ${target:04X} is not resident")
        targets[module] = values
        shared = sum(target < 0x8956 for target in values)
        summary.append((module, lookup, address, len(set(values)), shared))
    lines = [
        "# 공용 키와 여섯 게임 모듈의 핸들러 주소표", "",
        "`MI.U1 $7E53–$7E6C`에는 26개 키 코드가 있다. 공용 해석기 `$82A2`는 일치한 키의 인덱스를 두 배로 만들어 현재 오버레이의 16비트 주소표를 고른다. 아래 표는 **정적 주소 관계**다. 핸들러가 실제로 실행되는 조건과 효과는 각 모듈의 실행 기록으로 따로 검증해야 한다.", "",
        "여섯 파일은 모두 `$8956`에 서로 배타적으로 로드된다. 셀의 `M:$xxxx`는 상주 공용 엔진 `MI.U1 $7000–$8955`를, `$xxxx`는 해당 열의 오버레이 내부를 가리킨다. 같은 숫자 주소라도 열이 다르면 다른 코드다.", "",
        "| 모듈 | 공용 해석 뒤 표 조회 | 주소표 시작 | 중복 제외 대상 수 | 공용 엔진 대상 항목 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for module, lookup, address, unique, shared in summary:
        lines.append(f"| `{module}` | `${lookup:04X}` | `${address:04X}` | {unique} | {shared}/26 |")
    lines += ["", "| 순서 | 키 | OUT | CAS | TWN | DNG | SPA | TM |",
              "| ---: | --- | --- | --- | --- | --- | --- | --- |"]
    for i, key in enumerate(KEYS):
        name = KEY_NAMES.get(key, chr(key))
        cells = []
        for module in TABLES:
            target = targets[module][i]
            cells.append(f"`{'M:' if target < 0x8956 else ''}${target:04X}`")
        lines.append(f"| {i} | `{name}` (`${key:02X}`) | " + " | ".join(cells) + " |")
    lines += [
        "", "표의 26개 항목이 모두 공용 엔진 또는 현재 오버레이의 로드 범위에 들어가는지 [생성기](../tools/build_command_matrix.py)가 확인한다. `OUT` Space의 `$8A76`, `OUT` 방향 네 항목, `CAS`/`TWN`/`DNG` 첫 이동, `SPA`/`TM` 첫 Space는 별도 실행 추적으로 도달한 예다. [한 턴 비교](turn-contracts.md)와 [Ghidra 호출 지도](ghidra-call-atlas.md)를 함께 읽는다.",
        "", "이 표는 Ghidra가 자동으로 복구하지 못한 **간접 디스패치 간선**을 명시한다. 주소표 자체는 원본 파일의 데이터이며, 이 52바이트를 명령으로 해석하면 호출 그래프가 왜곡된다. 공용 코드와 오버레이 핸들러의 연결을 포팅할 때는 키 인덱스, 간접 대상, 상태 전이, 표시 효과를 별도로 모델링한다.", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != result:
            print("command matrix is stale; run python3 tools/build_command_matrix.py", file=sys.stderr)
            return 1
        print("six overlay command tables and public matrix match local extraction")
        return 0
    OUTPUT.write_text(result)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
