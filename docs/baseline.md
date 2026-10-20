# 0단계: 원본 실행 기준점

2026-10-20 현재 확인한 범위와 재현 방법이다. [로드맵](porting-roadmap.md)의 0단계 완료 여부는 아래 표에 따라 판단한다. 여기의 명령은 저장소 루트에서 실행한다.

| 항목 | 현재 결과 |
| --- | --- |
| 디스크 판본 | `disk/UltimaI.woz`: CiderPress II가 ProDOS `U1`, RDOS 16-sector, 140KB로 인식. SHA-256과 크기는 비공개 로컬 매니페스트에 기록. |
| 추출물 | 16개 파일의 크기와 로드 주소 확인. CiderPress II로 새로 추출한 16개 파일과 `extracted/`가 모두 바이트 단위로 일치. |
| 분석 도구 | Python, `da65`, `ca65`, `ld65`, CiderPress II 경로·버전을 로컬 매니페스트에 기록. |
| 기존 분석 검증 | 10개 역어셈블 조각의 재조립 결과와 `TCMAPS` 구조 검사가 통과. |
| 에뮬레이터 | [a2m](https://github.com/StewBC/a2m)의 고정 커밋 `d863ad98487639445db16134d260221839cb72e9`을 `build/emulator/`에 빌드. 실행 파일 버전·해시와 Apple //e Enhanced 설정을 로컬 매니페스트에 기록. |
| 시작 스냅샷·입력 재생 | **미완료.** 첫 `$2088` 스냅샷은 ProDOS 실행 중에 잡힌 것으로 판명되어 폐기했다. `U1.SYSTEM` 메모리 영상까지 검사하는 새 캡처를 실행해야 한다. |
| 기존 캐릭터·주요 장면 상태 | **미완료.** 시작 경로가 추적된 뒤 게임 진행에 맞춰 별도 로컬 스냅샷을 만든다. |

## 로컬에서 기준점 만들기

원본 디스크는 `disk/`, 추출물은 `extracted/`에 둔다. 두 디렉터리와 `build/`는 Git에서 제외한다. `tools/baseline.py capture`는 로컬 매니페스트를 새로 쓰므로, 이미 수집한 실행 스냅샷이 있다면 먼저 백업한다.

```sh
python3 tools/baseline.py capture \
  --disk disk/UltimaI.woz \
  --extractor ~/Applications/CiderPress2/cp2 \
  --emulator build/emulator/a2m-build/a2m
python3 tools/check_all.py
```

`check_all.py`는 매니페스트의 SHA-256·버전, 디스크 재추출, 파일 크기·주소, 검토된 어셈블리, `TCMAPS`를 검사한다. 일치하지 않으면 실패한다. 매니페스트는 `build/baseline/manifest.json`에만 저장된다.

## 에뮬레이터 빌드와 첫 실행 기록

이 저장소에서는 WOZ 읽기, Apple //e Enhanced, 디버거, 로컬 제어 포트와 스냅샷을 제공하는 [a2m의 고정 버전](https://github.com/StewBC/a2m/tree/d863ad98487639445db16134d260221839cb72e9)을 첫 추적 도구로 선택했다. 이 프로젝트는 현재 보관 상태이므로 커밋을 고정한다. 다른 에뮬레이터와의 교차 검증은 이후 표현·타이밍 단계에서 수행한다.

```sh
git clone --depth 1 \
  --branch frozen-for-machines-d863ad98487639445db16134d260221839cb72e9 \
  https://github.com/StewBC/a2m.git build/emulator/a2m
cmake -S build/emulator/a2m -B build/emulator/a2m-build \
  -DCMAKE_BUILD_TYPE=Release -DSDL2_DIR=/opt/homebrew/lib/cmake/SDL2
cmake --build build/emulator/a2m-build --target a2m -j 6
```

빌드 후 위의 `baseline.py capture`를 실행한다. 그다음 **로컬 소켓이 허용되는 일반 터미널에서** 다음을 실행한다.

```sh
python3 tools/capture_boot.py
python3 tools/check_all.py
```

첫 명령은 WOZ를 Slot 6 Drive 0에 장착하고 `$2088`에 실행 중단점을 건다. 이 주소는 ProDOS 코드에도 있으므로 PC만으로 게임 진입을 판정하지 않는다. `$2000`의 헤더 16바이트와 `$2088`의 코드 16바이트가 추출된 `U1.SYSTEM`과 일치할 때만 스냅샷을 저장한다. 복원 후에도 두 영역을 다시 검사한다. 첫 `$2088`이 다른 프로그램이면 한 명령을 진행한 뒤 중단점을 다시 건다. 입력은 빈 시퀀스로 기록하고 결과 파일은 `build/baseline/`에만 남긴다.

초기 버전은 a2m의 `--break=2088`이 10진수로 해석되는 것을 놓쳤다. 제어 포트의 `break-exec $2088`로 바꾼 뒤 프레임 310, 사이클 5,270,292에서 스냅샷을 얻었지만, 복원된 `$2088`의 바이트 `AC 0F`는 `PRODOS` 추출물과 일치하며 `U1.SYSTEM`의 `78 A9`와 다르다. 따라서 그 스냅샷은 게임 진입의 런타임 증거가 아니다. 기존 로컬 매니페스트의 해당 스냅샷 참조도 무효화했다.

새 게임과 이어하기 경로의 스냅샷, 프레임 수가 포함된 입력 재생은 1단계 실행 추적 중 마련한다. 0단계의 전체 완료 표시는 그때 갱신한다.

메모리 영상이 확인된 새 스냅샷을 만든 뒤 `python3 tools/trace_startup.py`로 `U1.SYSTEM`의 `$2220`, 저주소 전송점 `$0136`, `U1.INTRO`의 진입점을 확인한다. 로그·스냅샷은 `build/traces/startup/`에만 저장된다.
