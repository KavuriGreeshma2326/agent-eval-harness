The file /app/access.log contains HTTP request logs. Each valid line has exactly
5 space-separated fields: timestamp, method, path, status code, latency.

Count server errors (status codes 500 to 599 inclusive) per endpoint path.

Rules:
- Ignore query strings: /api/orders?page=2 counts as /api/orders
- Skip malformed lines (wrong field count or non-numeric status)
- Only include paths with at least one server error

Write the result to /app/errors.json as a JSON object mapping path to count,
with keys sorted alphabetically.