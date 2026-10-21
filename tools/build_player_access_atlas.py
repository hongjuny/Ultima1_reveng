#!/usr/bin/env python3
"""Summarize candidate direct player-record accesses in private Ghidra exports."""

import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path
import sys

from disassemble import ROOT


OUTPUT = ROOT / "docs/player-access-atlas.md"
EXPORTS = ROOT / "build/ghidra-project"
MODULES = ("MI.U1", "GEN", "OUT", "CAS", "TWN", "DNG", "SPA", "TM")
START, END = 0x7E6D, 0x8036
PREFIX_END = 0x7EF5
FIELDS = (
    (0x7E6D, 0x7E6E, "record header"),
    (0x7E73, 0x7E74, "outdoor return position"),
    (0x7E75, 0x7E78, "gems"),
    (0x7E7A, 0x7E7A, "attack damage input, partial"),
    (0x7E7B, 0x7E7B, "guard hit input, partial"),
    (0x7EA8, 0x7EA8, "craft creation gate, partial"),
    (0x7EA9, 0x7EB0, "quests"),
    (0x7EB5, 0x7EB5, "craft request"),
    (0x7EB7, 0x7EB7, "sex"),
    (0x7EB8, 0x7EC4, "name"),
    (0x7EC6, 0x7EC7, "HP"),
    (0x7EC8, 0x7ED3, "attributes"),
    (0x7ED4, 0x7ED5, "Coin"),
    (0x7ED6, 0x7ED6, "race"),
    (0x7ED8, 0x7ED8, "class"),
    (0x7EDA, 0x7EDA, "shared turn/accounting byte"),
    (0x7EE4, 0x7EE4, "shared turn/resource byte"),
    (0x7EE5, 0x7EE6, "Food"),
    (0x7EE7, 0x7EE8, "SPA third resource, unresolved"),
    (0x7EE9, 0x7EEA, "Fuel"),
    (0x7EEB, 0x7EEC, "Shield"),
    (0x7EF6, 0x7EF6, "object count"),
    (0x7EF7, 0x7F46, "object X array"),
    (0x7F47, 0x7F96, "object Y/world array"),
    (0x7F97, 0x7FE6, "object tile array"),
    (0x7FE7, 0x8036, "underlying tile array"),
)


def label(address):
    return next((name for low, high, name in FIELDS if low <= address <= high),
                "unclassified prefix")


def read_rows():
    rows = []
    for module in MODULES:
        path = EXPORTS / f"{module}-memory.tsv"
        with path.open(newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                if row["kind"] != "player":
                    continue
                if row["program"] != module:
                    raise ValueError(f"{module}: wrong export owner")
                address = int(row["to"], 16)
                if not START <= address <= END or row["access"] not in (
                        "read", "write", "readwrite"):
                    raise ValueError(f"{module}: invalid player reference")
                rows.append((module, address, int(row["from"], 16), row["access"]))
    return rows


def render():
    rows = read_rows()
    by_address = defaultdict(list)
    by_module = Counter()
    by_access = Counter()
    for module, address, instruction, access in rows:
        by_address[address].append((module, instruction, access))
        by_module[module] += 1
        by_access[access] += 1
    prefix = {address for address in by_address if address <= PREFIX_END}
    lines = [
        "# 플레이어 저장 레코드의 직접 접근 후보", "",
        "`U1.VARS`의 458바이트는 게임 중 `$7E6D–$8036`에 놓인다. 이 지도는 Ghidra가 **명령 후보**로 해석한 코드의 직접 메모리 읽기·쓰기 참조만 모은 것이다. 인덱스 주소 지정으로 뒷부분 배열을 순회하거나 간접 포인터로 접근하는 경우는 여기에 주소별로 나타나지 않는다. 후보 참조가 실제 실행된다는 뜻도 아니다. 확인된 의미와 저장 왕복은 [레코드 형식](../disasm/U1.VARS.md), [플레이어 상태](player-state.md)에서 따로 본다.", "",
        f"직접 참조 후보는 **{len(rows)}곳**, 서로 다른 레코드 주소는 **{len(by_address)}곳**이다. 137바이트 접두부 `$7E6D–$7EF5` 중 직접 참조된 주소는 **{len(prefix)}곳**이다. `{', '.join(MODULES)}`의 8개 게임 단계/공용 프로그램에서 추출했다.", "",
        "| 프로그램 | 직접 참조 후보 수 |", "| --- | ---: |",
    ]
    for module in MODULES:
        lines.append(f"| `{module}` | {by_module[module]} |")
    lines += ["", f"접근 종류: 읽기 {by_access['read']}, 쓰기 {by_access['write']}, 읽기·쓰기 {by_access['readwrite']}. 주소별 칸의 `R/W/RW`는 Ghidra 참조 유형이다. 괄호는 명령 주소이며 각 모듈·접근 종류에서 앞의 세 곳만 표시한다.", "",
              "| 레코드 주소 | 현재 필드 해석 | 직접 접근 후보 |",
              "| --- | --- | --- |"]
    for address in sorted(by_address):
        grouped = defaultdict(list)
        for module, instruction, access in by_address[address]:
            grouped[(module, access)].append(instruction)
        cells = []
        for module in MODULES:
            for access in ("read", "write", "readwrite"):
                sites = sorted(set(grouped[(module, access)]))
                if not sites:
                    continue
                head = ",".join(f"${site:04X}" for site in sites[:3])
                if len(sites) > 3:
                    head += f" +{len(sites)-3}"
                cells.append(f"`{module}` { {'read':'R','write':'W','readwrite':'RW'}[access] }({head})")
        lines.append(f"| `${address:04X}` | {label(address)} | {'; '.join(cells)} |")
    lines += ["", "이 장부는 **주소별 직접 참조의 탐색 인덱스**다. 특정 바이트에 행이 없다는 사실은 미사용을 증명하지 않는다. 다음 단계에서는 미분류 접두부의 실제 생산자·소비자, 인덱스 배열의 경계, 각 필드의 저장·재로드 효과를 명령별 실행 기록으로 교차 검증한다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != result:
            print("player access atlas is stale", file=sys.stderr)
            return 1
        print("player direct-access atlas matches private Ghidra exports")
        return 0
    OUTPUT.write_text(result)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
