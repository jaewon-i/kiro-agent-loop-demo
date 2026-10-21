# 점진적 마이그레이션 Outer Loop 데모

Kyle Mistele "Loop Engineering from First Principles"(AIEWF 2026)의 제어 루프 구조를 그대로 옮긴 데모다. 버그 하나를 고치는 main 데모와 달리, **한 번에 끝낼 수 없는 일**(파일 6개 마이그레이션)을 루프가 오차를 재며 하나씩 줄여 간다.

과제: `src/`의 Java 클래스 6개가 쓰는 낡은 날짜 API(`java.util.Date`, `Calendar`, `TimeZone`, `SimpleDateFormat`)를 `java.time`으로 옮긴다. 동작(출력 문자열, 시간대, 정밀도, 예외)은 하나도 바뀌면 안 된다.

## 제어 루프 대응

| 제어 루프 | 이 데모 |
|---|---|
| 목표값 | 낡은 API를 쓰는 파일 0개 + 동작 테스트 PASS |
| 센서 | `measure.py`(남은 파일 수) + `verify.py`(컴파일 + 동작 테스트 28개) |
| 컨트롤러 | `migrate_loop.py` — 남은 파일 하나를 골라 새 세션에 지시, 결과로 반영/되돌림 결정 (AI 아님) |
| 실행기 | Kiro CLI — 그 파일 하나만 옮긴다 |
| 시스템 | `src/*.java` |

## loop 1회의 규칙

1. 센서가 남은 파일을 센다. 0개이고 테스트 PASS면 종료.
2. 남은 파일 중 하나를 골라, **저장소 밖 임시 작업 폴더**(src + tests 복사본)에서 새 Kiro 세션을 실행한다.
3. 컨트롤러가 대상 파일 **하나만** 실제 `src/`에 반영하고 다시 잰다.
   - 테스트 PASS + 그 파일에 낡은 API 없음 → **ACCEPT** (남은 파일 수 감소)
   - 테스트 FAIL, 낡은 API 남음, 또는 변경 없음 → **REVERT**, 실패 출력을 들고 같은 파일을 새 세션으로 재시도
   - 같은 파일이 `--max-attempts`(기본 2)번 실패 → 사람에게 넘기고 다음 파일로 (억지로 밀어붙이지 않음)
4. 대상 외 파일 변경은 무시한다. 테스트·센서·컨트롤러를 건드리면 복원하고 즉시 중단한다.

종료: `DONE`(0) · `PARTIAL_NEEDS_HUMAN`(1) · `MAX_ITERATIONS`(1) · `AGENT_ERROR`(2) · `GUARDRAIL_STOP`(3)

## 실행

```bash
cd migration
python3 measure.py                                  # 6/6 files remaining
python3 verify.py                                   # ALL 28 BEHAVIOR CHECKS PASSED (레거시 기준선)
python3 migrate_loop.py --provider mock --reset     # 리허설 (AI 아님, 약 5초)
python3 migrate_loop.py --provider kiro --reset     # 실제 Kiro (약 2~3분)
```

각 상태 줄 아래에 `↳` 로 시작하는 한국어 해설이 붙는다(무엇을 했고 왜 반영/되돌렸는지). 영어 줄만 보려면 `--no-ko`. 실행 후 소스를 시작 상태로 되돌리려면 `git restore migration/src` (또는 다음 실행에서 `--reset`).

Kiro 호출: `kiro-cli chat --no-interactive --trust-tools=fs_read,fs_write "<prompt>"`. 셸 등 다른 도구는 비대화형 모드에서 자동 거부된다.

증거: `.loop/summary.json`(궤적 6 → … → 0 포함), `iteration-NN.json`, `agent-NN.log`, `diff-NN.patch`.

## 검증된 결과 (2026-10-21, macOS, kiro-cli 2.32.0, JDK 17)

- **실제 Kiro**: 6개 파일 모두 1회에 ACCEPT, 세션 6개, 약 2분 20초. 궤적 `6 → 5 → 4 → 3 → 2 → 1 → 0`, 테스트 PASS. 재시도는 일어나지 않았다. 기록: `docs/captures/migration/`.
- **mock 리허설**: `ShippingSchedule` 1회차에 의도적 실수(파싱 예외를 감싸지 않음)를 넣어 REVERT → 재시도 → ACCEPT 흐름을 보여준다. **스크립트이며 AI 실행이 아니다.** 정답 코드는 `rehearsal/`.
- **테스트 공정성**: 정답 `java.time` 버전은 28/28 PASS. 흔한 실수 4가지(시간대를 UTC로, 밀리초 포함, 파싱 예외 미변환, 2월 30일 허용)는 각각 테스트가 잡는다.
- **가드레일**: 테스트 변조 → 복원 + `GUARDRAIL_STOP`, 대상 외 파일 변경 무시, 잘못된 동작 → REVERT, 낡은 API가 남은 변경 → REVERT, 저장소의 실제 `src/`를 직접 수정 → 되돌림.

개발 중 발견한 문제: 작업 폴더를 저장소 안에 두었을 때 Kiro가 파일 검색으로 실제 `src/`를 찾아 수정하는 경우가 있었다. 작업 폴더를 저장소 밖 임시 폴더로 옮기고, 실제 `src/`가 바뀌면 되돌리는 가드레일을 추가했다. 이 수정 전 실행 결과는 증거로 쓰지 않는다.

## 한계

- 동작 테스트는 28개 사례만 고정한다. 예: Kiro가 `LogTimestamp`에 쓴 `xxx` 패턴은 오프셋이 0일 때 원래의 `XXX`와 다르게 출력하지만(`+00:00` vs `Z`), 이 클래스는 서울 시간대만 쓰므로 실제 동작 차이는 없다. 테스트가 고정한 것만 보장된다.
- 보호 파일 검사는 보안 샌드박스가 아니다. 비밀정보가 없는 일회용 체크아웃에서 실행할 것.
- AI 결과는 매번 다르다. 재시도가 생길 수도, 사람에게 넘어가는 파일이 생길 수도 있다.
