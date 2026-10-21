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
        "이 표는 추출 파일의 **정적 주소 관계**다. Space·방향 네 개·H는 첫 항법 화면에서 핸들러와 다음 입력까지 재생했다. Space의 `$95BF`에는 `Center` 표시가 있다. 방향키는 속도 성분 `±4`와 Fuel 2 소모, H는 Fuel 100 경계와 한 구역 이동을 보였다. [실행 추적](../tools/trace_spa_view_controls.py)과 [검증기](../tools/verify_spa_view_controls.py)를 참조한다.", "",
        "나머지 고유 대상을 [같은 첫 항법 입력 상태에서 독립 재생](../tools/trace_spa_view_survey.py)했다. 다음 표의 차이는 **V 화면 첫 입력 시점부터** 측정하므로 진입·화면 갱신에 따른 공통 변경도 포함한다. `$93DB`는 하위 명령 호출이 반환된 지점이며, 그 뒤 화면 입력까지는 이 조사에서 재생하지 않았다. I와 Z는 `$160F/$160D`의 STUPH 지연·표시 루프 중 제한 시간에 도달했다. 이 둘의 완료 또는 실패를 뜻하지 않는다. [검증기](../tools/verify_spa_view_survey.py)는 선택된 실제 대상과 확인 가능한 상태 차이를 고정한다.", "",
        "| 키 | 실제 대상 | 관찰된 다음 경계 | 구분되는 상태 차이 |",
        "| --- | ---: | --- | --- |",
        "| 기본 A | `$97EE` | `$93DB` | 공통 턴 상태·표시 변경 |",
        "| F | `$964D` | `$93DB` | Fuel 하위 바이트 `$E3→$D9` (10 소모) |",
        "| I | `$98F2` | 미도달 | `$9241/$9242/$9280/$9286` 작업 상태 변경 |",
        "| R | `$98F5` | `$93DB` | 공통 상태·표시 변경 |",
        "| V | `$98FE` | 일반 SPA 입력 `$8A5F` | `$7E51/$7E52` 반환 벡터 변경 |",
        "| Z | `$99FE` | 미도달 | `$7E4E` 및 표시 상태 변경 |",
        "| Ctrl-A | `$8845` | `$93DB` | `$7E71:FF→00` |",
        "| N | `$885B` | `$93DB` | `$7E72:FF→00` |", "",
        "I·Z의 전체 작동, F의 대상·피해, R의 시각 효과, Ctrl-A·N 필드의 의미와 실패 조건은 후속 재생이 필요하다.", "",
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
