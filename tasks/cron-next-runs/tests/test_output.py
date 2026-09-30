import json
import sys

# Expected values were generated independently with the croniter library.
EXPECTED = {
    "backup-db": [
        "2026-10-01T09:30",
        "2026-10-05T09:30",
        "2026-10-12T09:30"
    ],
    "rotate-logs": [
        "2026-10-01T06:00",
        "2026-10-01T12:00",
        "2026-10-01T18:00"
    ],
    "weekly-report": [
        "2026-10-04T02:15",
        "2026-10-11T02:15",
        "2026-10-18T02:15"
    ],
    "audit": [
        "2026-10-02T00:00",
        "2026-10-09T00:00",
        "2026-10-13T00:00"
    ],
    "poll-queue": [
        "2026-10-01T08:45",
        "2026-10-01T12:45",
        "2026-10-01T16:45"
    ],
    "leap-report": [
        "2028-02-29T12:00",
        "2032-02-29T12:00",
        "2036-02-29T12:00"
    ]
}

try:
    with open("/app/next_runs.json") as f:
        data = json.load(f)
except FileNotFoundError:
    print("FAIL: /app/next_runs.json not found")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"FAIL: invalid JSON: {e}")
    sys.exit(1)

failed = False
for job, runs in EXPECTED.items():
    if data.get(job) != runs:
        print(f"FAIL: {job}: expected {runs}, got {data.get(job)}")
        failed = True
extra = set(data) - set(EXPECTED)
if extra:
    print(f"FAIL: unexpected jobs in output: {sorted(extra)}")
    failed = True

if failed:
    sys.exit(1)
print("PASS")
sys.exit(0)
