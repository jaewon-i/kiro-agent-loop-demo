# 발표 준비 공부 자료 (PART 1·2)

모든 링크는 2026-10-20에 직접 열어 내용을 확인했다. 괄호 안은 관련 슬라이드 번호.

| 순서 | 자료 | 볼 부분 | 시간 |
|---|---|---|---|
| 1 | [Business Insider — Forget prompt engineering: 'Loop engineering' is all the rage now](https://www.businessinsider.com/what-are-loops-ai-engineering-tips-2026-6) (2026-06-20, 행사 전 보도) | "What are loops?" 문단, Addy Osmani의 "자기 숙제를 후하게 채점" 인용 (3·7장) | 5분 |
| 2 | [swyx — The Highest Loop](https://github-main-preview.ai.engineer/talks/Fva8hFosqyQ-highest-loop-swyx) (오프닝 키노트, 7:20) | 1:05 "From tokens to scheduled work", 1:58 "Move up for scale, down for reliability" (4장) | 10분 |
| 3 | [Kyle Mistele — Loop Engineering from First Principles](https://github-main-preview.ai.engineer/talks/xIt_mTQp6mY-loop-engineering-from-first-principles) (17:57) | 4:33 "Measure, correct and measure again" (제어 루프, 5·9장), 0:27 Ralph 이야기, 15:10 "리뷰가 막히면 멈춰라" | 20분 |
| 4 | [Latent Space — AIEWF Daily Dispatch: Loops, Software Factories & FDEs](https://www.latent.space/p/aiewf-daily-dispatch-loops) (2026-07-01) | 첫 문단, "Software factories" 절 (2장) | 5분 |
| 5 | [Latent Space — The great loops debate and the state of AI engineering](https://www.latent.space/p/aiewf-daily-dispatch-locomotives) (2026-07-03) | 디베이트 절, Amplify 설문 절 (15장 — 4부지만 질문이 나오기 쉬움) | 5분 |

시간이 없으면 3번 하나만 본다. 데모 설계(센서 = `verify.py`, 컨트롤러 = `loop.py`, 실행기 = Kiro)와 그대로 맞아서 질문 대응에 가장 도움이 된다.

## 각 자료에서 챙길 한 줄

- **Business Insider**: Loop = 사람이 매번 프롬프트를 쓰지 않아도 AI 에이전트를 이끄는 반복 시스템. 가장 큰 우려는 비용.
- **swyx**: 핵심 역량은 "지금 어느 루프에서 일하고 있나"를 아는 것. 준비되면 한 층 위로(규모), 깨지면 한 층 아래로(신뢰성). 무조건 높이 쌓는 게 목표가 아니다.
- **Kyle Mistele**: 목표값 – 센서 – 컨트롤러 – 실행기. 한 번에 끝내려 하지 말고 작게 고치고 다시 측정한다. 측정 없는 반복은 눈먼 루프.
- **Latent Space (Day 2)**: 둘째 날 대화를 지배한 단어가 loop. 메인 트랙 주제는 Software Factories.
- **Latent Space (Debate)**: 찬성은 "피할 수 없다", "핵심은 검증 가능성". 신중론은 "과대광고가 규율을 앞지른다", "작게 시작하라". 에이전트 통제 계층은 아직 아무도 정립하지 못했다.

## 주의

- swyx 키노트 제목은 ai.engineer 페이지 기준 "The Highest Loop". Latent Space 기사는 "Loopcraft: The Art of Stacking Loops"라고 적었는데, Loopcraft는 그가 언급한 에세이 이름이다.
- 4장의 단계 구분과 축은 발표 내용을 시각화하기 위한 해석이며, 원본 슬라이드에 있는 그림은 아니다.
