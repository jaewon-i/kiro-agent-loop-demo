#!/usr/bin/env python3
"""Bounded Outer Loop controller.

- Each iteration starts a NEW, independent AI session (no --resume).
- The controller runs the QA Gate (verify.py) itself; an AI saying "done" is not success.
- State and evidence are written to .loop/ (per-iteration JSON, agent log, source diff, summary).
- Stops on: QA PASS, max iterations, agent error/timeout, or protected-file tampering.
"""
import argparse
import datetime
import difflib
import json
import pathlib
import shutil
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent
STATE = ROOT / '.loop'
BUILD = ROOT / '.build'
SRC = ROOT / 'src/DiscountCalculator.java'
PROTECTED = [ROOT / 'tests/DiscountTest.java', ROOT / 'verify.py', ROOT / 'loop.py']

BUGGY_SOURCE = '''public class DiscountCalculator {
    public static int discount(int price, int rate) {
        // BUG: negative prices, negative rates and rates > 100 are accepted.
        return price - (price * rate / 100);
    }
}
'''
FIXED_SOURCE = '''public class DiscountCalculator {
    public static int discount(int price, int rate) {
        if (price < 0) throw new IllegalArgumentException("invalid price");
        if (rate < 0 || rate > 100) throw new IllegalArgumentException("invalid rate");
        return price - (price * rate / 100);
    }
}
'''
# Used ONLY by --inject-fault: a deliberate regression (price validation removed).
FAULT_SOURCE = '''public class DiscountCalculator {
    public static int discount(int price, int rate) {
        // [FAULT INJECTION] price validation intentionally removed by the demo controller
        if (rate < 0 || rate > 100) throw new IllegalArgumentException("invalid rate");
        return price - (price * rate / 100);
    }
}
'''

BASE_PROMPT = '''You are an autonomous Java repair agent running in a fresh, non-interactive session.
Goal: make the QA Gate pass.
Requirements for DiscountCalculator.discount(price, rate):
- rate must be within [0, 100], otherwise throw IllegalArgumentException
- price must be >= 0, otherwise throw IllegalArgumentException
- preserve valid calculations (e.g. discount(1000, 10) == 900)
Rules:
- You may edit ONLY src/DiscountCalculator.java. You may read tests/DiscountTest.java for reference.
- Do NOT modify tests/, verify.py, loop.py or any other file. Do not weaken tests.
- You cannot run shell commands; an external controller will compile and test your change.
Make the smallest correct fix, then reply with a one-line summary and stop.
Latest QA Gate output from the external controller:
---
{feedback}
---
'''


def log(msg=''):
    print(msg, flush=True)


KO = True


def ko(msg):
    """Korean explanation line under each English status line (disable with --no-ko)."""
    if KO:
        print('  ↳ ' + msg, flush=True)


