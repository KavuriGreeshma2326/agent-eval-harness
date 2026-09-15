import json
from collections import defaultdict
from pathlib import Path


def main():
    files = sorted(Path("runs").glob("*.json"))
    if not files:
        print("No runs found in runs/")
        return

    groups = defaultdict(list)
    for f in files:
        r = json.loads(f.read_text())
        info = r.get("agent_info") or {}
        model = info.get("model", "-")
        groups[(r["task_id"], r["agent"], model)].append(r)

    header = (f"{'TASK':24} {'AGENT':7} {'MODEL':22} {'TRIALS':>6} {'PASS':>6} "
              f"{'AVG STEPS':>9} {'AVG TOKENS':>10} {'AVG CONF':>8} {'ERRORS':>6}")
    print(header)
    print("-" * len(header))

    for (task_id, agent, model), rs in sorted(groups.items()):
        n = len(rs)
        passes = sum(1 for r in rs if r["passed"])
        avg_steps = sum(r["num_steps"] for r in rs) / n

        infos = [r.get("agent_info") or {} for r in rs]
        avg_tokens = sum(i.get("prompt_tokens", 0) + i.get("completion_tokens", 0) for i in infos) / n
        confs = [i["confidence"] for i in infos if i.get("confidence") is not None]
        avg_conf = f"{sum(confs) / len(confs):.2f}" if confs else "-"
        errors = sum(1 for r in rs if r["error"])

        print(f"{task_id[:24]:24} {agent:7} {model[-22:]:22} {n:>6} {passes / n:>6.0%} "
              f"{avg_steps:>9.1f} {avg_tokens:>10.0f} {avg_conf:>8} {errors:>6}")


if __name__ == "__main__":
    main()