#!/usr/bin/env python3
"""Partition imported game bytes by reviewed evidence and Ghidra candidates."""

import argparse
from collections import Counter
import csv
from pathlib import Path
import sys

from build_command_matrix import KEY_ADDRESS, KEYS, TABLES
from disassemble import FILES, ROOT
from verify_disasm import FRAGMENTS


OUTPUT = ROOT / "docs/code-data-ledger.md"
EXPORTS = ROOT / "build/ghidra-project"
MODULES = ("U1.SYSTEM", "U1.INTRO", "MAKE.INDATA", "MI.U1", "STUPH",
           "GEN", "OUT", "CAS", "TWN", "DNG", "SPA", "TM")

# These exact ranges are operands consumed after JSR, rather than 6502 instructions.
# Each is inside a fragment that verify_disasm.py reassembles byte-for-byte.
INLINE_DATA = {
    "U1.INTRO": ((0x0B5A, 0x0B60), (0x0F2B, 0x0F37)),
    "MI.U1": ((0x890A, 0x890E), (0x8926, 0x8928)),
    "GEN": ((0x8A18, 0x8A1C), (0x8F26, 0x8F2C)),
    "OUT": ((0x92DA, 0x92E0),),
    "SPA": ((0x8FEE, 0x8FF1), (0x8FF4, 0x8FFC),
            (0x9040, 0x9043), (0x9046, 0x904E),
            (0x906E, 0x9071), (0x9094, 0x9097)),
}


def contiguous(addresses):
    """Return half-open spans from sorted integer addresses."""
    result = []
    for address in sorted(addresses):
        if result and address == result[-1][1]:
            result[-1] = (result[-1][0], address + 1)
        else:
            result.append((address, address + 1))
    return result


def fmt_span(span):
    start, end = span
    return f"`${start:04X}–${end-1:04X}` ({end-start})"


def load_kinds(name, base, size):
    path = EXPORTS / f"{name}-memory.tsv"
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    kinds = [None] * size
    for row in rows:
        if row["kind"] != "span":
            continue
        start, end = int(row["from"], 16), int(row["to"], 16) + 1
        if not base <= start < end <= base + size:
            raise ValueError(f"{name}: Ghidra span outside imported file")
        for address in range(start, end):
            offset = address - base
            if kinds[offset] is not None:
                raise ValueError(f"{name}: overlapping Ghidra spans at ${address:04X}")
            kinds[offset] = row["operand"]
    if None in kinds:
        raise ValueError(f"{name}: Ghidra spans leave a hole")
    return kinds


def verified_sets(name, base, size):
    reviewed = {address for _, module, _, start, end in FRAGMENTS
                if module == name for address in range(start, end)}
    inline = {address for start, end in INLINE_DATA.get(name, ())
              for address in range(start, end)}
    if not inline <= reviewed:
        raise ValueError(f"{name}: inline data outside reviewed fragments")
    code = reviewed - inline
    data = set(inline)
    if name == "MI.U1":
        data.update(range(KEY_ADDRESS, KEY_ADDRESS + len(KEYS)))
    if name in TABLES:
        table, _ = TABLES[name]
        data.update(range(table, table + 2*len(KEYS)))
    if name == "STUPH":
        code.update(range(0x1583, 0x15E9))  # inspect_stuph_vectors.py
    if code & data:
        raise ValueError(f"{name}: verified code and data overlap")
    if not all(base <= address < base + size for address in code | data):
        raise ValueError(f"{name}: verified range outside extracted file")
    return code, data


