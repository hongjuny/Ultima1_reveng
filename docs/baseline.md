# 0단계: 원본 실행 기준점

2026-10-20 현재 확인한 범위와 재현 방법이다. [로드맵](porting-roadmap.md)의 0단계 완료 여부는 아래 표에 따라 판단한다. 여기의 명령은 저장소 루트에서 실행한다.

| 항목 | 현재 결과 |
| --- | --- |
| 디스크 판본 | `disk/UltimaI.woz`: CiderPress II가 ProDOS `U1`, RDOS 16-sector, 140KB로 인식. SHA-256과 크기는 비공개 로컬 매니페스트에 기록. |
| 추출물 | 16개 파일의 크기와 로드 주소 확인. CiderPress II로 새로 추출한 16개 파일과 `extracted/`가 모두 바이트 단위로 일치. |
| 분석 도구 | Python, `da65`, `ca65`, `ld65`, CiderPress II 경로·버전을 로컬 매니페스트에 기록. |
| 기존 분석 검증 | 10개 역어셈블 조각의 재조립 결과와 `TCMAPS` 구조 검사가 통과. |
| 에뮬레이터 | [a2m](https://github.com/StewBC/a2m)의 고정 커밋 `d863ad98487639445db16134d260221839cb72e9`을 `build/emulator/`에 빌드. 실행 파일 버전·해시와 Apple //e Enhanced 설정을 로컬 매니페스트에 기록. |
| 시작 스냅샷·입력 재생 | **게임 진입 확인.** 블록 동등 `.po` 이미지로 `$2088`에서 `U1.SYSTEM`의 헤더·진입 코드가 메모리에 적재된 것을 확인하고 스냅샷 복원 후 재검사했다. 입력은 빈 시퀀스다. 원본 WOZ의 a2m 부팅 오류와 이후 장면의 입력 재생은 미해결. |
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

`check_all.py`는 매니페스트의 SHA-256·버전, 디스크 재추출, 파일 크기·주소, 검토된 어셈블리, `TCMAPS`, 그리고 추적 스냅샷이 있을 때 `MAKE.INDATA`의 메모리 복사본을 검사한다. 일치하지 않으면 실패한다. 매니페스트는 `build/baseline/manifest.json`에만 저장된다.

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

첫 명령은 WOZ를 Slot 6 Drive 0에 장착하고 `$2088`에 실행 중단점을 건다. 이 주소는 ProDOS 코드에도 있으므로 PC만으로 게임 진입을 판정하지 않는다. `$2000`의 헤더 16바이트와 `$2088`의 코드 16바이트가 추출된 `U1.SYSTEM`과 일치할 때만 스냅샷을 저장한다. 복원 후에도 두 영역을 다시 검사한다. 첫 `$2088`이 다른 프로그램이면 한 명령을 진행한 뒤 중단점을 다시 건다. ProDOS 초기화 오류가 나면 MLI 반환 지점과 오류 상태를 기록하고, CiderPress로 원본의 280개 블록을 복사한 비공개 `.po` 이미지로 자동 재시도한다. 어떤 매체에서 캡처했는지와 각 해시를 로컬 기록에 남긴다. 입력은 빈 시퀀스로 기록하고 결과 파일은 `build/baseline/`에만 남긴다.

초기 버전은 a2m의 `--break=2088`이 10진수로 해석되는 것을 놓쳤다. 제어 포트의 `break-exec $2088`로 바꾼 뒤 프레임 310, 사이클 5,270,292에서 스냅샷을 얻었지만, 복원된 `$2088`의 바이트 `AC 0F`는 `PRODOS` 추출물과 일치하며 `U1.SYSTEM`의 `78 A9`와 다르다. 따라서 그 스냅샷은 게임 진입의 런타임 증거가 아니다. 기존 로컬 매니페스트의 해당 스냅샷 참조도 무효화했다.

새 검사를 적용한 WOZ 부팅은 첫 `$2088`이 ProDOS임을 확인한 뒤 `$21D4`에서 멈췄다. 추출된 ProDOS의 이 주소는 `JMP $21D4`이며, 바로 뒤에는 `RELOCATION / CONFIGURATION ERROR` 메시지가 있다. 따라서 현재 문제는 게임의 시작 파일 판단이 아니라 ProDOS 초기화 단계에 있다. 블록 변환 자체는 CiderPress가 280개 전부를 오류 없이 읽었으며, 변환된 이미지의 파일 카탈로그도 원본과 일치한다.

이후 로컬 실행에서 WOZ는 ProDOS `GET_PREFIX` 직후 `A=$27`, 분기 대상 `$21C3`으로 실패했다. 같은 블록의 `.po` 이미지에서는 `U1.SYSTEM` 진입점 `$2088`을 프레임 524, 사이클 8,915,922에 확인했다. 메모리의 `$2000–$200F`와 `$2088–$2097`은 추출된 `U1.SYSTEM`과 바이트 단위로 일치했고, 스냅샷 복원 뒤에도 일치했다. 이는 게임 진입에 대한 런타임 증거지만, `U1.INTRO`로의 전달과 WOZ 직접 부팅은 아직 검증하지 않았다. `.po`와 스냅샷은 Git 제외 경로인 `build/`에만 둔다.

새 게임과 이어하기 경로의 스냅샷, 프레임 수가 포함된 입력 재생은 1단계 실행 추적 중 마련한다. 0단계의 전체 완료 표시는 그때 갱신한다.

`python3 tools/trace_startup.py`는 저장된 스냅샷에서 `$21A0`, 시작 파일 분기, `$2220`, `$0136`, `U1.INTRO`의 `$0800 → $0F23`을 확인했다. 분기는 `$21D6`으로 진행했고, 살아 있는 헤더는 `U1.INTRO`를 가리켰다. `$0800`의 메모리는 추출물과 일치했다. 추적과 스냅샷은 `build/traces/startup/`에만 저장된다.

다음 로컬 실행은 `python3 tools/trace_intro_support.py`이다. 저장된 `$0F23` 상태에서 `$B70C` 요청, `$0F37` 반환 상태, `$1E00`의 `MAKE.INDATA` 영상과 `$0F41` 진행을 기록한다. 결과는 `build/traces/intro-support/`에만 남는다.

이 추적도 성공했다. `$B70C` 진입 후 `$0F37`에 carry clear로 돌아와 `$0F41`에 도달했다. `$1E00`부터 파일 전체와 메모리를 비교하면 첫 차이는 `$2000`이다. `MAKE.INDATA`가 실행 중 원본의 `$2000–$27FF`를 `$8700–$8EFF`로, `$27BD–$4DBC`를 `$6000–$85FF`로 복사하고 기존 위치를 재사용하기 때문이다. 두 복사본은 각각 2048·9728바이트 전부가 추출물과 일치한다. `python3 tools/verify_intro_support.py`로 비공개 스냅샷을 다시 검사할 수 있다.

다음 추적 `python3 tools/trace_intro_to_engine.py`는 `$0F41` 스냅샷에서 키 대기 루프까지 진행하고 ASCII `A` 한 번을 입력한다. 입력 전 상태·키 경로·`MI.U1` 로드와 `$7000`/`$8956` 진입을 비공개 스냅샷에 기록한다. 이 경로의 실제 실행 결과는 아직 확인하지 않았다.
