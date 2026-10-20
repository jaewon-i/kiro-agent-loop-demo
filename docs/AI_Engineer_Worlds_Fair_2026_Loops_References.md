# AI Engineer World's Fair 2026 — Loop 관련 발표 및 참고자료

> 목적: 별도 세션에서 PPT 업데이트 시 참고할 수 있도록, **직전 답변의 행사 발표·기사·발표 활용 포인트만** 정리한 문서. 이전 Kiro 데모 구축 대화 전체는 포함하지 않음.

## 1. 행사와 핵심 주제

- 행사: **AI Engineer World's Fair 2026**, 2026년 6월 29일~7월 2일, 샌프란시스코.
- Loop는 단일 제품이나 독립된 하나의 기술명보다는, AI가 작업을 반복하고 검증·피드백을 통해 목표를 달성하는 **AI 엔지니어링 패러다임**으로 다뤄졌다는 점이 핵심.
- 발표에선 단순 프롬프트 작성보다 **반복 실행 구조, 종료 조건, 검증, 자동화**를 어떻게 설계할지에 초점을 맞출 수 있음.

## 2. 관련 발표 세션

### ① The Highest Loop — Shawn “swyx” Wang

- 성격: 오프닝 키노트, Loop 개념을 전체적으로 설명하는 데 적합.
- 핵심: 토큰 생성에서 채팅, 도구 사용, 목표 달성, 자동화로 AI 작업 단위가 확장되며, 이러한 계층을 쌓는 **Loop Stacking** 관점.
- 발표 영상·내용: https://github-main-preview.ai.engineer/talks/Fva8hFosqyQ-highest-loop-swyx
- PPT 활용: “왜 Loop인가?”라는 도입부와 개념 설명에 사용.

### ② Loop Engineering from First Principles — Kyle Mistele

- 성격: 약 18분 발표, 실제 개발 과정에 Loop를 적용하는 실무 관점.
- 핵심: 작은 코드 변경, CI, 자동 검증, 피드백 및 사람의 리뷰를 연결하는 접근. 반복 자체보다 **검증 가능한 반복 구조**가 중요.
- 발표 영상·스크립트·챕터: https://github-main-preview.ai.engineer/talks/xIt_mTQp6mY-loop-engineering-from-first-principles
- PPT 활용: 외부 QA Gate, 테스트 결과를 통한 재실행을 설명할 때 연결.

### ③ The Great Loops Debate — Geoffrey Huntley 등

- 성격: 자율 소프트웨어 개발과 Software Factory의 실현 가능성에 관한 패널 토론.
- 핵심: AI가 자율적으로 개발을 이어갈 수 있는 가능성과, 신뢰성·비용·검증의 현실적 제약을 함께 검토.
- 관련 현장 기사: https://www.latent.space/p/aiewf-daily-dispatch-locomotives
- PPT 활용: 마지막에 도입 시 주의점과 한계를 균형 있게 소개.

## 3. 현장 기사 및 보도

1. **Latent Space — Loops, Software Factories & Forward Deployed Engineers** (2026-07-01)
   - 행사 현장의 Loop 및 Software Factory 관련 발표와 분위기를 정리.
   - https://www.latent.space/p/aiewf-daily-dispatch-loops
2. **Latent Space — The Great Loops Debate and the State of AI Engineering** (2026-07-03)
   - Loop에 대한 찬반 관점, 실현 가능성과 신뢰성 이슈를 다룸.
   - https://www.latent.space/p/aiewf-daily-dispatch-locomotives
3. **Business Insider — Forget Prompt Engineering: Loop Engineering Is All the Rage Now** (2026-06-20)
   - 행사 전 보도. 프롬프트 엔지니어링에서 Loop 설계로 관심이 옮겨가는 흐름을 설명.
   - https://www.businessinsider.com/what-are-loops-ai-engineering-tips-2026-6

## 4. 발표에서 설명할 Loop 계층

| 계층 | 의미 |
|---|---|
| Token Loop | 토큰을 반복 생성 |
| Chat Loop | 사람과 AI가 질문·응답을 반복 |
| Agent Turn | AI가 도구를 호출하고 결과를 확인하며 반복 |
| Goal Loop | 목표 달성 여부를 평가하고 필요하면 재시도 |
| Automation Loop | 일정이나 이벤트에 따라 작업을 자동 시작 |
| Software Factory | 여러 Loop를 조합해 소프트웨어 개발 과정을 운영 |

이 표는 swyx의 발표 취지를 설명하기 위한 **요약·재구성**이다. 정확한 슬라이드 용어와 단계 구분은 원본 발표 영상·슬라이드에서 재확인할 것.

## 5. PPT 업데이트 권장 구성

- **도입(약 5분):** 행사 소개 → Loop가 주요 화두가 된 배경 → swyx의 The Highest Loop 소개.
- **개념 설명:** Token / Chat / Agent / Goal / Automation 등 Loop 계층을 간단히 시각화.
- **실무 연결:** Kyle Mistele의 발표와 연계해 작은 작업, 테스트, CI, 피드백을 설명.
- **데모 연결:** Java + Kiro CLI + 외부 QA Gate 예시는 **Goal Loop를 외부 Controller로 구현한 사례**라고 표현.
- **한계와 결론:** The Great Loops Debate를 인용해 자율성만큼 검증, 안전장치, 비용 관리가 중요하다고 설명.

### PPT에 바로 사용할 핵심 문장

> Loop는 단순히 AI에게 같은 작업을 여러 번 시키는 것이 아니라, **실행·검증·피드백·종료 조건을 설계해 목표 달성을 반복적으로 관리하는 방식**이다.

> 우리가 구현한 외부 Kiro Controller는 Goal Loop의 한 구현 사례이지, 완전한 Software Factory 전체를 구현한 것은 아니다.

## 6. 참고 시 주의사항

- 본 문서는 **직전 답변 내용을 독립 세션용으로 재구성한 참고 메모**이며, 각 링크의 현재 접근성이나 영상 원문을 이번 문서 작성 과정에서 다시 검증한 것은 아님.
- 발표 제목, 발표자, 세부 발언 및 슬라이드 인용은 최종 PPT 반영 전에 원본 링크에서 확인할 것.
- Business Insider 기사는 행사 *사전* 보도이며, 행사 현장 후기와 구별할 것.
- 이미지나 발표 슬라이드를 PPT에 직접 삽입할 경우 출처·저작권 조건을 확인할 것.
