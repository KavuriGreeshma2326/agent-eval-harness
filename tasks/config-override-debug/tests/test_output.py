import hashlib
import json
import subprocess
import sys

APP_SHA256 = "6e9f8ae68ee2ec944667e362767453b09f95736048860606169e138f15478a17"
EXPECTED = {
    "host": "0.0.0.0",
    "log_file": "/var/log/app.log",
    "log_level": "debug",
    "port": 8080,
    "workers": 4,
}

try:
    digest = hashlib.sha256(open("/app/app.py", "rb").read()).hexdigest()
except FileNotFoundError:
    print("FAIL: /app/app.py is missing")
    sys.exit(1)
if digest != APP_SHA256:
    print("FAIL: /app/app.py was modified")
    sys.exit(1)

r = subprocess.run(["python3", "/app/app.py", "--print-config"], capture_output=True, text=True, timeout=30)
if r.returncode != 0:
    print(f"FAIL: app.py --print-config exited {r.returncode}: {r.stderr.strip()[-300:]}")
    sys.exit(1)
try:
    config = json.loads(r.stdout)
except json.JSONDecodeError:
    print(f"FAIL: could not parse config output: {r.stdout[:300]}")
    sys.exit(1)

if config != EXPECTED:
    print(f"FAIL: expected effective config {EXPECTED}, got {config}")
    sys.exit(1)

print("PASS")
sys.exit(0)
