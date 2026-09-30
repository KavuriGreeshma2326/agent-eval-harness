/app/shop.db is a SQLite database with a users table and an orders table. Add an email
column to users, filled from /app/emails.csv (columns: user_id, email).

Requirements:
- users must end up with the columns id, name, city, email, in that order.
- email must be declared NOT NULL and must have no default value.
- Store each email trimmed and in lowercase.
- Users with no row in emails.csv get the email user<id>@placeholder.invalid
  (for example user3@placeholder.invalid). Ignore rows for users that do not exist.
- Keep every existing user and order, with their ids and data unchanged.
- Keep the index idx_users_name on users(name).
- orders must still reference users(id) with ON DELETE CASCADE, and the database must
  pass PRAGMA integrity_check and PRAGMA foreign_key_check.
- Do not leave any extra tables in the database.

Python's sqlite3 module is available. The sqlite3 command-line tool is not installed.
