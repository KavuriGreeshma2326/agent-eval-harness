import json
import sys

EXPECTED = {
    "asha": {"sessions": 2, "total_minutes": 49},
    "bilal": {"sessions": 2, "total_minutes": 35},
    "chen": {"sessions": 3, "total_minutes": 65},
}

try:
    with open("/app/sessions.json") as f:
        data = json.load(f)
except FileNotFoundError:
    print("FAIL: /app/sessions.json not found")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"FAIL: invalid JSON: {e}")
    sys.exit(1)

if data != EXPECTED:
    print(f"FAIL: expected {EXPECTED}, got {data}")
    sys.exit(1)

print("PASS")
sys.exit(0)
