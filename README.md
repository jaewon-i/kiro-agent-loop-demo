# Persistent autonomous Agent Loop — presentation demo

## Concept
An **outer controller** independently checks tests, invokes a **fresh AI CLI process** after failures, records results to `.loop/`, and stops on success or a hard limit. The CLI's own internal tool-use loop is different from this outer loop.

## Requirements
- Python 3.9+
- JDK 11+ (`java`, `javac` on PATH)
- For real AI mode: authenticated `kiro-cli`, with permission to use local files and tools

No Maven, pip packages, or network are required for mock rehearsal.

## Commands
```bash
python3 verify.py                          # should FAIL initially
python3 loop.py --provider mock --reset     # deterministic two-iteration rehearsal
python3 loop.py --provider kiro --reset --max-iterations 5
python3 loop.py --provider kiro --reset --max-iterations 5 --inject-fault   # explicit demo mode
```
Each English status line is followed by a Korean explanation line (`↳ …`) saying what happened and why; add `--no-ko` to hide them (e.g. for screenshots matching the slides).

Kiro is invoked as `kiro-cli chat --no-interactive --trust-tools=fs_read,fs_write "<prompt>"` (verified with kiro-cli 2.32.0 on macOS). Shell and other tools are denied automatically in non-interactive mode.

`--inject-fault` is a labeled demo mode: after loop 1 the **controller** deliberately removes the price check, so the QA Gate fails and a new Kiro session is started automatically. The failure is not the AI's; say so in the presentation.

Evidence per run: `.loop/summary.json`, `iteration-NN.json`, `agent-NN.log`, `diff-NN.patch`. Captured real runs: `docs/captures/`.
macOS: use `python3`. Check `java -version`, `javac -version`, `python3 --version`, and `kiro-cli --version`.

## What to narrate
1. Initial test fails because rates -1 and 101 are accepted.
2. External controller launches one AI session, which is allowed to edit only `src/DiscountCalculator.java`.
3. Controller runs tests **itself**, saves `.loop/iteration-NN.json`, and if needed starts a new AI session with the last failure output.
4. Test PASS is the only success signal. An AI claiming success is not enough.
5. A timeout, maximum iterations, or tool error ends the run.

## Safety / limitations
- `--provider mock` is a **scripted simulation**, not an AI run. Use it to rehearse the UI and fallback when Wi-Fi/auth fails.
- The real Kiro mode was verified on 2026-10-20 (macOS, kiro-cli 2.32.0); see `docs/captures/`.
- The example's protected-file guard checks only three exact files and restores them if changed; it is **not a security sandbox**. Run live AI only in a disposable repository/VM/container with scoped permissions, no secrets, and ideally network controls. Kiro `--trust-all-tools` is permissive. Avoid production repositories.
- Python controller state survives across iterations in `.loop/`; AI sessions themselves are fresh. To restart the controller after a crash, rerun (it re-verifies), but iteration counts restart. This is a **persistent, bounded outer-loop demonstration**, not a production daemon or queue.
- If `javac` is missing, install a JDK (a JRE is insufficient).

## References
- https://kiro.dev/docs/cli/reference/cli-commands/
- https://kiro.dev/docs/cli/headless/
