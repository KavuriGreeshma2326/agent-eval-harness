import hashlib
import subprocess
import sys

TEST_FILE_SHA256 = {'test_cart.py': '5f28a6e8f6b4d9ab78d119436abbdfa963cc1172acf42d40c2212dd889fccc2d', 'test_coupons.py': '01e0fcee7885146e15aaf898d714251993a816063bbffcc928ffb994d92fdb65'}
SEEDS = range(30)

for name, digest in TEST_FILE_SHA256.items():
    try:
        actual = hashlib.sha256(open(f"/app/project/{name}", "rb").read()).hexdigest()
    except FileNotFoundError:
        print(f"FAIL: /app/project/{name} is missing")
        sys.exit(1)
    if actual != digest:
        print(f"FAIL: /app/project/{name} was modified")
        sys.exit(1)

# Each shuffled order runs in a fresh process so no state carries over between runs.
failed_seeds = []
for seed in SEEDS:
    r = subprocess.run(["python3", "/tests/shuffled_run.py", str(seed)],
                       cwd="/app/project", capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        failed_seeds.append(seed)
if failed_seeds:
    print(f"FAIL: suite failed in {len(failed_seeds)} of {len(SEEDS)} shuffled orders (seeds {failed_seeds[:10]})")
    sys.exit(1)

r = subprocess.run(["python3", "/tests/behavior_check.py"], cwd="/app/project",
                   capture_output=True, text=True, timeout=60)
if r.returncode != 0:
    print(f"FAIL: behavior check: {(r.stdout + r.stderr).strip()[-300:]}")
    sys.exit(1)

print("PASS")
sys.exit(0)
