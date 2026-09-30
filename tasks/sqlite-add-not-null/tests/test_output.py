import sqlite3
import sys

EXPECTED_USERS = [
    (1, "Anitha Rao", "Guntur", "anitha.rao@example.com"),
    (2, "Bilal Khan", "Hyderabad", "bilal.khan@example.com"),
    (3, "Chen Wei", None, "user3@placeholder.invalid"),
    (4, "Divya Menon", "Kochi", "divya@example.com"),
    (5, "Esha Patel", "Pune", "esha.patel@example.com"),
    (7, "Farhan Ali", "Vijayawada", "user7@placeholder.invalid"),
    (8, "Gita Nair", "Chennai", "gita.nair@example.com"),
    (10, "Hari Prasad", "Tirupati", "hari@example.com"),
]
EXPECTED_ORDERS = [
    (101, 1, 250.0), (102, 2, 99.5), (103, 1, 1200.0), (104, 4, 45.25),
    (105, 5, 300.0), (106, 7, 18.0), (107, 8, 760.4), (108, 10, 55.0),
    (109, 3, 410.0), (110, 2, 12.75), (111, 7, 999.99), (112, 1, 5.5),
]

errors = []
try:
    conn = sqlite3.connect("file:/app/shop.db?mode=ro", uri=True)
    columns = conn.execute("PRAGMA table_info(users)").fetchall()
except sqlite3.Error as e:
    print(f"FAIL: cannot open /app/shop.db: {e}")
    sys.exit(1)

# (cid, name, type, notnull, dflt_value, pk)
names = [c[1] for c in columns]
if names != ["id", "name", "city", "email"]:
    errors.append(f"users columns should be ['id', 'name', 'city', 'email'], got {names}")
email_col = next((c for c in columns if c[1] == "email"), None)
if email_col is not None:
    if email_col[3] != 1:
        errors.append("email is not declared NOT NULL")
    if email_col[4] is not None:
        errors.append(f"email must have no default value, found default {email_col[4]}")

users = conn.execute("SELECT * FROM users ORDER BY id").fetchall() if names == ["id", "name", "city", "email"] else None
if users is not None and users != EXPECTED_USERS:
    errors.append(f"users rows are wrong:\n  expected {EXPECTED_USERS}\n  got      {users}")

indexes = {row[1] for row in conn.execute("PRAGMA index_list(users)").fetchall()}
if "idx_users_name" not in indexes:
    errors.append("index idx_users_name on users is missing")
else:
    cols = [row[2] for row in conn.execute("PRAGMA index_info(idx_users_name)").fetchall()]
    if cols != ["name"]:
        errors.append(f"idx_users_name should cover (name), covers {cols}")

fks = conn.execute("PRAGMA foreign_key_list(orders)").fetchall()
# (id, seq, table, from, to, on_update, on_delete, match)
if [(fk[2], fk[3], fk[4], fk[6]) for fk in fks] != [("users", "user_id", "id", "CASCADE")]:
    errors.append(f"orders foreign key should be user_id -> users(id) ON DELETE CASCADE, got {fks}")

orders = conn.execute("SELECT id, user_id, total FROM orders ORDER BY id").fetchall()
if orders != EXPECTED_ORDERS:
    errors.append("orders rows were changed")

tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
if tables != {"users", "orders"}:
    errors.append(f"expected only tables users and orders, found {sorted(tables)}")

if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
    errors.append("PRAGMA integrity_check failed")
if conn.execute("PRAGMA foreign_key_check").fetchall():
    errors.append("PRAGMA foreign_key_check reported problems")

if errors:
    for e in errors:
        print("FAIL:", e)
    sys.exit(1)
print("PASS")
sys.exit(0)
