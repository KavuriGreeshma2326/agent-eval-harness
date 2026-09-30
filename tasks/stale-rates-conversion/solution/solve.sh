#!/bin/bash
python3 - <<'PY'
import csv
import glob
import json

# Collect every rate set together with its as_of date. The file names are not reliable
# ("rates_latest.csv" is actually the oldest), so compare the dates inside the files.
candidates = []
for path in glob.glob("/app/rates/*.json"):
    data = json.load(open(path))
    candidates.append((data["as_of"], {k: float(v) for k, v in data["rates"].items()}))
for path in glob.glob("/app/rates/*.csv"):
    rows = list(csv.DictReader(open(path)))
    candidates.append((rows[0]["as_of"], {r["currency"]: float(r["per_usd"]) for r in rows}))

as_of, rates = max(candidates, key=lambda c: c[0])  # ISO dates sort correctly as strings

result = {}
for product in json.load(open("/app/products.json")):
    price, currency = float(product["price"]), product["currency"]
    inr = price if currency == "INR" else price / rates[currency] * rates["INR"]
    result[product["sku"]] = round(inr, 2)

with open("/app/prices_inr.json", "w") as f:
    json.dump(result, f, indent=2)
PY