def explain_failure(output):
    """Translate the QA Gate failure into plain Korean."""
    import re
    m = re.search(r'price=(-?\d+) rate=(-?\d+)', output)
    if m:
        return f'금액 {int(m.group(1)):,}원 · 할인율 {m.group(2)}% 는 잘못된 입력이라 거부(예외)해야 하는데, 그대로 계산했습니다'
    m = re.search(r'expected=(-?\d+) actual=(-?\d+)', output)
    if m:
        return f'계산 결과가 {int(m.group(1)):,}원이어야 하는데 {int(m.group(2)):,}원이 나왔습니다'
    if 'error:' in output:
        return 'Java 컴파일 오류가 났습니다'
    return '테스트가 실패했습니다 (위 출력 참고)'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def qa_gate():
    """Independent verification. Runs verify.py in a separate process."""
    try:
        p = subprocess.run([sys.executable, 'verify.py'], cwd=ROOT, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        return p.returncode == 0, p.stdout[-5000:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f'QA Gate error: {e}'


def run_streaming(cmd, timeout, log_path):
    """Run cmd, stream output live to the terminal and to log_path; kill on timeout."""
    with open(log_path, 'w') as lf:
        p = subprocess.Popen(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        chunks = []

        def pump():
            for line in p.stdout:
                sys.stdout.write('    │ ' + line)
                sys.stdout.flush()
                lf.write(line)
                chunks.append(line)
        t = threading.Thread(target=pump, daemon=True)
        t.start()
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            rc = 124
            chunks.append('\n[controller] agent session timed out\n')
        t.join(timeout=5)
    return rc, ''.join(chunks)


def invoke_agent(provider, prompt, timeout, iteration, log_path):
    if provider == 'mock':
        # Scripted simulation, NOT an AI: iteration 1 changes nothing, iteration 2 applies the fix.
        if iteration >= 2:
            SRC.write_text(FIXED_SOURCE)
            out = 'Mock agent: applied scripted fix (no external AI invoked).\n'
        else:
            out = 'Mock agent: no change this iteration (no external AI invoked).\n'
        log_path.write_text(out)
        log('    │ ' + out.rstrip())
        return 0, out
    exe = shutil.which('kiro-cli')
    if not exe:
        return 127, 'kiro-cli is not installed or not on PATH'
    # Least privilege: only file read/write tools are auto-approved. Shell etc. are denied
    # automatically in --no-interactive mode (verified with kiro-cli 2.32.0).
    cmd = [exe, 'chat', '--no-interactive', '--trust-tools=fs_read,fs_write', prompt]
    log('    $ kiro-cli chat --no-interactive --trust-tools=fs_read,fs_write "<prompt + QA feedback>"')
    ko('Kiro 작업 중… 아래 │ 줄이 Kiro 출력입니다 (보통 15~30초). 허용 도구: 파일 읽기/쓰기만')
    return run_streaming(cmd, timeout, log_path)


def unified_diff(before, after):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        'a/src/DiscountCalculator.java', 'b/src/DiscountCalculator.java'))


def main():
    ap = argparse.ArgumentParser(description='Bounded Outer Loop controller (demo)')
    ap.add_argument('--provider', choices=['mock', 'kiro'], default='mock')
    ap.add_argument('--max-iterations', type=int, default=5)
    ap.add_argument('--timeout', type=int, default=300, help='seconds per agent session')
    ap.add_argument('--reset', action='store_true', help='clear .loop/.build and restore the buggy source')
    ap.add_argument('--inject-fault', action='store_true',
                    help='DEMO ONLY: after iteration 1, the controller deliberately removes price '
                         'validation before the QA Gate, to show FAIL -> automatic new session -> PASS')
    ap.add_argument('--no-ko', action='store_true', help='hide the Korean explanation lines')
    a = ap.parse_args()
    global KO
    KO = not a.no_ko
    if not 1 <= a.max_iterations <= 20:
        ap.error('--max-iterations must be 1..20')
    if a.timeout < 10:
        ap.error('--timeout must be >= 10')
    if a.inject_fault and a.max_iterations < 2:
        ap.error('--inject-fault needs --max-iterations >= 2')

    if a.reset:
        shutil.rmtree(STATE, ignore_errors=True)
        shutil.rmtree(BUILD, ignore_errors=True)
        SRC.write_text(BUGGY_SOURCE)
    STATE.mkdir(exist_ok=True)

    log('=' * 64)
    log(f'OUTER LOOP CONTROLLER  provider={a.provider}  max={a.max_iterations}  '
        f'timeout={a.timeout}s  inject_fault={a.inject_fault}')
    log('=' * 64)
    ko('이 Outer Loop는 할인 계산기 버그를 에이전트(Kiro)에게 고치게 하고, 결과는 컨트롤러가 직접 테스트해서 판정합니다.')
    ko(f'목표: 테스트 7개 모두 PASS. 최대 {a.max_iterations}번 loop, 세션당 {a.timeout}초. 사람은 중간에 아무것도 입력하지 않습니다.')
    if a.provider == 'mock':
        log('NOTE: mock is a scripted simulation, not an AI run.')
        ko('주의: mock은 AI가 아니라 미리 써 둔 스크립트입니다 (Loop 1은 아무것도 안 하고, Loop 2에서 고침).')
    else:
        log('WARNING: live agent edits local files. Use a disposable repo with no secrets.')
        ko('실제 Kiro가 파일을 수정합니다. 비밀정보가 없는 저장소에서만 실행하세요.')
    if a.inject_fault:
        log('NOTE: --inject-fault is an explicit demo mode. The iteration-1 failure is injected '
            'by the controller, not made by the AI.')
        ko('데모 모드: Loop 1에서 에이전트가 고친 뒤 컨트롤러가 일부러 가격 검사를 지웁니다. 이 실패는 AI의 실패가 아닙니다.')

    ok, feedback = qa_gate()
    log(f'\n[QA GATE] initial: {"PASS" if ok else "FAIL"}')
    log(feedback.rstrip())
    ko('시작 상태: 테스트 PASS — 고칠 것이 없습니다.' if ok else f'시작 상태: 테스트 FAIL — {explain_failure(feedback)}. (일부러 넣어 둔 버그)')
    summary = {'provider': a.provider, 'inject_fault': a.inject_fault, 'started': now(),
               'initial_qa': ok, 'iterations': []}
    if ok:
        log('Nothing to do: QA Gate already passes.')
        return finish(summary, 'ALREADY_PASSING', 0)

    for i in range(1, a.max_iterations + 1):
        log(f'\n[LOOP {i}/{a.max_iterations}] starting NEW {a.provider} session (no human input)')
        ko(f'Loop {i}: 새 {"Kiro" if a.provider == "kiro" else "mock(스크립트)"} 세션을 엽니다. 프롬프트 = 요구사항 + 방금 테스트 실패 내용'
           + (' (이전 세션 기억은 없고, 넘겨준 실패 내용이 유일한 기억)' if i > 1 else ''))
        protected_before = {p: p.read_bytes() for p in PROTECTED}
        src_before = SRC.read_text()
        started = time.time()
        rc, _ = invoke_agent(a.provider, BASE_PROMPT.format(feedback=feedback.strip()),
                             a.timeout, i, STATE / f'agent-{i:02d}.log')
        elapsed = round(time.time() - started, 1)
        log(f'[AGENT] session ended: exit={rc} ({elapsed}s). Agent claim is NOT trusted; verifying...')
        ko(f'세션 종료 ({elapsed}초). 에이전트가 "고쳤다"고 해도 믿지 않고, 컨트롤러가 테스트를 직접 다시 돌립니다.')

        tampered = [str(p.relative_to(ROOT)) for p, b in protected_before.items() if p.read_bytes() != b]
        if tampered:
            for p, b in protected_before.items():
                p.write_bytes(b)
            log(f'[GUARDRAIL] protected files modified {tampered}; restored. STOP.')
            ko(f'에이전트가 테스트/검증기 파일 {tampered} 을(를) 건드렸습니다(시험지 고치기). 원래대로 복원하고 즉시 멈춥니다.')
            summary['iterations'].append({'iteration': i, 'agent_exit': rc, 'tampered': tampered})
            return finish(summary, 'GUARDRAIL_STOP', 3)

        # Diff of the AGENT's own change (recorded before any demo fault injection).
        diff = unified_diff(src_before, SRC.read_text())
        (STATE / f'diff-{i:02d}.patch').write_text(diff)
        ko('에이전트가 DiscountCalculator.java 를 수정했습니다 (변경 내용은 .loop/diff 파일에 기록).' if diff
           else '에이전트가 코드를 바꾸지 않았습니다.')

        injected = False
        if a.inject_fault and i == 1:
            SRC.write_text(FAULT_SOURCE)
            injected = True
            log('[FAULT INJECTION] demo controller deliberately removed price validation '
                '(this failure is NOT the AI\'s).')
            ko('데모 모드: 컨트롤러가 일부러 가격 검사 코드를 지웠습니다. 다음 테스트 실패는 AI 탓이 아닙니다.')
        ok, feedback = qa_gate()
        log(f'[QA GATE] {"PASS" if ok else "FAIL"}')
        log(feedback.rstrip())
        ko('판정: 테스트 7개 모두 PASS.' if ok else f'판정: FAIL — {explain_failure(feedback)}.')
        rec = {'iteration': i, 'provider': a.provider, 'agent_exit': rc, 'agent_seconds': elapsed,
               'fault_injected': injected, 'source_changed': bool(diff), 'qa_pass': ok,
               'qa_output': feedback, 'timestamp': now()}
        (STATE / f'iteration-{i:02d}.json').write_text(json.dumps(rec, indent=2))
        summary['iterations'].append(rec)

        if ok:
            log(f'\nSUCCESS: QA Gate passed on iteration {i}. Controller stops the loop.')
            ko(f'테스트가 통과했으니 컨트롤러가 loop를 멈춥니다 (Loop {i}에서 종료).')
            return finish(summary, 'PASS', 0)
        if rc != 0:
            log('[STOP] agent session failed (tool/auth/timeout). Not retrying.')
            ko('에이전트 세션이 오류/인증 문제/시간 초과로 실패했습니다. 재시도하지 않고 멈춥니다.')
            return finish(summary, 'AGENT_ERROR', 2)
        log('[LOOP] QA failed -> feeding failure log into a NEW session')
        ko('실패 내용을 다음 프롬프트에 담아 새 세션을 자동으로 시작합니다 (사람 입력 없음).')

    log('\n[STOP] maximum outer iterations reached without PASS.')
    ko(f'최대 {a.max_iterations}번 loop를 돌았지만 통과하지 못해 멈춥니다 (무한 반복 방지).')
    return finish(summary, 'MAX_ITERATIONS', 1)


def finish(summary, result, code):
    summary.update({'result': result, 'finished': now(), 'iteration_count': len(summary['iterations'])})
    (STATE / 'summary.json').write_text(json.dumps(summary, indent=2))
    log('\n' + '=' * 64)
    log(f'RESULT={result}  iterations={summary["iteration_count"]}  exit={code}')
    for r in summary['iterations']:
        tag = ' (fault injected)' if r.get('fault_injected') else ''
        log(f'  loop {r["iteration"]}: agent_exit={r.get("agent_exit")} '
            f'qa={"PASS" if r.get("qa_pass") else "FAIL"}{tag}')
    log('Evidence: .loop/summary.json, iteration-NN.json, agent-NN.log, diff-NN.patch')
    log('=' * 64)
    ko({'PASS': f'결과: 성공. 세션 {summary["iteration_count"]}개로 테스트 7개 모두 통과.',
        'ALREADY_PASSING': '결과: 이미 통과 상태라 아무것도 하지 않았습니다 (--reset 으로 버그 코드부터 시작).',
        'MAX_ITERATIONS': '결과: 최대 반복 횟수에 도달해 실패로 끝났습니다.',
        'AGENT_ERROR': '결과: 에이전트 세션 오류로 멈췄습니다.',
        'GUARDRAIL_STOP': '결과: 보호 파일 변조를 감지해 멈췄습니다.'}.get(result, result))
    ko('loop별 기록과 코드 변경(diff)은 .loop/ 폴더에 있습니다.')
    return code


if __name__ == '__main__':
    sys.exit(main())
