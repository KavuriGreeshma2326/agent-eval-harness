The test suite in /app/project passes when run locally:

    cd /app/project && python3 -m unittest

but CI runs the same tests in a random order, and there it fails intermittently.

Fix the application code so the suite passes reliably in any test order.

Rules:
- Do not modify, rename or delete the test files (test_*.py).
- Keep the public behavior of cart.py and coupons.py the same.
