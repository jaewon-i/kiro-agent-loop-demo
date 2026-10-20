# Kiro Developer ↔ QA Agent Loop (Java Order Service)

This is a **new demo alongside** the original discount-calculator loop. The existing root files remain unchanged.

## Architecture

Python orchestrator -> fresh Kiro Developer session (edits Java source) -> fresh Kiro QA Reviewer session (read-only by prompt) -> independent Java acceptance gate -> repeat with feedback if either fails.

**Important:** Python is still deterministic orchestration, not a third AI agent. The two Kiro sessions play distinct AI roles. AI QA approval is necessary but insufficient: the Java gate must also pass.

## Requirements
- Python 3.9+, JDK 17+ (Java record), authenticated `kiro-cli`
- Disposable local checkout, no credentials or sensitive files

## Run on macOS

```bash
git switch feature/multi-agent-loop
cd multi-agent
python3 verify.py              # intentionally FAILS initially (different-payload replay)
python3 agent_loop.py --max-rounds 3
cat .loop/summary.json
```

## Scenario

OrderService exposes `create(requestId, itemId, quantity, unitPrice)`.
- Reject blank IDs, nonpositive quantity and negative unit price.
- Repeated same request ID + same payload returns the same order.
- Repeated same request ID + different payload must fail.
- Concurrent same-key requests must never create inconsistent orders.
- Large totals must use safe arithmetic.

The starter implementation has **known flaws**, so the agents have real work to do.
The Java acceptance gate covers validation, idempotency and arithmetic. **It does not establish concurrency correctness on its own**; the QA Reviewer must inspect atomicity. This is a small Java service, **not yet a Spring Boot REST API**. HTTP endpoints can be added as a separate stage.

## Evidence and limitations

`.loop/developer-NN.log`, `.loop/qa-NN.log`, `.loop/summary.json` are created during execution.
The QA agent is instructed not to edit code, but the tool permission grants filesystem write capability; this is **not an enforced read-only role**. The guard restores only explicitly protected files and is not a sandbox. Run in a disposable directory. AI responses are nondeterministic and may approve flawed code. Never claim that a simulated or unexecuted run is real evidence.
