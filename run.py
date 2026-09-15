import argparse
from pathlib import Path

from harness.agents import AGENTS
from harness.runner import run_trial
from harness.task import load_task


def main():
    parser = argparse.ArgumentParser(description="Agent Evaluation Harness")
    parser.add_argument("--task", required=True, help="Path to a task folder")
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--trials", type=int, default=1)
    args = parser.parse_args()

    task = load_task(args.task)
    passes = 0

    for i in range(args.trials):
        record = run_trial(task, AGENTS[args.agent](), Path("runs"))
        status = "PASS" if record["passed"] else "FAIL"
        print(f"[{i + 1}/{args.trials}] {task.id} agent={args.agent} -> {status} "
              f"({record['duration_sec']}s)")
        if record["error"]:
            print(f"    error: {record['error']}")
        if record["test_output"]:
            print(f"    test output: {record['test_output'].strip()[:300]}")
        passes += int(record["passed"])

    print(f"\nPass rate: {passes}/{args.trials}")


if __name__ == "__main__":
    main()