"""Analysis of saved trial records: outcomes, pass@k, calibration and failure labels."""
import json
from math import comb
from pathlib import Path

OUTCOMES = ("passed", "failed", "infra_error")
ECE_BINS = 5


def load_runs(runs_dir="runs"):
    """Load every trial record directly in runs_dir (runs/validate/ is not included)."""
    return [json.loads(p.read_text()) for p in sorted(Path(runs_dir).glob("*.json"))]


def load_labels(path="labels.json"):
    """Optional manual failure labels: a JSON object mapping trial_id to a label string."""
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def outcome_of(record):
    """Outcome of a trial record. Old records (before the "outcome" field existed)
    count as infra_error if they have an error, otherwise passed/failed."""
    if record.get("outcome") in OUTCOMES:
        return record["outcome"]
    if record.get("error"):
        return "infra_error"
    return "passed" if record.get("passed") else "failed"


def model_of(record):
    return (record.get("agent_info") or {}).get("model", "-")


def scored(records):
    """Trials that count toward pass rates: everything except infra errors."""
    return [r for r in records if outcome_of(r) != "infra_error"]


def pass_at_k(n, c, k):
    """Unbiased pass@k estimator (Chen et al., 2021): the probability that at least one
    of k trials drawn without replacement from n trials (c of them passing) passes."""
    if k > n:
        raise ValueError(f"k={k} is larger than the number of trials n={n}")
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def calibration(records, bins=ECE_BINS):
    """Brier score and expected calibration error (ECE) over scored trials that have a
    stated confidence. Trials that stopped without declaring done have no confidence and
    are counted separately, because leaving them out makes the agent look better calibrated."""
    records = scored(records)
    points = []
    no_confidence = 0
    for r in records:
        conf = (r.get("agent_info") or {}).get("confidence")
        if conf is None:
            no_confidence += 1
        else:
            points.append((float(conf), 1.0 if outcome_of(r) == "passed" else 0.0))

    result = {"n": len(points), "no_confidence": no_confidence,
              "brier": None, "ece": None, "bins": []}
    if not points:
        return result

    result["brier"] = sum((c - y) ** 2 for c, y in points) / len(points)
    ece = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        # Each bin is [lo, hi), except the last, which also includes 1.0.
        members = [(c, y) for c, y in points if lo <= c < hi or (i == bins - 1 and c == hi)]
        if not members:
            result["bins"].append({"lo": lo, "hi": hi, "count": 0, "avg_conf": None, "accuracy": None})
            continue
        avg_conf = sum(c for c, _ in members) / len(members)
        accuracy = sum(y for _, y in members) / len(members)
        ece += len(members) / len(points) * abs(avg_conf - accuracy)
        result["bins"].append({"lo": lo, "hi": hi, "count": len(members),
                               "avg_conf": avg_conf, "accuracy": accuracy})
    result["ece"] = ece
    return result


def auto_failure_label(record):
    """Automatic label for a failed trial, from how the agent stopped. None if not failed."""
    if outcome_of(record) != "failed":
        return None
    stop = (record.get("agent_info") or {}).get("stop_reason")
    if stop == "done":
        return "overconfident_done"  # declared the task complete, but the tests failed
    if stop in ("max_steps", "parse_errors"):
        return stop
    return "other"
