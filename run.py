import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from harness.agents import AGENTS
from harness.analysis import load_runs, model_of, outcome_of
from harness.runner import run_trial
from harness.task import load_task

TASKS_DIR = Path("tasks")


def discover_tasks():
    return sorted(p for p in TASKS_DIR.iterdir() if (p / "task.json").exists())


def pass_rate_str(passed: int, failed: int) -> str:
    scored = passed + failed
    return f"{passed}/{scored}" if scored else "-"


def validate_main(argv):
    """Check every task is well-formed: the reference solution (oracle) must pass
    and a do-nothing agent (nop) must fail. Validation runs are saved in runs/validate/
    so they don't mix with real results in report.py."""
    parser = argparse.ArgumentParser(prog="run.py validate",
                                     description="Validate tasks with the oracle and nop agents")
    parser.add_argument("--task", nargs="+", help="One or more task folders")
    parser.add_argument("--all", action="store_true", help="Validate every task in tasks/")
    args = parser.parse_args(argv)
    if not args.task and not args.all:
        parser.error("give --task <folder> or --all")

    task_dirs = discover_tasks() if args.all else [Path(t) for t in args.task]
    tasks = [load_task(str(d)) for d in task_dirs]
    runs_dir = Path("runs") / "validate"
    labels = {"passed": "PASS", "failed": "FAIL", "infra_error": "INFRA_ERROR"}

    print(f"{'TASK':30} {'ORACLE':>12} {'NOP':>12} {'VALID':>6}")
    all_valid = True
    for task in tasks:
        oracle = run_trial(task, AGENTS["oracle"](), runs_dir)
        nop = run_trial(task, AGENTS["nop"](), runs_dir)
        valid = oracle["outcome"] == "passed" and nop["outcome"] == "failed"
        all_valid = all_valid and valid
        print(f"{task.id:30} {labels[oracle['outcome']]:>12} {labels[nop['outcome']]:>12} "
              f"{'yes' if valid else 'NO':>6}")
        for name, rec in (("oracle", oracle), ("nop", nop)):
            if rec["error"]:
                print(f"    {name} error ({rec['error_type']}): {rec['error']}")

    print("\nAll tasks valid." if all_valid else "\nSome tasks are INVALID (see above).")
    return 0 if all_valid else 1


RATE_LIMIT_WAIT_SEC = 65   # per-minute provider limits reset within about a minute
MAX_RATE_LIMIT_WAITS = 5   # per trial; after that the trial is kept as an infra error
STATUS = {"passed": "PASS", "failed": "FAIL", "infra_error": "INFRA_ERROR"}


def is_rate_limit(record):
    return record["outcome"] == "infra_error" and (record.get("error") or "").startswith("RateLimitError")


def is_daily_limit(record):
    """A rate-limit error caused by a per-day cap. Waiting a minute will not help."""
    text = (record.get("error") or "").lower()
    return is_rate_limit(record) and any(marker in text for marker in ("per day", "(tpd)", "(rpd)"))


def count_scored(existing, task_id, agent_name, model):
    """Saved trials for this task, agent and model that count toward pass rates."""
    return sum(1 for r in existing
               if r["task_id"] == task_id and r["agent"] == agent_name
               and model_of(r) == model and outcome_of(r) != "infra_error")


def print_trial(index, total, task, agent_name, record, say=print):
    say(f"[{index}/{total}] {task.id} agent={agent_name} -> {STATUS[record['outcome']]} "
        f"({record['duration_sec']}s, {record['num_steps']} steps)")
    info = record["agent_info"]
    if info.get("stop_reason"):
        say(f"    stop_reason: {info['stop_reason']}  confidence: {info.get('confidence')}  "
            f"tokens: {info.get('prompt_tokens', 0)}+{info.get('completion_tokens', 0)}")
    if record["error"]:
        say(f"    error ({record['error_type']}): {record['error'][:300]}")
    if record["test_output"]:
        say(f"    test output: {record['test_output'].strip()[:300]}")


