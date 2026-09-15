import json
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FILES = [
    "task.json",
    "instruction.md",
    "environment/Dockerfile",
    "tests/test.sh",
]


@dataclass
class Task:
    id: str
    path: Path
    instruction: str
    difficulty: str
    max_steps: int
    command_timeout_sec: int
    test_timeout_sec: int


def load_task(task_dir: str) -> Task:
    path = Path(task_dir).resolve()
    for rel in REQUIRED_FILES:
        if not (path / rel).exists():
            raise FileNotFoundError(f"Task is missing required file: {path / rel}")

    meta = json.loads((path / "task.json").read_text())
    return Task(
        id=meta["id"],
        path=path,
        instruction=(path / "instruction.md").read_text(),
        difficulty=meta.get("difficulty", "unknown"),
        max_steps=meta.get("max_steps", 20),
        command_timeout_sec=meta.get("command_timeout_sec", 30),
        test_timeout_sec=meta.get("test_timeout_sec", 60),
    )