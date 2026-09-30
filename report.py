import argparse
from collections import Counter, defaultdict
from pathlib import Path

from harness.analysis import (auto_failure_label, calibration, load_labels, load_runs,
                              model_of, outcome_of, pass_at_k, scored)


def fmt(value, spec, empty="-"):
    return empty if value is None else format(value, spec)


def table(headers, rows, markdown):
    if markdown:
        lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
        lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
        return "\n".join(lines)
    widths = [max(len(str(x)) for x in [h] + [row[i] for row in rows]) for i, h in enumerate(headers)]
    line = lambda cells: "  ".join(str(c).ljust(w) if i == 0 else str(c).rjust(w)
                                   for i, (c, w) in enumerate(zip(cells, widths)))
    out = [line(headers), "-" * len(line(headers))]
    return "\n".join(out + [line(row) for row in rows])


def summary_section(records, markdown):
    groups = defaultdict(list)
    for r in records:
        groups[(r["task_id"], r["agent"], model_of(r))].append(r)

    rows, any_salvaged = [], False
    for (task_id, agent, model), rs in sorted(groups.items()):
        infra = len(rs) - len(scored(rs))
        ok = scored(rs)
        if ok:
            k = len(ok)
            infos = [r.get("agent_info") or {} for r in ok]
            passes = sum(1 for r in ok if outcome_of(r) == "passed")
            tokens = sum(i.get("prompt_tokens", 0) + i.get("completion_tokens", 0) for i in infos) / k
            confs = [i["confidence"] for i in infos if i.get("confidence") is not None]
            salvaged = sum(i.get("salvaged_tool_calls", 0) for i in infos)
            any_salvaged = any_salvaged or salvaged > 0
            rows.append([task_id, agent, model, len(rs), f"{passes / k:.0%}",
                         f"{sum(r['num_steps'] for r in ok) / k:.1f}",
                         f"{tokens:.0f}" + ("*" if salvaged else ""),
                         fmt(sum(confs) / len(confs) if confs else None, ".2f"),
                         f"{salvaged / k:.1f}", infra])
        else:
            rows.append([task_id, agent, model, len(rs), "-", "-", "-", "-", "-", infra])

    headers = ["TASK", "AGENT", "MODEL", "TRIALS", "PASS", "AVG STEPS", "AVG TOKENS",
               "AVG CONF", "AVG SALV", "INFRA"]
    notes = ["PASS and averages exclude infra-error trials (LLM API or Docker failures)."]
    if any_salvaged:
        notes.append("* Token count is a lower bound: salvaged tool-call turns return no usage data.")
    return "Summary by task", table(headers, rows, markdown), notes


def pass_at_k_section(records, markdown, ks=(1, 3)):
    groups = defaultdict(lambda: defaultdict(list))
    for r in scored(records):
        if r["agent"] == "llm":
            groups[model_of(r)][r["task_id"]].append(r)

    rows = []
    for model, tasks in sorted(groups.items()):
        for task_id, rs in sorted(tasks.items()):
            n, c = len(rs), sum(1 for r in rs if outcome_of(r) == "passed")
            rows.append([model, task_id, n, c] +
                        [fmt(pass_at_k(n, c, k) if k <= n else None, ".2f") for k in ks])
        means = []
        for k in ks:
            vals = [pass_at_k(len(rs), sum(1 for r in rs if outcome_of(r) == "passed"), k)
                    for rs in tasks.values() if len(rs) >= k]
            means.append(fmt(sum(vals) / len(vals) if vals else None, ".2f"))
        rows.append([model, "MEAN", "", ""] + means)

    headers = ["MODEL", "TASK", "N", "PASSED"] + [f"PASS@{k}" for k in ks]
    notes = ["Unbiased estimator: pass@k = 1 - C(n-c, k) / C(n, k). "
             "'-' means fewer than k scored trials. MEAN averages over tasks with at least k "
             "scored trials. LLM agent only; infra errors excluded."]
    return "pass@k", table(headers, rows, markdown), notes


def calibration_section(records, markdown):
    by_model = defaultdict(list)
    for r in records:
        if r["agent"] == "llm":
            by_model[model_of(r)].append(r)

    rows, bin_rows = [], []
    for model, rs in sorted(by_model.items()):
        cal = calibration(rs)
        rows.append([model, cal["n"], cal["no_confidence"], fmt(cal["brier"], ".3f"), fmt(cal["ece"], ".3f")])
        for b in cal["bins"]:
            if b["count"]:
                bin_rows.append([model, f"{b['lo']:.1f}-{b['hi']:.1f}", b["count"],
                                 f"{b['avg_conf']:.2f}", f"{b['accuracy']:.2f}"])

    text = table(["MODEL", "WITH CONF", "NO CONF", "BRIER", "ECE"], rows, markdown)
    if bin_rows:
        text += "\n\n" + table(["MODEL", "CONF BIN", "COUNT", "AVG CONF", "ACCURACY"], bin_rows, markdown)
    notes = ["Brier: mean of (confidence - outcome)^2, lower is better. ECE: 5 equal-width bins, "
             "weighted gap between average confidence and accuracy, lower is better.",
             "Only trials where the agent declared done have a confidence. NO CONF trials "
             "(step limit or invalid replies) are excluded from Brier and ECE."]
    return "Calibration", text, notes


def failure_section(records, markdown, labels):
    auto = defaultdict(Counter)
    manual = defaultdict(Counter)
    for r in records:
        if r["agent"] != "llm":
            continue
        label = auto_failure_label(r)
        if label is None:
            continue
        auto[model_of(r)][label] += 1
        if r["trial_id"] in labels:
            manual[model_of(r)][labels[r["trial_id"]]] += 1

    auto_labels = ["overconfident_done", "max_steps", "parse_errors", "other"]
    rows = [[m] + [c[l] for l in auto_labels] + [sum(c.values())] for m, c in sorted(auto.items())]
    text = table(["MODEL"] + auto_labels + ["TOTAL FAILED"], rows, markdown)
    if manual:
        mrows = [[m, label, n] for m, c in sorted(manual.items()) for label, n in c.most_common()]
        text += "\n\n" + table(["MODEL", "MANUAL LABEL", "COUNT"], mrows, markdown)
    notes = ["overconfident_done: the agent declared the task complete but the tests failed.",
             "Manual labels come from labels.json (trial_id -> label)."]
    return "Failure taxonomy", text, notes


def main():
    parser = argparse.ArgumentParser(description="Summarize saved trial records in runs/")
    parser.add_argument("--markdown", action="store_true", help="Also write results/REPORT.md")
    args = parser.parse_args()

    records = load_runs()
    if not records:
        print("No runs found in runs/")
        return
    labels = load_labels()

    sections = [summary_section, pass_at_k_section, calibration_section]
    for markdown in ([False, True] if args.markdown else [False]):
        parts = []
        for section in sections + [lambda recs, md: failure_section(recs, md, labels)]:
            title, text, notes = section(records, markdown)
            if markdown:
                parts.append(f"## {title}\n\n{text}\n\n" + "\n".join(f"- {n}" for n in notes))
            else:
                parts.append(f"=== {title} ===\n{text}\n" + "\n".join(notes))
        if markdown:
            Path("results").mkdir(exist_ok=True)
            body = "# Results\n\n" + "\n\n".join(parts) + "\n"
            Path("results/REPORT.md").write_text(body)
            print("Wrote results/REPORT.md")
        else:
            print("\n\n".join(parts))


if __name__ == "__main__":
    main()
