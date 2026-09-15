import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from harness.sandbox import Sandbox


def run_trial(task, agent, runs_dir: Path) -> dict:
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trial_id = f"{stamp}-{task.id}-{agent.name}-{uuid.uuid4().hex[:6]}"

    sandbox = Sandbox(task)
    steps = []
    passed = False
    test_output = ""
    error = None
    started = time.time()

    try:
        sandbox.build()
        sandbox.start()
        agent.run(task, sandbox, steps)
        sandbox.copy_in(task.path / "tests", "/tests")
        test = sandbox.exec("bash /tests/test.sh", task.test_timeout_sec)
        passed = test["exit_code"] == 0
        test_output = test["output"]
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    finally:
        sandbox.stop()

    record = {
        "trial_id": trial_id,
        "task_id": task.id,
        "difficulty": task.difficulty,
        "agent": agent.name,
        "agent_info": getattr(agent, "info", {}),
        "passed": passed,
        "error": error,
        "test_output": test_output,
        "num_steps": len(steps),
        "duration_sec": round(time.time() - started, 2),
        "steps": steps,
    }
    (runs_dir / f"{trial_id}.json").write_text(json.dumps(record, indent=2))
    return record