#!/usr/bin/env python3
"""Kiro Developer <-> Kiro QA review loop with independent deterministic gate.

Run only in a disposable checkout without credentials. This is an orchestrator,
not a secure sandbox. Each agent invocation is a fresh Kiro CLI session.
"""
import argparse
import datetime
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
STATE = ROOT / ".loop"
SRC = ROOT / "src/OrderService.java"
PROTECTED = [ROOT / "verify.py", ROOT / "tests/OrderServiceTest.java", ROOT / "agent_loop.py"]
DEV = """You are Developer Agent. Work ONLY in multi-agent/src/OrderService.java.
Implement a reliable, thread-safe idempotent order creation service. Keep the public
API compatible with the tests. Reject reused request IDs with different payloads,
and handle total calculations without overflow. Do not edit any tests, scripts,
or other files. You cannot use shell tools. Here is QA feedback and gate output:
{feedback}
Make the smallest correct change, then summarize it.
"""
QA = """You are an independent QA Reviewer Agent. Review ONLY the source file
multi-agent/src/OrderService.java against these requirements: request validation,
idempotency, same key/different payload rejection, thread safety under concurrent
calls, arithmetic safety. Do not edit any source code or tests. Do not use shell.
Return ONLY valid JSON, with keys "approved" (boolean), "findings" (array of
specific strings). Do not wrap in markdown. Approve only if no substantive
defects remain. This is a review, not the final acceptance gate.
"""
def invoke(prompt, timeout):
    exe = shutil.which("kiro-cli")
    if not exe:
        raise RuntimeError("kiro-cli not found on PATH")
    return subprocess.run(
        [exe, "chat", "--no-interactive", "--trust-tools=fs_read,fs_write", prompt],
        cwd=ROOT.parent, text=True, capture_output=True, timeout=timeout,
    )
def gate():
    result = subprocess.run([sys.executable, "verify.py"], cwd=ROOT,
                            capture_output=True, text=True, timeout=90)
    return result.returncode == 0, (result.stdout + result.stderr)[-6000:]
def parse_review(output):
    # Kiro may prepend tool traces. Require an unambiguous JSON object.
    import re
    candidates = re.findall(r'\{[^{}]*"approved"\s*:\s*(?:true|false)[^{}]*\}', output, re.S)
    for candidate in reversed(candidates):
        try:
            value = json.loads(candidate)
            if type(value.get("approved")) is bool and isinstance(value.get("findings"), list):
                return value
        except (ValueError, TypeError):
            pass
    return {"approved": False, "findings": ["QA response was not parseable JSON; review required"]}
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.max_rounds <= 10 or args.timeout < 10:
        parser.error("max-rounds must be 1..10; timeout >= 10")
    STATE.mkdir(exist_ok=True)
    feedback = "Initial implementation: inspect source and meet all requirements."
    history = []
    for n in range(1, args.max_rounds + 1):
        print(f"\n=== ROUND {n}: Developer ===", flush=True)
        snapshot = {p: p.read_bytes() for p in PROTECTED}
        before = SRC.read_bytes()
        try:
            dev = invoke(DEV.format(feedback=feedback), args.timeout)
            (STATE / f"developer-{n:02}.log").write_text(dev.stdout + dev.stderr)
            if dev.returncode:
                raise RuntimeError(f"Developer exited {dev.returncode}")
            if any(p.read_bytes() != data for p, data in snapshot.items()):
                for p, data in snapshot.items(): p.write_bytes(data)
                raise RuntimeError("Protected file changed; restored protected files")
            print(f"Developer changed source: {SRC.read_bytes() != before}")
            print(f"=== ROUND {n}: QA Reviewer ===", flush=True)
            qa = invoke(QA, args.timeout)
            (STATE / f"qa-{n:02}.log").write_text(qa.stdout + qa.stderr)
            if qa.returncode:
                raise RuntimeError(f"QA exited {qa.returncode}")
            if any(p.read_bytes() != data for p, data in snapshot.items()):
                for p, data in snapshot.items(): p.write_bytes(data)
                raise RuntimeError("Protected file changed; restored protected files")
            review = parse_review(qa.stdout)
            passed, output = gate()
            print(f"QA approved={review['approved']} findings={review['findings']}")
            print(f"Independent gate={'PASS' if passed else 'FAIL'}\n{output}", flush=True)
            entry = {"round": n, "qa": review, "gate_pass": passed, "gate_output": output,
                     "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            history.append(entry)
            (STATE / "summary.json").write_text(json.dumps(history, indent=2))
            if review["approved"] and passed:
                print("SUCCESS: both AI review and independent acceptance gate passed.")
                return 0
            feedback = "QA findings:\n" + "\n".join(map(str, review["findings"])) + "\nGate:\n" + output
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
            print(f"STOP: {exc}", file=sys.stderr)
            return 2
    print("STOP: max rounds reached without both approvals.")
    return 1
if __name__ == "__main__":
    sys.exit(main())
