import csv
import sys

EXPECTED = [
    ["customer_id", "name", "email", "updated_at"],
    ["C001", "Anitha Rao", "anitha.new@example.com", "2026-09-10 18:40:00"],
    ["C002", "Suresh Babu", "suresh@example.com", "2026-07-21 11:00:00"],
    ["C003", "Ravi Teja", "ravi.teja@example.com", "2026-09-01 07:30:00"],
    ["C004", "Divya Menon", "divya@example.com", "2026-06-30 23:59:59"],
    ["C005", "Farhan Ali", "farhan@example.com", "2026-09-12 10:10:10"],
    ["C006", "Meena Iyer", "meena@example.com", "2026-04-01 06:00:00"],
]

try:
    with open("/app/customers_clean.csv", newline="") as f:
        rows = [r for r in csv.reader(f) if r]
except FileNotFoundError:
    print("FAIL: /app/customers_clean.csv not found")
    sys.exit(1)

if rows != EXPECTED:
    print("FAIL: output does not match expected rows")
    print("expected:", EXPECTED)
    print("got:     ", rows)
    sys.exit(1)

print("PASS")
sys.exit(0)
