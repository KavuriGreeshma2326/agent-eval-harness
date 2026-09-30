#!/bin/bash
python3 - <<'PY'
import csv
from datetime import datetime

best = {}
with open("/app/customers.csv", newline="") as f:
    reader = csv.DictReader(f)
    header = reader.fieldnames
    for row in reader:
        cid = row["customer_id"].strip().upper()
        ts = datetime.strptime(row["updated_at"], "%Y-%m-%d %H:%M:%S")
        if cid not in best or ts > best[cid][0]:
            best[cid] = (ts, row)

with open("/app/customers_clean.csv", "w", newline="") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(header)
    for cid in sorted(best):
        row = best[cid][1]
        writer.writerow([cid, row["name"], row["email"], row["updated_at"]])
PY
