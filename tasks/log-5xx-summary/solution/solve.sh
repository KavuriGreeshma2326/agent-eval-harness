#!/bin/bash
python3 - <<'EOF'
import json
counts = {}
for line in open("/app/access.log"):
    parts = line.split()
    if len(parts) != 5:
        continue
    _, method, path, status, _ = parts
    if not status.isdigit():
        continue
    code = int(status)
    if 500 <= code <= 599:
        p = path.split("?")[0]
        counts[p] = counts.get(p, 0) + 1
with open("/app/errors.json", "w") as f:
    json.dump(dict(sorted(counts.items())), f, indent=2)
EOF