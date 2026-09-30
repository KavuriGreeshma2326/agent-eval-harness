Merge /app/base.env and /app/override.env into /app/final.env.

File format:
- Each setting is a line KEY=VALUE. A line may start with "export " before the key.
- Blank lines and lines whose first non-space character is # are comments.
- There are no inline comments: a # anywhere after the = is part of the value.
- The value is everything after the first =, exactly as written (keep any quotes).

Merge rules:
- A key in override.env replaces the same key from base.env, even if the new value
  is empty (KEY= means the value becomes empty).
- Keys that only exist in override.env are added.

Output format for /app/final.env:
- One KEY=VALUE line per key, with no "export " prefix, no comments and no blank lines.
- Keys from base.env come first in their original order, followed by keys that only
  appear in override.env in the order they appear there.
