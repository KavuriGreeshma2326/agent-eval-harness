import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from harness.sandbox import Sandbox, SandboxError


def classify_error(exc: Exception) -> str:
    """Say where an exception came from. None of these are the agent's fault:
    the agent's own shell commands never raise (failures come back as exit codes)."""
    if isinstance(exc, SandboxError):
        return "docker"
    try:
        import openai
        if isinstance(exc, openai.OpenAIError):
            return "llm_api"
    except ImportError:
        pass
    return "harness"


def run_trial(task, agent, runs_dir: Path) -> dict:
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trial_id = f"{stamp}-{task.id}-{agent.name}-{uuid.uuid4().hex[:6]}"

    sandbox = Sandbox(task)
    steps = []
    passed = False
    test_output = ""
    error = None
    error_type = None
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
        error_type = classify_error(e)
    finally:
        sandbox.stop()

    if error is not None:
        outcome = "infra_error"
    elif passed:
        outcome = "passed"
    else:
        outcome = "failed"

    record = {
        "trial_id": trial_id,
        "task_id": task.id,
        "difficulty": task.difficulty,
        "agent": agent.name,
        "agent_info": getattr(agent, "info", {}),
        "outcome": outcome,
        "passed": passed,
        "error": error,
        "error_type": error_type,
        "test_output": test_output,
        "num_steps": len(steps),
        "duration_sec": round(time.time() - started, 2),
        "steps": steps,
    }
    (runs_dir / f"{trial_id}.json").write_text(json.dumps(record, indent=2))
    return record
