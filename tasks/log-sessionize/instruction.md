/app/events.log contains user activity events, one per line:

    <timestamp> <user> <event>

Timestamps are ISO 8601 and include a UTC offset (either Z or +05:30).

Group each user's events into sessions: a new session starts when the time since that
user's previous event is MORE than 30 minutes. A gap of exactly 30 minutes stays in the
same session. A session's duration is the time from its first event to its last event,
in whole minutes (a session with a single event has duration 0).

Write /app/sessions.json as a JSON object mapping each user to an object with two
integer fields: "sessions" (the number of sessions) and "total_minutes" (the sum of all
session durations for that user).
