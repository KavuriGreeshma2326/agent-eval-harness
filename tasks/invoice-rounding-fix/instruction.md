/app/invoice.py prints the total of an invoice CSV file:

    python3 /app/invoice.py /app/invoices/sample.csv

Finance reports that its totals are sometimes off by a cent and badly formatted.
Fix /app/invoice.py so that it follows these rules:

- Each line total is qty × unit_price, rounded to 2 decimal places, with exact halves
  rounded up (for example 0.125 becomes 0.13 and 2.675 becomes 2.68).
- The invoice total is the sum of the rounded line totals.
- The script prints only the total, with exactly 2 decimal places (for example 31.50).

For /app/invoices/sample.csv the correct output is 30.77.

Your fixed script will also be run on other invoice files with the same columns, so it
must compute the result rather than hardcode it. Keep the same command-line usage.
