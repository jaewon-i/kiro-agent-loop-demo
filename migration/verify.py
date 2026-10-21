#!/usr/bin/env python3
"""QA Gate: compiles every source file and runs the behavior tests. No AI involved."""
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BUILD = ROOT / '.build'
shutil.rmtree(BUILD, ignore_errors=True)
BUILD.mkdir()
sources = [str(p) for p in sorted((ROOT / 'src').glob('*.java'))] + [str(ROOT / 'tests/BehaviorTest.java')]
for cmd in (['javac', '-nowarn', '-d', str(BUILD)] + sources, ['java', '-cp', str(BUILD), 'BehaviorTest']):
    try:
        r = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f'QA GATE ERROR: {e}')
        sys.exit(2)
    print(r.stdout, end='', flush=True)
    if r.returncode:
        sys.exit(r.returncode)
