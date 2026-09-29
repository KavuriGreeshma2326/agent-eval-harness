import json
from collections import defaultdict
from pathlib import Path


def outcome_of(r: dict) -> str:
    """Outcome of a trial record. Old records (before the "outcome" field existed)
    count as infra_error if they have an error, otherwise passed/failed."""
    if r.get("outcome") in ("passed", "failed", "infra_error"):
        return r["outcome"]
    if r.get("error"):
        return "infra_error"
    return "passed" if r.get("passed") else "failed"


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
              f"{'AVG STEPS':>9} {'AVG TOKENS':>11} {'AVG CONF':>8} {'AVG SALV':>8} {'INFRA':>6}")
    print(header)
    print("-" * len(header))

    any_salvaged = False
    for (task_id, agent, model), rs in sorted(groups.items()):
        n = len(rs)
        infra = sum(1 for r in rs if outcome_of(r) == "infra_error")
        scored = [r for r in rs if outcome_of(r) != "infra_error"]
        passes = sum(1 for r in scored if outcome_of(r) == "passed")

        if scored:
            k = len(scored)
            pass_str = f"{passes / k:.0%}"
            avg_steps = f"{sum(r['num_steps'] for r in scored) / k:.1f}"
            infos = [r.get("agent_info") or {} for r in scored]
            avg_tokens_val = sum(i.get("prompt_tokens", 0) + i.get("completion_tokens", 0) for i in infos) / k
            confs = [i["confidence"] for i in infos if i.get("confidence") is not None]
            avg_conf = f"{sum(confs) / len(confs):.2f}" if confs else "-"
            salvaged = sum(i.get("salvaged_tool_calls", 0) for i in infos)
            avg_salv = f"{salvaged / k:.1f}"
            tokens_str = f"{avg_tokens_val:.0f}" + ("*" if salvaged else "")
            any_salvaged = any_salvaged or salvaged > 0
        else:
            pass_str = avg_steps = tokens_str = avg_conf = avg_salv = "-"

        print(f"{task_id[:24]:24} {agent:7} {model[-22:]:22} {n:>6} {pass_str:>6} "
              f"{avg_steps:>9} {tokens_str:>11} {avg_conf:>8} {avg_salv:>8} {infra:>6}")

    print("\nPASS and averages exclude infra-error trials (LLM API or Docker failures).")
    if any_salvaged:
        print("* Token count is a lower bound: salvaged tool-call turns return no usage data.")


if __name__ == "__main__":
    main()
