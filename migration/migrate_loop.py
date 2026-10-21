#!/usr/bin/env python3
"""Incremental migration Outer Loop (control-loop style, after Kyle Mistele's talk).

  set point  : 0 source files using the legacy date API, behavior tests PASS
  sensor     : measure.py (legacy usage per file) + verify.py (compile + behavior tests)
  controller : this file — picks ONE remaining file, starts a NEW agent session, decides accept/revert
  actuator   : Kiro CLI (or the scripted mock) — migrates that one file

Each iteration is a small, reviewable change. A change is merged only if the gate passes AND the
sensor no longer sees legacy usage in that file; otherwise it is reverted and retried with the
failure output. A file that keeps failing is left for a human (the loop does not force it).
"""
import argparse
import datetime
import difflib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent
SRC, LEGACY, TESTS = ROOT / 'src', ROOT / 'legacy', ROOT / 'tests'
REHEARSAL = ROOT / 'rehearsal'
STATE = ROOT / '.loop'
WORK = pathlib.Path(tempfile.gettempdir()) / 'migration-ws-unset'  # replaced per iteration
PROTECTED = [TESTS / 'BehaviorTest.java', ROOT / 'verify.py', ROOT / 'measure.py', ROOT / 'migrate_loop.py']
sys.path.insert(0, str(ROOT))
import measure  # noqa: E402

PROMPT = '''You are a Java migration agent in a fresh, non-interactive session.
Task: migrate ONLY src/{target} from the legacy date API (java.util.Date, Calendar, TimeZone,
java.text.SimpleDateFormat/DateFormat) to java.time.
Rules:
- Edit ONLY src/{target}. Do not touch other files. Keep the public class name and method signatures.
- Behavior must stay exactly the same: same output strings, same time zones, same rounding/precision,
  same IllegalArgumentException cases. tests/BehaviorTest.java pins the expected behavior (read it).
- Do not leave any legacy date API in the file, not even in imports.
- You cannot run shell commands. An external controller compiles, tests and measures your change.
Make the change, then reply with a one-line summary and stop.
{feedback}'''


def log(msg=''):
    print(msg, flush=True)


KO = True


def ko(msg):
    """Korean explanation line shown under each English status line (disable with --no-ko)."""
    if KO:
        print('  ↳ ' + msg, flush=True)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def gate():
    try:
        p = subprocess.run([sys.executable, 'verify.py'], cwd=ROOT, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        return p.returncode == 0, p.stdout[-4000:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f'QA Gate error: {e}'


def fresh_workspace():
    """Agent works on a copy (src + tests only) OUTSIDE the repo, so it cannot find the real sources.
    The controller decides what comes back."""
    global WORK
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK = pathlib.Path(tempfile.mkdtemp(prefix='migration-ws-'))
    shutil.copytree(SRC, WORK / 'src')
    shutil.copytree(TESTS, WORK / 'tests')


def run_streaming(cmd, cwd, timeout, log_path):
    with open(log_path, 'w') as lf:
        p = subprocess.Popen(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)

        def pump():
            for line in p.stdout:
                sys.stdout.write('    │ ' + line)
                sys.stdout.flush()
                lf.write(line)
        t = threading.Thread(target=pump, daemon=True)
        t.start()
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            rc = 124
            lf.write('\n[controller] agent session timed out\n')
            log('    │ [controller] agent session timed out')
        t.join(timeout=5)
    return rc


def invoke_agent(provider, target, attempt, feedback, timeout, log_path):
    if provider == 'mock':
        # Scripted rehearsal, NOT an AI: copies reference solutions. ShippingSchedule's first
        # attempt deliberately forgets to wrap DateTimeParseException, to rehearse a retry.
        dest = WORK / 'src' / target
        text = (REHEARSAL / target).read_text()
        if target == 'ShippingSchedule.java' and attempt == 1:
            text = text.replace('catch (DateTimeParseException e)', 'catch (IllegalStateException e)')
            note = 'scripted mistake: parse exception not wrapped'
        else:
            note = 'scripted reference solution'
        dest.write_text(text)
        out = f'Mock agent: wrote {target} ({note}). No AI invoked.\n'
        log_path.write_text(out)
        log('    │ ' + out.rstrip())
        return 0
    exe = shutil.which('kiro-cli')
    if not exe:
        log_path.write_text('kiro-cli is not installed or not on PATH\n')
        return 127
    fb = f'Previous attempt was REVERTED by the controller. Fix this:\n---\n{feedback}\n---' if feedback else ''
    prompt = PROMPT.format(target=target, feedback=fb)
    log('    $ kiro-cli chat --no-interactive --trust-tools=fs_read,fs_write "<migrate one file>"')
    ko('Kiro 작업 중… 아래 │ 줄이 Kiro 출력입니다 (보통 20~30초)')
    return run_streaming([exe, 'chat', '--no-interactive', '--trust-tools=fs_read,fs_write', prompt],
                         WORK, timeout, log_path)


def diff(before, after, name):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        f'a/src/{name}', f'b/src/{name}'))


