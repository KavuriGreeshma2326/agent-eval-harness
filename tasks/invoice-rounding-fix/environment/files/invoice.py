import csv
import sys


def line_total(qty, unit_price):
    return round(qty * unit_price, 2)


def main(path):
    total = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            total += line_total(int(row["qty"]), float(row["unit_price"]))
    print(total)


if __name__ == "__main__":
    main(sys.argv[1])
