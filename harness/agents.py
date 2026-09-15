from harness.llm_agent import LLMAgent


class NopAgent:
    """Does nothing. A valid task must FAIL with this agent."""
    name = "nop"

    def __init__(self):
        self.info = {}

    def run(self, task, sandbox, steps: list):
        steps.append({"step": 1, "action": "nop", "note": "agent did nothing"})


class OracleAgent:
    """Runs the reference solution. A valid task must PASS with this agent."""
    name = "oracle"

    def __init__(self):
        self.info = {}

    def run(self, task, sandbox, steps: list):
        solution_dir = task.path / "solution"
        if not (solution_dir / "solve.sh").exists():
            raise FileNotFoundError(f"No solution/solve.sh in {task.path}")
        sandbox.copy_in(solution_dir, "/solution")
        result = sandbox.exec("bash /solution/solve.sh", task.command_timeout_sec)
        steps.append({
            "step": 1,
            "command": "bash /solution/solve.sh",
            "exit_code": result["exit_code"],
            "output": result["output"],
        })


AGENTS = {
    "nop": NopAgent,
    "oracle": OracleAgent,
    "llm": LLMAgent,
}