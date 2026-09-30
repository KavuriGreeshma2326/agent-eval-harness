import subprocess
import sys

CASES = {
    "/app/invoices/sample.csv": "30.77",
    "/tests/hidden/inv_a.csv": "3.38",
    "/tests/hidden/inv_b.csv": "58.40",
    "/tests/hidden/inv_c.csv": "167.22",
}

failed = False
for path, expected in CASES.items():
    try:
        r = subprocess.run(["python3", "/app/invoice.py", path],
                           capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        print(f"FAIL: {path}: timed out")
        failed = True
        continue
    got = r.stdout.strip()
    if r.returncode != 0 or got != expected:
        print(f"FAIL: {path}: expected {expected!r}, got {got!r} (exit {r.returncode}) {r.stderr.strip()[-200:]}")
        failed = True

if failed:
    sys.exit(1)
print("PASS")
sys.exit(0)
