#!/usr/bin/env python3
"""Generate SPA's separate front-view command pointer map from local extraction."""

import argparse
from pathlib import Path
import sys

from build_command_matrix import KEYS, KEY_NAMES
from disassemble import FILES, ROOT


OUTPUT = ROOT / "docs/spa-view-commands.md"
BASE = FILES["SPA"][0]
TABLE = 0x9BCB


def render():
    data = (ROOT / "extracted/SPA").read_bytes()
    if len(data) != FILES["SPA"][1]:
        raise ValueError("SPA extraction size changed")
    at = lambda address, size: data[address - BASE:address - BASE + size]
    if at(0x93C1, 3) != bytes.fromhex("20 a2 82"):
        raise ValueError("view subloop no longer calls shared key decoder")
    if at(0x93CC, 3) != bytes.fromhex("bd cb 9b") or \
       at(0x93D2, 3) != bytes.fromhex("bd cc 9b") or \
       at(0x93D8, 1) != b"\x20":
        raise ValueError("view subloop pointer patch does not match table")
    values = [int.from_bytes(at(TABLE + 2*i, 2), "little") for i in range(26)]
    for target in values:
        if not (0x7000 <= target < 0x8956 or BASE <= target < BASE + len(data)):
            raise ValueError(f"view handler ${target:04X} is not resident")
    lines = [
        "# SPA 항법 화면의 별도 키 명령표", "",
        "`SPA`의 일반 입력 `$8A5F`는 `$91D3`의 표를 사용한다. `V` 명령이 여는 항법 화면은 `$9361`에서 입력을 반복하며, `$93C1`의 공용 `$82A2` 해석 뒤 **다른** 26개 포인터를 `$9BCB`에서 읽어 `$93D8`의 호출 피연산자를 패치한다. 두 상태의 명령표를 포트에서 분리해야 한다.", "",
        "이 표는 추출 파일의 **정적 주소 관계**다. `$97EE` 중복 항목의 표시·비용과 다수 핸들러의 실제 효과는 아직 실행 검증 대상이다. Space·방향 네 개·H는 첫 항법 화면에서 핸들러와 다음 입력까지 재생했다. Space의 `$95BF`에는 `Center` 표시가 있다. 방향키는 속도 성분 `±4`와 Fuel 2 소모, H는 Fuel 100 경계와 한 구역 이동을 보였다. [실행 추적](../tools/trace_spa_view_controls.py)과 [검증기](../tools/verify_spa_view_controls.py)를 참조한다.", "",
        "| 인덱스 | 키 | 항법 화면 대상 | 위치 |",
        "| ---: | --- | ---: | --- |",
    ]
    for index, (key, target) in enumerate(zip(KEYS, values)):
        name = KEY_NAMES.get(key, chr(key))
        location = "공용 `MI.U1`" if target < BASE else "`SPA` 내부"
        lines.append(f"| {index} | `{name}` (`${key:02X}`) | `${target:04X}` | {location} |")
    lines += ["", f"고유 대상은 {len(set(values))}곳이고, `$97EE`로 모이는 키는 {values.count(0x97EE)}개다. 공용 엔진으로 직접 이어지는 항목은 {sum(target < BASE for target in values)}개다. 일반 SPA 명령표는 [여섯 모듈 행렬](command-dispatch-matrix.md)의 `SPA` 열을 본다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != result:
            print("SPA view matrix is stale", file=sys.stderr)
            return 1
        print("SPA view command table matches local extraction")
        return 0
    OUTPUT.write_text(result)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
