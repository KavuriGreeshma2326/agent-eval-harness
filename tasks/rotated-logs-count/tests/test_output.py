import json
import sys

EXPECTED = {
    "/api/orders": 5,
    "/api/payments": 5,
    "/api/search": 3,
    "/api/users": 2
}

try:
    with open("/app/errors_by_path.json") as f:
        data = json.load(f)
except FileNotFoundError:
    print("FAIL: /app/errors_by_path.json not found")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"FAIL: invalid JSON: {e}")
    sys.exit(1)

if data != EXPECTED:
    print(f"FAIL: expected {EXPECTED}, got {data}")
    sys.exit(1)

print("PASS")
sys.exit(0)