def failing_lines_for(target, output):
    cls = target.removesuffix('.java')
    lines = [ln for ln in output.splitlines() if ln.strip().startswith(f'- {cls}:') or 'error:' in ln]
    return '\n'.join(lines) or output[-1500:]


def main():
    ap = argparse.ArgumentParser(description='Incremental migration Outer Loop (demo)')
    ap.add_argument('--provider', choices=['mock', 'kiro'], default='mock')
    ap.add_argument('--max-iterations', type=int, default=12, help='total agent sessions')
    ap.add_argument('--max-attempts', type=int, default=2, help='attempts per file before leaving it to a human')
    ap.add_argument('--timeout', type=int, default=300, help='seconds per agent session')
    ap.add_argument('--reset', action='store_true', help='restore legacy sources and clear .loop/')
    ap.add_argument('--no-ko', action='store_true', help='hide the Korean explanation lines')
    a = ap.parse_args()
    global KO
    KO = not a.no_ko
    if not 1 <= a.max_iterations <= 30 or not 1 <= a.max_attempts <= 5 or a.timeout < 10:
        ap.error('limits: max-iterations 1..30, max-attempts 1..5, timeout >= 10')

    if a.reset:
        shutil.rmtree(STATE, ignore_errors=True)
        for f in SRC.glob('*.java'):
            f.unlink()
        for f in LEGACY.glob('*.java'):
            shutil.copy(f, SRC / f.name)
    STATE.mkdir(exist_ok=True)

    log('=' * 66)
    log(f'MIGRATION LOOP  provider={a.provider}  max_iterations={a.max_iterations}  '
        f'max_attempts/file={a.max_attempts}  timeout={a.timeout}s')
    log('set point: 0 files on legacy date API, behavior tests PASS')
    log('=' * 66)
    ko('이 Outer Loop는 옛 날짜 API를 쓰는 Java 파일을 loop 한 번에 하나씩 java.time으로 옮깁니다.')
    ko('목표: 옛 날짜 API를 쓰는 파일 0개 + 동작 테스트 28개 PASS. 사람은 중간에 아무것도 입력하지 않습니다.')
    if a.provider == 'mock':
        log('NOTE: mock is a scripted rehearsal, not an AI run.')
        ko('주의: mock은 AI가 아니라 미리 써 둔 스크립트입니다 (배송일 파일 1회차에 일부러 실수함).')
    else:
        log('WARNING: live agent edits files. Use a disposable checkout with no secrets.')
        ko('실제 Kiro가 파일을 수정합니다. 비밀정보가 없는 저장소에서만 실행하세요.')

    ok, out = gate()
    m = measure.measure()
    log(f'\n[SENSOR] legacy files {len(m["remaining"])}/{m["total"]} · tests {"PASS" if ok else "FAIL"}')
    ko(f'시작 상태 측정: 옛 날짜 API 파일 {len(m["remaining"])}/{m["total"]}개 남음, 동작 테스트 {"PASS (정상 출발)" if ok else "FAIL"}')
    if not ok:
        log(out.rstrip())
        log('[STOP] baseline tests fail; fix the baseline before migrating.')
        ko('시작 코드부터 테스트가 실패해서 마이그레이션을 시작하지 않습니다.')
        return 2

    trajectory = [len(m['remaining'])]
    summary = {'provider': a.provider, 'started': now(), 'iterations': [], 'trajectory': trajectory,
               'left_for_human': []}
    attempts, feedback = {}, {}
    result, code = 'MAX_ITERATIONS', 1

    for i in range(1, a.max_iterations + 1):
        todo = [f for f in measure.measure()['remaining'] if f not in summary['left_for_human']]
        if not todo:
            break
        target = todo[0]
        attempts[target] = attempts.get(target, 0) + 1
        n = attempts[target]
        log(f'\n[LOOP {i}/{a.max_iterations}] target={target} (attempt {n}/{a.max_attempts}) '
            f'— NEW {a.provider} session, no human input')
        ko(f'Loop {i}: 컨트롤러가 {target} 을(를) 골라 새 세션에 "이 파일 하나만 옮겨라"라고 지시합니다'
           + (f' ({n}번째 시도, 직전 실패 내용 포함)' if n > 1 else ''))

        protected_before = {p: p.read_bytes() for p in PROTECTED}
        fresh_workspace()
        src_before = {p: p.read_bytes() for p in SRC.glob('*.java')}
        before = (SRC / target).read_text()
        t0 = time.time()
        rc = invoke_agent(a.provider, target, n, feedback.get(target), a.timeout, STATE / f'agent-{i:02d}.log')
        secs = round(time.time() - t0, 1)

        tampered = [str(p.relative_to(ROOT)) for p, b in protected_before.items() if p.read_bytes() != b]
        if tampered:
            for p, b in protected_before.items():
                p.write_bytes(b)
            log(f'[GUARDRAIL] protected files modified {tampered}; restored. STOP.')
            ko(f'에이전트가 테스트/센서/컨트롤러 파일 {tampered} 을(를) 건드렸습니다. 원래대로 복원하고 즉시 멈춥니다.')
            result, code = 'GUARDRAIL_STOP', 3
            summary['iterations'].append({'iteration': i, 'target': target, 'tampered': tampered})
            break

        outside = sorted(p.name for p, b in src_before.items() if not p.exists() or p.read_bytes() != b)
        outside += sorted(p.name for p in SRC.glob('*.java') if p not in src_before)
        if outside:
            for p in SRC.glob('*.java'):
                if p not in src_before:
                    p.unlink()
            for p, b in src_before.items():
                p.write_bytes(b)
            log(f'[GUARDRAIL] agent edited the real src/ outside its workspace {outside}; reverted '
                '(only the controller may merge changes).')
            ko(f'에이전트가 작업 폴더 밖의 진짜 src/ {outside} 을(를) 고쳤습니다. 되돌립니다 (반영은 컨트롤러만 할 수 있음).')

        changed = sorted(p.name for p in (WORK / 'src').glob('*.java')
                         if not (SRC / p.name).exists() or p.read_bytes() != (SRC / p.name).read_bytes())
        others = [c for c in changed if c != target]
        after = (WORK / 'src' / target).read_text() if (WORK / 'src' / target).exists() else before
        log(f'[AGENT] exit={rc} ({secs}s) · changed: {", ".join(changed) or "nothing"}'
            + (f' · ignored (not target): {", ".join(others)}' if others else '')
            + '. Agent claim is NOT trusted; measuring...')
        who = 'Kiro' if a.provider == 'kiro' else 'mock(스크립트)'
        ko(f'{who} 세션 종료 ({secs}초). 에이전트가 "다 했다"고 해도 믿지 않고, 컨트롤러가 직접 테스트하고 잽니다.')
        if others:
            ko(f'대상이 아닌 파일 {", ".join(others)} 의 수정은 반영하지 않고 무시합니다.')
        if rc != 0:
            log('[STOP] agent session failed (tool/auth/timeout). Not retrying.')
            ko(f'{who} 세션이 오류/인증 문제/시간 초과로 실패했습니다. 재시도하지 않고 멈춥니다.')
            result, code = 'AGENT_ERROR', 2
            summary['iterations'].append({'iteration': i, 'target': target, 'agent_exit': rc})
            break

        # Merge ONLY the target file, then measure the real tree.
        (SRC / target).write_text(after)
        patch = diff(before, after, target)
        (STATE / f'diff-{i:02d}.patch').write_text(patch)
        ok, out = gate()
        left_in_target = measure.legacy_hits(SRC / target)
        accepted = ok and not left_in_target and bool(patch)

        if accepted:
            remaining = len(measure.measure()['remaining'])
            trajectory.append(remaining)
            log(f'[GATE] tests PASS · sensor: {target} clean → ACCEPT   legacy files {trajectory[-2]} → {remaining}')
            ko(f'판정: 테스트 28개 PASS + {target} 에 옛 날짜 API 없음 → 반영. 남은 파일 {trajectory[-2]}개 → {remaining}개')
            verdict = 'ACCEPT'
        else:
            (SRC / target).write_text(before)
            if not patch:
                reason = 'no change was made to the target file'
            elif not ok:
                reason = 'behavior tests failed:\n' + failing_lines_for(target, out)
            else:
                reason = 'sensor still detects legacy API in the file: ' + ', '.join(left_in_target)
            feedback[target] = reason
            reason_ko = ('대상 파일이 바뀌지 않음' if not patch else
                         '동작 테스트 실패 (동작이 바뀜)' if not ok else
                         '파일에 옛 날짜 API가 아직 남아 있음')
            first = reason.splitlines()[0]
            log(f'[GATE] {"tests FAIL" if not ok else "tests PASS"} · {first} → REVERT')
            for ln in reason.splitlines()[1:6]:
                log('       ' + ln)
            if n >= a.max_attempts:
                summary['left_for_human'].append(target)
                log(f'[LOOP] {target}: {n} failed attempts → left for a human, moving on')
                ko(f'판정: {reason_ko} → 되돌림. {n}번 실패해서 억지로 밀어붙이지 않고 사람에게 넘기고 다음 파일로 갑니다.')
                verdict = 'LEFT_FOR_HUMAN'
            else:
                log('[LOOP] retry the same file in a NEW session with the failure output')
                ko(f'판정: {reason_ko} → 되돌림. 실패 내용을 들고 같은 파일을 새 세션으로 다시 시킵니다.')
                verdict = 'REVERT_RETRY'

        rec = {'iteration': i, 'target': target, 'attempt': n, 'agent_exit': rc, 'agent_seconds': secs,
               'changed_files': changed, 'ignored_files': others, 'gate_pass': ok,
               'legacy_left_in_target': left_in_target, 'verdict': verdict,
               'gate_output': out, 'timestamp': now()}
        (STATE / f'iteration-{i:02d}.json').write_text(json.dumps(rec, indent=2))
        summary['iterations'].append(rec)
    else:
        i = a.max_iterations

    final = measure.measure()['remaining']
    ok, _ = gate()
    if result not in ('GUARDRAIL_STOP', 'AGENT_ERROR'):
        if not final and ok:
            result, code = 'DONE', 0
        elif not [f for f in final if f not in summary['left_for_human']]:
            result, code = 'PARTIAL_NEEDS_HUMAN', 1
    shutil.rmtree(WORK, ignore_errors=True)
    summary.update({'result': result, 'finished': now(), 'final_remaining': final, 'final_tests_pass': ok,
                    'agent_sessions': len(summary['iterations'])})
    (STATE / 'summary.json').write_text(json.dumps(summary, indent=2))

    log('\n' + '=' * 66)
    log(f'RESULT={result}  agent sessions={summary["agent_sessions"]}  exit={code}')
    log(f'legacy files: {" → ".join(map(str, trajectory))}   tests: {"PASS" if ok else "FAIL"}')
    for r in summary['iterations']:
        log(f'  loop {r["iteration"]:>2}: {r["target"]:<26} attempt {r.get("attempt", "-")}  {r.get("verdict", "STOP")}')
    if summary['left_for_human']:
        log(f'left for a human: {", ".join(summary["left_for_human"])}')
    log('Evidence: .loop/summary.json, iteration-NN.json, agent-NN.log, diff-NN.patch')
    log('=' * 66)
    ko({'DONE': f'결과: 완료. 옛 날짜 API 파일 {trajectory[0]}개 → 0개, 동작 테스트 28개 모두 PASS.',
        'PARTIAL_NEEDS_HUMAN': f'결과: 일부 완료. 남은 파일 {", ".join(final)} 은(는) 사람이 확인해야 합니다.',
        'MAX_ITERATIONS': '결과: 최대 반복 횟수에 도달해 멈췄습니다 (목표 미달성).',
        'AGENT_ERROR': '결과: Kiro 세션 오류로 멈췄습니다.',
        'GUARDRAIL_STOP': '결과: 보호 파일 변조를 감지해 멈췄습니다.'}[result])
    ko(f'세션 {summary["agent_sessions"]}개 사용. loop별 기록과 코드 변경(diff)은 .loop/ 폴더에 있습니다.')
    return code


if __name__ == '__main__':
    sys.exit(main())
