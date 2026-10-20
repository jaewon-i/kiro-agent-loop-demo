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
    a = ap.parse_args()
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
    if a.provider == 'mock':
        log('NOTE: mock is a scripted simulation, not an AI run.')
    else:
        log('WARNING: live agent edits local files. Use a disposable repo with no secrets.')
    if a.inject_fault:
        log('NOTE: --inject-fault is an explicit demo mode. The iteration-1 failure is injected '
            'by the controller, not made by the AI.')

    ok, feedback = qa_gate()
    log(f'\n[QA GATE] initial: {"PASS" if ok else "FAIL"}')
    log(feedback.rstrip())
    summary = {'provider': a.provider, 'inject_fault': a.inject_fault, 'started': now(),
               'initial_qa': ok, 'iterations': []}
    if ok:
        log('Nothing to do: QA Gate already passes.')
        return finish(summary, 'ALREADY_PASSING', 0)

    for i in range(1, a.max_iterations + 1):
        log(f'\n[LOOP {i}/{a.max_iterations}] starting NEW {a.provider} session (no human input)')
        protected_before = {p: p.read_bytes() for p in PROTECTED}
        src_before = SRC.read_text()
        started = time.time()
        rc, _ = invoke_agent(a.provider, BASE_PROMPT.format(feedback=feedback.strip()),
                             a.timeout, i, STATE / f'agent-{i:02d}.log')
        elapsed = round(time.time() - started, 1)
        log(f'[AGENT] session ended: exit={rc} ({elapsed}s). Agent claim is NOT trusted; verifying...')

        tampered = [str(p.relative_to(ROOT)) for p, b in protected_before.items() if p.read_bytes() != b]
        if tampered:
            for p, b in protected_before.items():
                p.write_bytes(b)
            log(f'[GUARDRAIL] protected files modified {tampered}; restored. STOP.')
            summary['iterations'].append({'iteration': i, 'agent_exit': rc, 'tampered': tampered})
            return finish(summary, 'GUARDRAIL_STOP', 3)

        # Diff of the AGENT's own change (recorded before any demo fault injection).
        diff = unified_diff(src_before, SRC.read_text())
        (STATE / f'diff-{i:02d}.patch').write_text(diff)

        injected = False
        if a.inject_fault and i == 1:
            SRC.write_text(FAULT_SOURCE)
            injected = True
            log('[FAULT INJECTION] demo controller deliberately removed price validation '
                '(this failure is NOT the AI\'s).')
        ok, feedback = qa_gate()
        log(f'[QA GATE] {"PASS" if ok else "FAIL"}')
        log(feedback.rstrip())
        rec = {'iteration': i, 'provider': a.provider, 'agent_exit': rc, 'agent_seconds': elapsed,
               'fault_injected': injected, 'source_changed': bool(diff), 'qa_pass': ok,
               'qa_output': feedback, 'timestamp': now()}
        (STATE / f'iteration-{i:02d}.json').write_text(json.dumps(rec, indent=2))
        summary['iterations'].append(rec)

        if ok:
            log(f'\nSUCCESS: QA Gate passed on iteration {i}. Controller stops the loop.')
            return finish(summary, 'PASS', 0)
        if rc != 0:
            log('[STOP] agent session failed (tool/auth/timeout). Not retrying.')
            return finish(summary, 'AGENT_ERROR', 2)
        log('[LOOP] QA failed -> feeding failure log into a NEW session')

    log('\n[STOP] maximum outer iterations reached without PASS.')
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
    return code


if __name__ == '__main__':
    sys.exit(main())
