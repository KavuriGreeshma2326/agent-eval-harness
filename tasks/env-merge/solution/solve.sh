#!/bin/bash
python3 - <<'PY'
def parse(path):
    settings = {}
    for raw in open(path):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):]
        key, _, value = stripped.partition("=")
        settings[key.strip()] = value
    return settings

base = parse("/app/base.env")
override = parse("/app/override.env")
merged = dict(base)
for key, value in override.items():
    merged[key] = value  # existing keys keep their position, new keys are appended

with open("/app/final.env", "w") as f:
    for key, value in merged.items():
        f.write(f"{key}={value}\n")
PY
