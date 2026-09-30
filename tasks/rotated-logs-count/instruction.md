/app/logs/ contains an API access log and its rotated older copies. Each valid line has
exactly 6 space-separated fields:

    <timestamp> <request_id> <method> <path> <status> <latency>

Count server errors (status 500 to 599 inclusive) per path across ALL of the logs.

Rules:
- Every request has a unique request_id. Log rotation sometimes wrote the same request
  into more than one file; count each request only once.
- Skip malformed lines (any line that does not have exactly 6 fields).
- Only include paths with at least one server error.

Write /app/errors_by_path.json as a JSON object mapping path to count, with keys sorted
alphabetically.
