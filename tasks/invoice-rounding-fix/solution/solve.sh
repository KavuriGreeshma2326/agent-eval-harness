#!/bin/bash
cat > /app/invoice.py <<'PY'
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def line_total(qty, unit_price):
    # Parse from strings: converting through float would bring back binary rounding errors.
    return (Decimal(qty) * Decimal(unit_price)).quantize(CENT, rounding=ROUND_HALF_UP)


def main(path):
    total = Decimal("0")
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            total += line_total(row["qty"].strip(), row["unit_price"].strip())
    print(f"{total:.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
PY
