# Multi-Agent 데모 시나리오 전환 — 다음 세션 인수인계

작성일: 2026-10-20
대상 저장소: `jaewon-i/kiro-agent-loop-demo`
작업 브랜치: `feature/multi-agent-loop` (**main 변경 금지**)

## 1. 다음 세션의 목표

AI Engineer World's Fair 2026의 Loop Engineering 발표를 위해, 기존 **할인 계산기 + 단일 Kiro Agent + Python 외부 검증 루프** 데모를 **Developer Agent ↔ QA Agent 간 반복 피드백** 데모로 전환한다. 핵심 메시지는 단순한 재시도가 아니라 **서로 다른 역할의 AI 에이전트가 실제 코드/검토 결과를 주고받고, 독립적인 검증 게이트가 종료를 결정하는 구조**다.

**절대 원칙:** 실제 실행하지 않은 Kiro 대화, 발견 결함, 반복 횟수, PASS 결과를 발표 자료에 실제 결과처럼 쓰지 않는다.

## 2. 현재 상태 (이미 GitHub에 반영됨)

- `feature/multi-agent-loop` 브랜치 생성 완료.
- 기존 루트 `loop.py`, `verify.py`, `src/DiscountCalculator.java`, `tests/DiscountTest.java` 및 발표 자료는 변경하지 않음.
- 새 `multi-agent/` 디렉터리에 다음 파일 추가:
  - `src/OrderService.java`: 의도적으로 결함이 있는 Java 주문 서비스 시작 코드
  - `tests/OrderServiceTest.java`: 독립적인 Java 인수 테스트
  - `verify.py`: Java 컴파일 및 테스트 실행
  - `agent_loop.py`: Python이 Kiro Developer/QA 세션을 순차 호출하고 피드백/검증을 반복
  - `README.md`: 실행 방법 및 제약
- **아직 실제 Kiro CLI 실행 및 결과 검증은 수행하지 않음.**
- 현재 구현은 **Spring Boot REST API가 아닌 Java 서비스**다. PPT에서 REST API 구현 완료라고 설명하지 말 것.

## 3. 다음 세션의 우선순위

### A. 로컬에서 실제 실행 확인 (가장 우선)

Mac의 저장소에서:

```bash
git fetch origin
git switch feature/multi-agent-loop
cd multi-agent
java -version
javac -version
python3 --version
kiro-cli --version
python3 verify.py
python3 agent_loop.py --max-rounds 3
```

`OrderService.java`는 Java `record`를 사용하므로 **JDK 17 이상** 필요. `verify.py` 초기 실패는 알려진 결함을 보여주기 위한 의도된 상태다. `agent_loop.py`는 Kiro 인증/파일 접근 권한이 있는 로컬 Mac에서 실행해야 한다.

실행 후 `multi-agent/.loop/summary.json`, `developer-*.log`, `qa-*.log`를 검토한다. 민감정보/토큰/경로를 확인한 뒤 공유한다. 로그를 GitHub에 올릴 때는 민감정보가 없는지 먼저 확인할 것. 로그 공유 대신 채팅에 파일 첨부해도 된다.

### B. 실제 데모 신뢰성 개선

- 현재 QA 에이전트는 **프롬프트로만 읽기 전용**을 지시한다. CLI에는 `fs_write`가 허용되어 있으므로 기술적으로 읽기 전용이 강제되지 않는다. QA 역할에는 실제로 `fs_read`만 허용하도록 수정하고 동작 확인.
- 보호 파일 검사는 지정된 세 파일만 감시하며 보안 샌드박스가 아니다. 안전한 임시 복제본에서 실행.
- QA 출력의 JSON 파싱이 Kiro 실제 응답 형식에 맞는지 확인.
- Java 인수 테스트는 기본 검증/멱등성/금액을 검사하지만 **동시성은 테스트로 입증하지 않는다**. 재현 가능한 동시성 테스트 추가 여부 검토.
- Developer가 실제로 발견 결함을 고치고 QA가 독립적으로 검토했는지 로그를 기준으로 확인. AI QA 승인만으로 성공 처리하지 말고 Java Gate도 PASS여야 함.
- 시연 시 실패 후 피드백이 다음 Developer 세션에 전달되는 장면을 가시화. 실행 결과가 한 번에 PASS하면 실제로 없었던 실패 반복을 꾸미지 말고, 필요하면 명시적 *시연용 결함 주입* 기능을 별도로 설계/표기.
- 종료 조건, timeout, 최대 반복 횟수, 실패 시 종료 코드, 로그 저장을 검증.
- 실제 CLI 동작이 불안정하면 리허설용 mock 모드를 별도로 만들 수 있으나 **실제 AI 실행과 명확히 구분**.

