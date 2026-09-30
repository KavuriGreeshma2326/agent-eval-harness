#!/bin/bash
python3 - <<'PY'
import glob
import gzip
import json

seen = set()
counts = {}
for path in sorted(glob.glob("/app/logs/access.log*")):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        for line in f:
            parts = line.split()
            if len(parts) != 6:
                continue
            _, request_id, _, endpoint, status, _ = parts
            if request_id in seen or not status.isdigit():
                continue
            seen.add(request_id)
            if 500 <= int(status) <= 599:
                counts[endpoint] = counts.get(endpoint, 0) + 1

with open("/app/errors_by_path.json", "w") as f:
    json.dump(dict(sorted(counts.items())), f, indent=2)
PY
