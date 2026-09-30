#!/bin/bash
python3 - <<'PY'
import json
from collections import defaultdict
from datetime import datetime, timedelta

events = defaultdict(list)
for line in open("/app/events.log"):
    parts = line.split()
    if len(parts) != 3:
        continue
    ts, user, _ = parts
    events[user].append(datetime.fromisoformat(ts.replace("Z", "+00:00")))

gap = timedelta(minutes=30)
result = {}
for user in sorted(events):
    times = sorted(events[user])  # the file is not in time order
    sessions, total = 0, timedelta()
    start = prev = None
    for t in times:
        if prev is None or t - prev > gap:
            if start is not None:
                total += prev - start
            sessions += 1
            start = t
        prev = t
    total += prev - start
    result[user] = {"sessions": sessions, "total_minutes": int(total.total_seconds() // 60)}

with open("/app/sessions.json", "w") as f:
    json.dump(result, f, indent=2)
PY
