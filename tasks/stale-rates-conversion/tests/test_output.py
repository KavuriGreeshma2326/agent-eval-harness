import json
import sys

# Computed with the rates dated 2026-09-15 (rates.json).
EXPECTED = {
    "BK-101": 1086.22,
    "BK-102": 4171.83,
    "EL-201": 21306.5,
    "EL-202": 2244.15,
    "HM-301": 749.0,
    "HM-302": 731.68,
    "TY-401": 704.82,
    "TY-402": 2145.51
}

try:
    with open("/app/prices_inr.json") as f:
        data = json.load(f)
except FileNotFoundError:
    print("FAIL: /app/prices_inr.json not found")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"FAIL: invalid JSON: {e}")
    sys.exit(1)

if set(data) != set(EXPECTED):
    print(f"FAIL: expected skus {sorted(EXPECTED)}, got {sorted(data)}")
    sys.exit(1)

failed = False
for sku, expected in EXPECTED.items():
    got = data[sku]
    if not isinstance(got, (int, float)) or abs(got - expected) > 0.001:
        print(f"FAIL: {sku}: expected {expected}, got {got!r}")
        failed = True

if failed:
    sys.exit(1)
print("PASS")
sys.exit(0)
