import argparse
from pathlib import Path

from dotenv import load_dotenv

from harness.agents import AGENTS
from harness.runner import run_trial
from harness.task import load_task


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Agent Evaluation Harness")
    parser.add_argument("--task", required=True, help="Path to a task folder")
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--trials", type=int, default=1)
    args = parser.parse_args()

    task = load_task(args.task)
    passes = 0

    for i in range(args.trials):
        agent = AGENTS[args.agent]()
        record = run_trial(task, agent, Path("runs"))
        status = "PASS" if record["passed"] else "FAIL"
        print(f"[{i + 1}/{args.trials}] {task.id} agent={args.agent} -> {status} "
              f"({record['duration_sec']}s, {record['num_steps']} steps)")

        info = record["agent_info"]
        if info.get("stop_reason"):
            print(f"    stop_reason: {info['stop_reason']}  confidence: {info.get('confidence')}  "
                  f"tokens: {info.get('prompt_tokens', 0)}+{info.get('completion_tokens', 0)}")
        if record["error"]:
            print(f"    error: {record['error']}")
        if record["test_output"]:
            print(f"    test output: {record['test_output'].strip()[:300]}")
        passes += int(record["passed"])

    print(f"\nPass rate: {passes}/{args.trials}")


if __name__ == "__main__":
    main()