def render():
    rows = []
    conflicts = []
    gaps = []
    totals = Counter()
    local_target_total = 0
    for name in MODULES:
        base, size, _ = FILES[name]
        kinds = load_kinds(name, base, size)
        code, data = verified_sets(name, base, size)
        if name in TABLES:
            table, _ = TABLES[name]
            source = (ROOT / "extracted" / name).read_bytes()
            offset = table - base
            local_targets = {int.from_bytes(source[offset + 2*i:offset + 2*i + 2], "little")
                             for i in range(len(KEYS))}
            local_targets = {address for address in local_targets
                             if base <= address < base + size}
            if any(kinds[address-base] != "instruction" for address in local_targets):
                raise ValueError(f"{name}: an indirect handler target was not decoded")
            local_target_total += len(local_targets)
        counts = Counter()
        code_missed = set()
        data_misread = set()
        unverified = set()
        for offset, kind in enumerate(kinds):
            address = base + offset
            if address in code:
                bucket = "verified_code"
                if kind != "instruction":
                    code_missed.add(address)
            elif address in data:
                bucket = "verified_data"
                if kind == "instruction":
                    data_misread.add(address)
                if kind != "defined_data":
                    raise ValueError(f"{name}: known data ${address:04X} was not typed in Ghidra")
            else:
                unverified.add(address)
                bucket = {"instruction": "candidate_code",
                          "defined_data": "candidate_data",
                          "undefined": "unclassified"}[kind]
            counts[bucket] += 1
        if sum(counts.values()) != size:
            raise ValueError(f"{name}: ledger does not partition file")
        totals.update(counts)
        rows.append((name, size, counts))
        conflicts.append((name, code_missed, data_misread))
        largest = sorted(contiguous(unverified), key=lambda pair: pair[1]-pair[0], reverse=True)[:2]
        gaps.append((name, largest))

    lines = [
        "# 파일별 코드·데이터 증거 장부", "",
        "이 장부는 [종합 리포트](consolidated-report-2026-10-21.md)의 첫 빈칸을 주소 단위로 추적한다. 12개 게임 실행 파일을 각 파일의 로드 주소로 분리하고, 파일의 **모든 바이트를 한 범주에만** 넣었다. `$8956`을 공유하는 오버레이는 서로 다른 행이다. 원본 데이터 파일 `MAPCHARS/TCMAPS/NIF`와 `PRODOS`는 이 Ghidra 실행 프로그램 집계에서 제외한다.", "",
        f"**검증 코드**는 재조립이 일치하는 검토 조각에서 인라인 인자·짧은 표 바이트를 뺀 범위와 34개 `STUPH` JMP 벡터다. **검증 데이터**는 재조립된 JSR 뒤 인라인 인자와 방향표 {sum(end-start for ranges in INLINE_DATA.values() for start, end in ranges)}바이트, 공용 키 26바이트, 여섯 모듈의 핸들러 포인터 312바이트다. 후자의 대상 주소 156개는 [명령 행렬](command-dispatch-matrix.md)과 추출 파일·Ghidra가 일치한다. 중복을 뺀 오버레이 내부 대상 {local_target_total}곳도 Ghidra에서 명령 시작으로 확인하지만, 이 사실만으로 핸들러 효과는 검증되지 않는다. 나머지 `Ghidra 명령 후보/데이터 후보/미분류`는 **검증된 의미가 아니다**. 자동 분석의 함수 수나 후보 바이트 수를 완료율로 읽지 않는다.", "",
        "| 파일 | 길이 | 검증 코드 | 검증 데이터 | Ghidra 명령 후보 | Ghidra 데이터 후보 | 미분류 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, size, c in rows:
        lines.append(f"| `{name}` | {size:,} | {c['verified_code']:,} | {c['verified_data']:,} | {c['candidate_code']:,} | {c['candidate_data']:,} | {c['unclassified']:,} |")
    total = sum(size for _, size, _ in rows)
    lines.append(f"| **합계** | **{total:,}** | **{totals['verified_code']:,}** | **{totals['verified_data']:,}** | **{totals['candidate_code']:,}** | **{totals['candidate_data']:,}** | **{totals['unclassified']:,}** |")
    lines += ["", "## 검증 범위와 Ghidra가 어긋난 주소", "",
              "| 파일 | 검증 코드를 명령으로 놓친 구간 | 검증 데이터를 명령으로 오독한 구간 |",
              "| --- | --- | --- |"]
    for name, code_missed, data_misread in conflicts:
        code_text = ", ".join(map(fmt_span, contiguous(code_missed))) or "—"
        data_text = ", ".join(map(fmt_span, contiguous(data_misread))) or "—"
        lines.append(f"| `{name}` | {code_text} | {data_text} |")
    lines += ["", f"검증 데이터가 명령으로 표시되면 Ghidra 스크립트의 데이터 지정이 실패한 것이다. 검증 코드를 놓친 경우에는 진입점·자기 수정 코드·분기 경계를 다시 조사한다. 검증 조각 전체가 코드라는 가정 대신 [{len(FRAGMENTS)}개 주소별 조각](assembly-atlas.md)과 [인라인 인자 소스](../tools/ghidra/MarkUltimaInlineData.java)를 대조한다.",
              "", "## 아직 근거로 분류하지 않은 큰 연속 구간", "",
              "아래는 각 파일에서 검증 코드·데이터 **어느 쪽에도 속하지 않는** 긴 구간 두 개다. Ghidra 후보와 미분류가 섞일 수 있다. 길이순 목록은 작업 순위가 아니며, 특히 인트로 지원 파일의 화면 데이터가 큰 구간을 차지한다.", "",
              "| 파일 | 큰 미검증 구간 두 곳 |", "| --- | --- |"]
    for name, largest in gaps:
        lines.append(f"| `{name}` | {', '.join(map(fmt_span, largest)) or '—'} |")
    lines += ["", "## 다음 검토 단위", "",
              "1. `MI.U1` 공용 루틴과 `STUPH` 서비스에서 **호출되는 후보 구간**을 우선 검토한다. 인라인 인자와 자기 수정 피연산자를 데이터/명령으로 구분하고 호출자·읽기/쓰기·반환 계약을 남긴다.",
              "2. 간접 표의 모든 로컬 대상에서 시작하는 코드 경계를 확인한다. Ghidra에는 이 대상들을 시작점으로 주지만, 표 값만으로 대상 루틴의 끝과 효과는 증명되지 않는다.",
              "3. `SPA/TM`의 큰 빈 구간과 `U1.SYSTEM`의 미검토 구간을 실행 경로에 따라 줄인다. 화면·그림·문구 데이터를 포함한 길이를 순수 코드량으로 세지 않는다.",
              "", "[장부 생성기](../tools/build_code_data_ledger.py)는 비공개 `build/ghidra-project/*-memory.tsv`와 로컬 추출 파일을 읽어 위 숫자를 재생성한다. 원본 바이트나 대량 자동 역어셈블은 문서에 넣지 않는다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != result:
            print("code/data ledger is stale; run python3 tools/build_code_data_ledger.py", file=sys.stderr)
            return 1
        print("12 program code/data ledgers match private Ghidra spans")
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
