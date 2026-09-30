# Task design notes

Each task is built so that an agent can be confident and still wrong. Every task passes
with its reference solution (oracle) and fails when nothing is done (nop).

| Task | Difficulty | Category |
|---|---|---|
| log-5xx-summary | easy | log processing |
| csv-dedupe-latest | easy | data processing |
| env-merge | easy | config parsing |
| invoice-rounding-fix | medium | fix a broken script |
| log-sessionize | medium | data processing |
| config-override-debug | medium | config debugging |
| rotated-logs-count | medium | multi-file reasoning |
| stale-rates-conversion | medium | misleading files |
| cron-next-runs | hard | reasoning / date logic |
| sqlite-add-not-null | hard | database migration |
| flaky-test-fix | hard | debugging |

Difficulty labels are initial guesses; model results will show the real difficulty.

---

### csv-dedupe-latest
**Tests:** following normalization rules exactly and comparing timestamps instead of file order.
**Trap:** the same customer appears as `C001`, ` C001` and `c001 `, and the newest row is not
the last one in the file (one pair differs by a single second).
**Common wrong answers:** keeping the last or first occurrence; not normalizing IDs, which
leaves duplicates.
**How the test catches it:** exact comparison with the expected rows.

### env-merge
**Tests:** implementing a specified file format instead of assuming a familiar one.
**Trap:** `#` inside a value is not a comment (`DB_PASSWORD="p@ss#word!"`, `API_TOKEN=tok_#live_42`),
`LOG_LEVEL=` must override to an empty value, a commented-out override must be ignored,
and `export ` must be stripped.
**Common wrong answers:** stripping inline comments; loading the files with a shell `source`,
which removes the quotes; skipping empty overrides.
**How the test catches it:** exact comparison of every output line and their order.

### invoice-rounding-fix
**Tests:** understanding floating-point rounding, not just patching the visible symptom.
**Trap:** Python's `round()` is not half-up, and binary floats can't represent values like
2.675 exactly (`round(2.675, 2)` is 2.67). Converting through float first
(`Decimal(qty * float(price))`) still gives wrong results.
**Common wrong answers:** only fixing the output format; using `Decimal` on a float value;
hardcoding the sample total.
**How the test catches it:** the fixed script is run on three hidden invoice files, each
containing values that break the wrong approaches.

### log-sessionize
**Tests:** handling time zones and unsorted input, and applying a boundary rule exactly.
**Trap:** timestamps mix `Z` and `+05:30`, the file is not in time order, a gap of exactly 30
minutes must stay in the same session, and a single-event session still counts.
**Common wrong answers:** ignoring the offsets (this produces 4–5 sessions per user instead
of 2–3); processing lines in file order; treating a 30-minute gap as a new session.
**How the test catches it:** exact expected session counts and total minutes per user.

### config-override-debug
**Tests:** investigating how a program actually loads configuration before changing it.
**Trap:** `app.ini` sets port 8000, but `conf.d/90-local.ini` is read later and overrides it
with 9090, so editing the obvious file changes nothing. The same override file also sets
host and workers, so deleting it breaks other settings. A decoy `95-port.ini.bak` is never loaded.
**Common wrong answers:** editing only `app.ini`; deleting `90-local.ini`; editing `app.py`.
**How the test catches it:** checks the effective configuration printed by the app, and
checks that `app.py` is unchanged using a file hash.

### rotated-logs-count
**Tests:** finding all relevant inputs and deduplicating across files.
**Trap:** the oldest log is gzipped, the rotated files overlap by a few lines (some of them
5xx errors), and one line was cut off during rotation.
**Common wrong answers:** skipping the `.gz` file; counting the duplicated requests twice.
**How the test catches it:** exact expected counts. Each careless approach produces a
different, wrong set of numbers.

### stale-rates-conversion
**Tests:** trusting data over names.
**Trap:** `rates_latest.csv` is actually the oldest rate set (as_of 2026-03-01); the newest is
`rates.json` (2026-09-15). A third file is in between.
**Common wrong answers:** using the file called "latest"; using the first file found.
**How the test catches it:** every rate set gives different prices, so only the correct one passes.

### cron-next-runs
**Tests:** implementing precise semantics with no library to lean on.
**Trap:** when both day-of-month and day-of-week are set, cron runs when EITHER matches;
day-of-week 7 means Sunday; runs must be strictly after the start time (so 00:00 on the
start day is excluded); one job only runs on February 29, so the next runs are in 2028,
2032 and 2036, and a search limited to one year finds nothing.
**Common wrong answers:** requiring both day fields to match; including the start time;
giving up or looping minute by minute for years.
**How the test catches it:** exact timestamps, generated independently with the croniter library.

### sqlite-add-not-null
**Tests:** knowing a database's real limitations and preserving everything around a change.
**Trap:** SQLite cannot add a NOT NULL column without a default, so the table must be rebuilt.
If the agent renames the OLD table (`ALTER TABLE users RENAME TO users_old`), modern SQLite
also rewrites the foreign key in `orders` to point at `users_old`, which then gets dropped.
Rebuilding the table also silently drops its index.
**Common wrong answers:** `ADD COLUMN ... NOT NULL DEFAULT ''` (violates "no default");
renaming the old table (breaks the foreign key); forgetting to recreate `idx_users_name`.
**How the test catches it:** inspects the schema, the default value, the index, the foreign
key target, all rows, `integrity_check` and `foreign_key_check`.

### flaky-test-fix
**Tests:** diagnosing order-dependent failures instead of trusting a single passing run.
**Trap:** the suite passes in its default order. There are two independent sources of shared
state: a mutable default argument (`new_cart(items=[])`) and a class-level list
(`CouponBook.codes = []`). Fixing only one still leaves the suite failing in most orders.
**Common wrong answers:** running the tests once, seeing them pass, and stopping; fixing
only one of the two bugs; editing the tests or adding retries.
**How the test catches it:** checks the test files are unchanged (hash), runs the suite in
30 shuffled orders, each in a fresh process, and runs hidden behavior checks.
