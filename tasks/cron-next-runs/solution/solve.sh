#!/bin/bash
python3 - <<'PY'
import json
from datetime import datetime, timedelta

RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


def parse_field(text, lo, hi):
    values = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/")
            step = int(step_text)
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            start, end = (int(x) for x in part.split("-"))
        else:
            start = end = int(part)
            if step != 1:  # "5/10" means 5, 15, 25 ... in cron
                end = hi
        values.update(range(start, end + 1, step))
    return values


def next_runs(fields, after, count=3):
    minutes, hours, doms, months, dows = (
        parse_field(f, lo, hi) for f, (lo, hi) in zip(fields, RANGES))
    dows = {0 if d == 7 else d for d in dows}
    dom_star, dow_star = fields[2] == "*", fields[4] == "*"

    runs = []
    day = after.replace(hour=0, minute=0)
    while len(runs) < count:
        cron_dow = (day.weekday() + 1) % 7  # Python Monday=0 -> cron Monday=1, Sunday=0
        dom_ok, dow_ok = day.day in doms, cron_dow in dows
        if dom_star or dow_star:
            day_ok = dom_ok and dow_ok
        else:
            day_ok = dom_ok or dow_ok
        if day.month in months and day_ok:
            for h in sorted(hours):
                for m in sorted(minutes):
                    t = day.replace(hour=h, minute=m)
                    if t > after and len(runs) < count:
                        runs.append(t.strftime("%Y-%m-%dT%H:%M"))
        day += timedelta(days=1)
    return runs


after = datetime(2026, 10, 1, 0, 0)
result = {}
for raw in open("/app/crontab"):
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    parts = line.split()
    if "=" in parts[0]:
        continue
    fields, command = parts[:5], " ".join(parts[5:])
    result[command] = next_runs(fields, after)

with open("/app/next_runs.json", "w") as f:
    json.dump(result, f, indent=2)
PY
