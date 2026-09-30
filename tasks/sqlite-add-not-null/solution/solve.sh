#!/bin/bash
python3 - <<'PY'
import csv
import sqlite3

emails = {}
with open("/app/emails.csv", newline="") as f:
    for row in csv.DictReader(f):
        emails[int(row["user_id"])] = row["email"].strip().lower()

conn = sqlite3.connect("/app/shop.db", isolation_level=None)
# SQLite cannot add a NOT NULL column without a default, so rebuild the table.
# Build a new table and rename it into place. Renaming the OLD table instead would make
# SQLite rewrite the foreign key in orders to point at the old name.
conn.execute("PRAGMA foreign_keys = OFF")
conn.execute("BEGIN")
conn.execute("""
    CREATE TABLE users_new (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT,
        email TEXT NOT NULL
    )
""")
for user_id, name, city in conn.execute("SELECT id, name, city FROM users ORDER BY id").fetchall():
    email = emails.get(user_id, f"user{user_id}@placeholder.invalid")
    conn.execute("INSERT INTO users_new VALUES (?, ?, ?, ?)", (user_id, name, city, email))
conn.execute("DROP TABLE users")  # also drops idx_users_name, recreated below
conn.execute("ALTER TABLE users_new RENAME TO users")
conn.execute("CREATE INDEX idx_users_name ON users(name)")
conn.execute("COMMIT")
conn.execute("PRAGMA foreign_keys = ON")
problems = conn.execute("PRAGMA foreign_key_check").fetchall()
assert not problems, problems
conn.close()
PY
