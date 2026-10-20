#!/usr/bin/env python3
"""Independent acceptance gate; no AI verdict can override this result."""
import pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parent
build = root / ".build"
build.mkdir(exist_ok=True)
for command in (
    ["javac", "-d", str(build), str(root / "src/OrderService.java"), str(root / "tests/OrderServiceTest.java")],
    ["java", "-cp", str(build), "OrderServiceTest"],
):
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"QA GATE ERROR: {exc}")
        sys.exit(2)
    print(result.stdout + result.stderr, end="")
    if result.returncode:
        sys.exit(result.returncode)
