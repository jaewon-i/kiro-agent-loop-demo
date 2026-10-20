#!/usr/bin/env python3
"""Bounded outer loop: independent AI sessions, external verification, durable state."""
import argparse, datetime, json, pathlib, shutil, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parent
STATE=ROOT/'.loop'; STATE.mkdir(exist_ok=True)
SRC=ROOT/'src/DiscountCalculator.java'
TEST=ROOT/'tests/DiscountTest.java'
BASE_PROMPT='''You are an autonomous Java repair agent. Goal: make all tests pass.\nRequirements: discount rate must be in [0,100]; otherwise throw IllegalArgumentException. Preserve valid calculations.\nYou may edit ONLY src/DiscountCalculator.java. Do not modify tests/, verify.py, loop.py, or any other files. Do not remove or weaken tests.\nRead the latest verification output below, inspect the source, make the smallest repair, then stop this agent session. The external controller will independently verify your changes and start a NEW session if needed.\nLatest verification output:\n{feedback}\n'''
def verify():
    try:
        p=subprocess.run([sys.executable,'verify.py'],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
        return p.returncode==0,p.stdout[-5000:]
    except (OSError,subprocess.TimeoutExpired) as e:return False,str(e)
def invoke(provider,prompt,timeout):
    if provider=='mock':
        # deterministic rehearsal: first iteration no fix, second iteration fix
        count=len(list(STATE.glob('iteration-*.json')))
        if count>=1:
            SRC.write_text('''public class DiscountCalculator {\n    public static int discount(int price, int rate) {\n        if (rate < 0 || rate > 100) throw new IllegalArgumentException("invalid rate");\n        return price - (price * rate / 100);\n    }\n}\n''')
        return 0,'Mock agent iteration completed (no external AI invoked).'
    cmd=['kiro-cli','chat','--no-interactive','--trust-all-tools',prompt]
    if not shutil.which(cmd[0]): return 127,f'{cmd[0]} is not installed or not on PATH'
    try:
        p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        return p.returncode,p.stdout[-12000:]
    except subprocess.TimeoutExpired:return 124,'Agent session timed out'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--provider',choices=['mock','kiro'],default='mock');ap.add_argument('--max-iterations',type=int,default=5);ap.add_argument('--timeout',type=int,default=180);ap.add_argument('--reset',action='store_true');a=ap.parse_args()
    if a.reset:
        for p in STATE.glob('*'):p.unlink()
        SRC.write_text('''public class DiscountCalculator {\n    public static int discount(int price, int rate) {\n        // BUG: negative rates and rates >100 are accepted.\n        return price - (price * rate / 100);\n    }\n}\n''')
    if a.max_iterations<1 or a.max_iterations>20:ap.error('--max-iterations must be 1..20')
    if a.timeout<10:ap.error('--timeout must be >= 10')
    if a.provider!='mock':
        print('WARNING: live agents can execute local tools. Run in a disposable, least-privilege workspace, with no secrets.')
        print('Kiro --trust-all-tools trusts all tools; review local sandbox/permission policies before using it.')
    ok,feedback=verify()
    print('INITIAL VERIFY:', 'PASS' if ok else 'FAIL', '\n'+feedback,flush=True)
    if ok:return 0
    for i in range(1,a.max_iterations+1):
        print(f'\n=== OUTER LOOP {i}/{a.max_iterations}: {a.provider} ===',flush=True)
        original_test=TEST.read_bytes(); original_verify=(ROOT/'verify.py').read_bytes();original_loop=(ROOT/'loop.py').read_bytes()
        rc,output=invoke(a.provider,BASE_PROMPT.format(feedback=feedback),a.timeout)
        (STATE/f'agent-{i}.log').write_text(output)
        if TEST.read_bytes()!=original_test or (ROOT/'verify.py').read_bytes()!=original_verify or (ROOT/'loop.py').read_bytes()!=original_loop:
            TEST.write_bytes(original_test);(ROOT/'verify.py').write_bytes(original_verify);(ROOT/'loop.py').write_bytes(original_loop)
            print('GUARDRAIL: protected files modified; restored; stopping.',flush=True)
            return 3
        ok,feedback=verify()
        result={'iteration':i,'provider':a.provider,'agent_exit':rc,'verified':ok,'verification_output':feedback,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        (STATE/f'iteration-{i:02d}.json').write_text(json.dumps(result,indent=2))
        print(f'AGENT EXIT={rc}; VERIFY={"PASS" if ok else "FAIL"}\n{feedback}',flush=True)
        if ok:
            print('SUCCESS: independently verified. STOP LOOP.',flush=True);return 0
        if rc!=0:
            print('Agent failed; stopping instead of retrying tool/auth errors.',flush=True);return 2
    print('STOP: maximum outer iterations reached.',flush=True);return 1
if __name__=='__main__':sys.exit(main())
