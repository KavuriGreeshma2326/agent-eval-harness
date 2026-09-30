import sys

EXPECTED = [
    "APP_NAME=orders-service",
    "DB_HOST=db.internal",
    "DB_PORT=5432",
    'DB_PASSWORD="p@ss#word!"',
    "LOG_LEVEL=",
    "FEATURE_FLAGS=search,checkout,wallet",
    "CACHE_TTL=300",
    "API_TOKEN=tok_#live_42",
    "METRICS_URL=http://metrics.internal:9090/push?job=orders",
]

try:
    with open("/app/final.env") as f:
        lines = [l.rstrip("\r\n") for l in f]
except FileNotFoundError:
    print("FAIL: /app/final.env not found")
    sys.exit(1)

while lines and lines[-1] == "":
    lines.pop()

if lines != EXPECTED:
    print("FAIL: /app/final.env does not match")
    print("expected:", EXPECTED)
    print("got:     ", lines)
    sys.exit(1)

print("PASS")
sys.exit(0)
