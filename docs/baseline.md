# 0단계: 원본 실행 기준점

2026-10-20 현재 확인한 범위와 재현 방법이다. [로드맵](porting-roadmap.md)의 0단계 완료 여부는 아래 표에 따라 판단한다. 여기의 명령은 저장소 루트에서 실행한다.

| 항목 | 현재 결과 |
| --- | --- |
| 디스크 판본 | `disk/UltimaI.woz`: CiderPress II가 ProDOS `U1`, RDOS 16-sector, 140KB로 인식. SHA-256과 크기는 비공개 로컬 매니페스트에 기록. |
| 추출물 | 16개 파일의 크기와 로드 주소 확인. CiderPress II로 새로 추출한 16개 파일과 `extracted/`가 모두 바이트 단위로 일치. |
| 분석 도구 | Python, `da65`, `ca65`, `ld65`, CiderPress II 경로·버전을 로컬 매니페스트에 기록. |
| 기존 분석 검증 | 10개 역어셈블 조각의 재조립 결과와 `TCMAPS` 구조 검사가 통과. |
| 에뮬레이터 | [a2m](https://github.com/StewBC/a2m)의 고정 커밋 `d863ad98487639445db16134d260221839cb72e9`을 `build/emulator/`에 빌드. 실행 파일 버전·해시와 Apple //e Enhanced 설정을 로컬 매니페스트에 기록. |
| 시작 스냅샷·입력 재생 | **미완료.** 이 작업 환경은 `127.0.0.1` 소켓 바인딩을 거부한다. `tools/capture_boot.py`는 에뮬레이터 제어 포트 연결을 시도할 때 `Operation not permitted`로 종료된다. 일반 로컬 터미널에서 재실행해 확인해야 한다. |
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

첫 명령은 WOZ를 Slot 6 Drive 0에 장착하고 `$2088` (`U1.SYSTEM` 진입)에 실행 중단점을 건다. CPU 상태를 확인한 뒤 로컬 스냅샷을 저장하고, 재시작해서 복원된 PC를 확인한다. 입력은 아직 없는 빈 시퀀스로 기록한다. 결과 파일은 `build/baseline/`에만 남는다. 이 검사가 통과하기 전까지 `$2088` 도달은 **정적 분석 결과**이며 런타임 확인으로 표시하지 않는다.

초기 버전은 a2m의 `--break=2088`이 10진수로 해석되는 것을 놓쳤다. 현재 스크립트는 제어 포트의 `break-exec $2088`로 중단점을 설정하며, 시작 시 이미 발생한 일시정지 이벤트를 소비한 후 실행한다. 실패 시 에뮬레이터를 강제 종료할 수 있게 해 종료 타임아웃이 원래 오류를 가리지 않도록 했다.

새 게임과 이어하기 경로의 스냅샷, 프레임 수가 포함된 입력 재생은 1단계 실행 추적 중 마련한다. 0단계의 전체 완료 표시는 그때 갱신한다.