def run_batch(tasks, agent_name, trials, model, fill=False, runs_dir=Path("runs"),
              max_infra_streak=3, trial_fn=run_trial, sleep_fn=time.sleep, say=print):
    """Run trials for every task. Returns (summary, stop_reason).

    fill: only run the trials still missing, counting scored trials already saved for this
    agent and model, so an interrupted run can simply be started again.
    Stops early (stop_reason is a message) when a daily rate limit is hit, or after
    max_infra_streak infra errors in a row, so a broken setup does not burn through every
    trial. A per-minute rate limit is waited out and the trial is run again."""
    existing = load_runs(str(runs_dir)) if fill else []
    summary, streak = [], 0

    for task in tasks:
        have = count_scored(existing, task.id, agent_name, model) if fill else 0
        todo = max(trials - have, 0)
        counts = {"passed": 0, "failed": 0, "infra_error": 0}
        summary.append({"task": task.id, "have": have, "counts": counts})
        if fill:
            say(f"{task.id}: {have} scored trials already saved, running {todo} more")

        for i in range(todo):
            for attempt in range(MAX_RATE_LIMIT_WAITS + 1):
                record = trial_fn(task, AGENTS[agent_name](), runs_dir)
                if (is_rate_limit(record) and not is_daily_limit(record)
                        and attempt < MAX_RATE_LIMIT_WAITS):
                    say(f"    per-minute rate limit hit; waiting {RATE_LIMIT_WAIT_SEC}s, "
                        f"then running a fresh trial")
                    sleep_fn(RATE_LIMIT_WAIT_SEC)
                    continue
                break

            print_trial(i + 1, todo, task, agent_name, record, say)
            counts[record["outcome"]] += 1
            streak = streak + 1 if record["outcome"] == "infra_error" else 0

            if is_daily_limit(record):
                return summary, ("a daily rate limit was reached for this model. "
                                 "Run the same command again after the limit resets; "
                                 "--fill continues where this run stopped.")
            if streak >= max_infra_streak:
                return summary, (f"{streak} infra errors in a row (last: "
                                 f"{(record['error'] or '')[:200]}). Fix the problem, then run the "
                                 f"same command again; --fill continues where this run stopped.")
    return summary, None


def main():
    load_dotenv()

    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        return validate_main(sys.argv[2:])

    parser = argparse.ArgumentParser(description="Agent Evaluation Harness")
    parser.add_argument("--task", nargs="+", help="One or more task folders")
    parser.add_argument("--all", action="store_true", help="Run every task in tasks/")
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--model", help="Override LLM_MODEL from .env")
    parser.add_argument("--fill", action="store_true",
                        help="Only run the trials still missing: count scored trials already "
                             "saved in runs/ for each task and model, and run just enough to "
                             "reach --trials")
    parser.add_argument("--max-infra-streak", type=int, default=3,
                        help="Stop after this many infra errors in a row (default 3)")
    args = parser.parse_args()

    if not args.task and not args.all:
        parser.error("give --task <folder> or --all")
    if args.model:
        os.environ["LLM_MODEL"] = args.model

    task_dirs = discover_tasks() if args.all else [Path(t) for t in args.task]
    tasks = [load_task(str(d)) for d in task_dirs]
    model = AGENTS[args.agent]().info.get("model", "-")

    summary, stop_reason = run_batch(tasks, args.agent, args.trials, model, fill=args.fill,
                                     max_infra_streak=args.max_infra_streak)

    print("\n=== Summary (pass rate excludes infra errors) ===")
    had = f" {'HAD':>5}" if args.fill else ""
    print(f"{'TASK':30}{had} {'PASSED':>8} {'INFRA_ERRORS':>13}")
    total = {"passed": 0, "failed": 0, "infra_error": 0}
    for row in summary:
        c = row["counts"]
        had_col = f" {row['have']:>5}" if args.fill else ""
        print(f"{row['task']:30}{had_col} {pass_rate_str(c['passed'], c['failed']):>8} {c['infra_error']:>13}")
        for k in total:
            total[k] += c[k]
    print(f"{'TOTAL':30}{' ' * 6 if args.fill else ''} "
          f"{pass_rate_str(total['passed'], total['failed']):>8} {total['infra_error']:>13}")

    if stop_reason:
        print(f"\nSTOPPED EARLY: {stop_reason}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
