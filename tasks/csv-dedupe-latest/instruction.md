The file /app/customers.csv contains customer records exported from two systems, so
some customers appear more than once. Columns: customer_id, name, email, updated_at
(format YYYY-MM-DD HH:MM:SS).

Produce /app/customers_clean.csv with exactly one row per customer.

Rules:
- Customer IDs are case-insensitive and may have leading or trailing spaces:
  "C001", " c001" and "c001 " are the same customer.
- For each customer, keep the row with the most recent updated_at.
- Write the customer_id in the output trimmed and uppercase (for example C001).
- Copy name, email and updated_at exactly as they appear in the kept row.
- Keep the same header row, and sort the output rows by customer_id.
