The service in /app must listen on port 8080, but running

    python3 /app/app.py

shows that it uses a different port.

Fix the configuration so the service uses port 8080. Rules:
- Do not modify /app/app.py.
- Do not change any other effective setting (you can see all of them with
  python3 /app/app.py --print-config).
