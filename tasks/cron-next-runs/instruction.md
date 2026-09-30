/app/crontab contains scheduled jobs in standard cron format:

    minute hour day-of-month month day-of-week command

For every job, compute its next 3 run times strictly after 2026-10-01 00:00 (all times
are UTC). Write /app/next_runs.json as a JSON object that maps each job's command to a
list of 3 strings in the format YYYY-MM-DDTHH:MM, in chronological order.

Follow standard cron semantics:
- Fields support *, single numbers, lists (1,15), ranges (1-5) and steps (*/6, 8-17/4).
- Day of week is 0-7, where both 0 and 7 mean Sunday.
- If both day-of-month and day-of-week are restricted (neither is *), the job runs
  when EITHER field matches.
- Ignore blank lines, comment lines starting with #, and environment lines such as
  MAILTO=ops@example.com.

No cron libraries are installed and there is no internet access.