### C. 시나리오 범위 결정

현재의 Java `OrderService.create(requestId, itemId, quantity, unitPrice)`는 빠른 검증을 위한 MVP다.

- 주문 검증: 빈 ID, 수량 0 이하, 음수 가격
- 멱등성: 동일 requestId + 동일 payload 재요청은 동일 주문 반환
- 충돌: 동일 requestId + 다른 payload는 예외
- 동시성: 동시 요청에서 check-then-act 경쟁 조건 제거
- 큰 금액 계산: `long` 기반 오버플로 고려

**선택지:** 발표까지 시간이 부족하면 Java 서비스 MVP로 데모를 안정화. 여유가 있으면 Spring Boot HTTP 주문 API + HTTP 상태코드 + REST Assured/JUnit 검증으로 확장. 확장 전에는 Spring Boot 데모라고 부르지 말 것.

### D. PPT 수정

현재 자료: `docs/AI_Agent_Loop.pptx`
참고 자료: `docs/KIRO_AGENT_LOOP_HANDOFF.md`, `docs/AI_Engineer_Worlds_Fair_2026_Loops_References.md`, `docs/STUDY_GUIDE.md`

먼저 수정 가능한 부분:
1. 기존 단일 Agent 수리 시나리오와 신규 Developer ↔ QA 협업 시나리오의 차이.
2. 아키텍처: Python Controller → Developer Agent → QA Reviewer Agent → 독립 Java QA Gate → 피드백 재전달.
3. 역할 경계: Python은 **AI가 아니라 오케스트레이터**. Kiro 세션 2개가 AI 에이전트 역할을 수행.
4. 성공 기준: QA 리뷰 승인 **AND** Java QA Gate PASS.
5. 제한/실패 조건: timeout, 최대 반복, 인증/도구 오류, 보호 파일 변경.

**실행 결과 확인 후에만** 수정할 부분:
- 실제 Agent 대화/피드백 인용
- 실제 발견 결함 및 수정 diff
- 반복 횟수, 테스트 PASS/FAIL
- 터미널 캡처 및 결과 화면
- 성공/실패에 대한 발표자의 결론

## 4. 발표 메시지와 용어 주의

- Kiro CLI 내부 도구 사용 반복과 Python의 외부 제어 루프는 다른 레벨이다. Inner/Outer Loop는 설명용 구분이며 행사에서 공식적으로 사용된 명칭이라고 단정하지 않는다.
- 멀티 에이전트의 가치는 에이전트 수가 아니라 **역할 분리, 독립적 검토, 피드백의 실제 반영, 검증 가능성**에 있다.
- AI가 PASS라고 말한 것과 실제 테스트 PASS는 다르다.
- 현재 Python Controller는 의사결정을 수행하는 AI가 아닌 결정적 제어 코드다.
- 실제 성공을 확인하지 못했다면 “설계/예정/실험 중”으로 표현한다.

## 5. 다음 세션 시작용 프롬프트 (그대로 붙여넣기)

> GitHub `jaewon-i/kiro-agent-loop-demo`의 `feature/multi-agent-loop` 브랜치에서 작업을 이어가자. 먼저 `docs/MULTI_AGENT_SCENARIO_HANDOFF.md`를 읽고 현재 `multi-agent/` 소스를 확인해줘. 목표는 실제 Kiro Developer ↔ QA Agent 협업 루프를 안정적으로 실행하고, **검증된 로그만** 바탕으로 `docs/AI_Agent_Loop.pptx`의 데모 부분을 업데이트하는 거야. `main`은 건드리지 마. 우선 로컬 실행 결과를 확인하고 문제를 수정하자. 아직 실행 결과가 없다면 결과를 추측하지 말고 필요한 로그를 요청해줘.

## 6. 완료 기준

- [ ] 로컬 Kiro 실행 로그 확보
- [ ] Developer와 QA의 실제 상호작용 및 피드백 확인
- [ ] 독립 Java QA Gate 결과 확인
- [ ] 시연 안정성/권한/반복 종료 검증
- [ ] PPT의 아키텍처/시나리오 교체
- [ ] 실제 결과 기반 캡처/결론 반영
- [ ] 변경사항은 `feature/multi-agent-loop`에만 커밋
