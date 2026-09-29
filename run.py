import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from harness.agents import AGENTS
from harness.runner import run_trial
from harness.task import load_task

TASKS_DIR = Path("tasks")


def discover_tasks():
    return sorted(p for p in TASKS_DIR.iterdir() if (p / "task.json").exists())


def pass_rate_str(passed: int, failed: int) -> str:
    scored = passed + failed
    return f"{passed}/{scored}" if scored else "-"


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Agent Evaluation Harness")
    parser.add_argument("--task", nargs="+", help="One or more task folders")
    parser.add_argument("--all", action="store_true", help="Run every task in tasks/")
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--model", help="Override LLM_MODEL from .env")
    args = parser.parse_args()

    if not args.task and not args.all:
        parser.error("give --task <folder> or --all")
    if args.model:
        os.environ["LLM_MODEL"] = args.model

    task_dirs = discover_tasks() if args.all else [Path(t) for t in args.task]
    tasks = [load_task(str(d)) for d in task_dirs]

    summary = []
    for task in tasks:
        counts = {"passed": 0, "failed": 0, "infra_error": 0}
        for i in range(args.trials):
            agent = AGENTS[args.agent]()
            record = run_trial(task, agent, Path("runs"))
            outcome = record["outcome"]
            counts[outcome] += 1
            status = {"passed": "PASS", "failed": "FAIL", "infra_error": "INFRA_ERROR"}[outcome]
            print(f"[{i + 1}/{args.trials}] {task.id} agent={args.agent} -> {status} "
                  f"({record['duration_sec']}s, {record['num_steps']} steps)")

            info = record["agent_info"]
            if info.get("stop_reason"):
                print(f"    stop_reason: {info['stop_reason']}  confidence: {info.get('confidence')}  "
                      f"tokens: {info.get('prompt_tokens', 0)}+{info.get('completion_tokens', 0)}")
            if record["error"]:
                print(f"    error ({record['error_type']}): {record['error']}")
            if record["test_output"]:
                print(f"    test output: {record['test_output'].strip()[:300]}")
        summary.append((task.id, counts))

    print("\n=== Summary (pass rate excludes infra errors) ===")
    print(f"{'TASK':30} {'PASSED':>8} {'INFRA_ERRORS':>13}")
    total = {"passed": 0, "failed": 0, "infra_error": 0}
    for task_id, c in summary:
        print(f"{task_id:30} {pass_rate_str(c['passed'], c['failed']):>8} {c['infra_error']:>13}")
        for k in total:
            total[k] += c[k]
    print(f"{'TOTAL':30} {pass_rate_str(total['passed'], total['failed']):>8} {total['infra_error']:>13}")


if __name__ == "__main__":
    main()
