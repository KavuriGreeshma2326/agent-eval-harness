import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

import run

PER_MINUTE = ("RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model "
              "`openai/gpt-oss-120b` in organization `org_x` service tier `on_demand` on tokens per "
              "minute (TPM): Limit 8000, Used 7900, Requested 1200. Please try again in 9.5s.'}}")
PER_DAY = ("RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model "
           "`openai/gpt-oss-120b` in organization `org_x` service tier `on_demand` on tokens per "
           "day (TPD): Limit 200000, Used 199500, Requested 3000. Please try again in 17m1s.'}}")
DOCKER = "SandboxError: Docker build failed: cannot connect to the docker API"


def rec(outcome, error=None, task_id="t1", model=None):
    return {"trial_id": f"{task_id}-{outcome}", "task_id": task_id, "agent": "nop",
            "outcome": outcome, "passed": outcome == "passed", "error": error,
            "error_type": "llm_api" if error else None, "test_output": "", "num_steps": 1,
            "duration_sec": 0.1, "agent_info": {"model": model} if model else {}}


def scripted(records):
    queue, calls = list(records), []

    def trial_fn(task, agent, runs_dir):
        calls.append(task.id)
        return queue.pop(0)
    return trial_fn, calls


def batch(tasks, records, **kwargs):
    trial_fn, calls = scripted(records)
    sleeps = []
    kwargs.setdefault("trials", 2)
    summary, stop = run.run_batch([NS(id=t) for t in tasks], "nop", model="-", trial_fn=trial_fn,
                                  sleep_fn=sleeps.append, say=lambda *a: None, **kwargs)
    return summary, stop, calls, sleeps


class DetectionTests(unittest.TestCase):
    def test_per_minute_limit(self):
        r = rec("infra_error", PER_MINUTE)
        self.assertTrue(run.is_rate_limit(r))
        self.assertFalse(run.is_daily_limit(r))

    def test_daily_limit(self):
        self.assertTrue(run.is_daily_limit(rec("infra_error", PER_DAY)))

    def test_other_errors_are_not_rate_limits(self):
        self.assertFalse(run.is_rate_limit(rec("infra_error", DOCKER)))
        self.assertFalse(run.is_rate_limit(rec("passed")))
        self.assertFalse(run.is_daily_limit(rec("failed")))


class BatchTests(unittest.TestCase):
    def test_runs_requested_trials_per_task(self):
        summary, stop, calls, _ = batch(["t1", "t2"], [rec("passed"), rec("failed"),
                                                       rec("passed"), rec("passed")])
        self.assertIsNone(stop)
        self.assertEqual(calls, ["t1", "t1", "t2", "t2"])
        self.assertEqual(summary[0]["counts"], {"passed": 1, "failed": 1, "infra_error": 0})
        self.assertEqual(summary[1]["counts"], {"passed": 2, "failed": 0, "infra_error": 0})

    def test_per_minute_limit_waits_and_runs_a_fresh_trial(self):
        summary, stop, calls, sleeps = batch(["t1"], [rec("infra_error", PER_MINUTE), rec("passed")],
                                             trials=1)
        self.assertIsNone(stop)
        self.assertEqual(sleeps, [run.RATE_LIMIT_WAIT_SEC])
        self.assertEqual(calls, ["t1", "t1"])
        self.assertEqual(summary[0]["counts"], {"passed": 1, "failed": 0, "infra_error": 0})

    def test_rate_limit_waits_are_capped(self):
        records = [rec("infra_error", PER_MINUTE)] * (run.MAX_RATE_LIMIT_WAITS + 1)
        summary, stop, calls, sleeps = batch(["t1"], records, trials=1, max_infra_streak=5)
        self.assertEqual(len(sleeps), run.MAX_RATE_LIMIT_WAITS)
        self.assertEqual(summary[0]["counts"]["infra_error"], 1)

    def test_daily_limit_stops_immediately(self):
        summary, stop, calls, sleeps = batch(["t1", "t2"], [rec("passed"), rec("infra_error", PER_DAY)],
                                             trials=3)
        self.assertIn("daily rate limit", stop)
        self.assertEqual(calls, ["t1", "t1"])
        self.assertEqual(sleeps, [])
        self.assertEqual(len(summary), 1)  # t2 was never started

    def test_infra_streak_stops_the_run(self):
        summary, stop, calls, _ = batch(["t1", "t2"], [rec("infra_error", DOCKER)] * 3, trials=5)
        self.assertIn("3 infra errors in a row", stop)
        self.assertIn("Docker build failed", stop)
        self.assertEqual(len(calls), 3)

    def test_success_resets_the_streak(self):
        records = [rec("infra_error", DOCKER), rec("infra_error", DOCKER), rec("passed"),
                   rec("infra_error", DOCKER), rec("infra_error", DOCKER), rec("passed")]
        summary, stop, calls, _ = batch(["t1"], records, trials=6)
        self.assertIsNone(stop)
        self.assertEqual(summary[0]["counts"], {"passed": 2, "failed": 0, "infra_error": 4})


class FillTests(unittest.TestCase):
    def runs_dir(self, records):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for i, r in enumerate(records):
            (Path(tmp.name) / f"r{i}.json").write_text(json.dumps(r))
        (Path(tmp.name) / "sub").mkdir()
        (Path(tmp.name) / "sub" / "ignored.json").write_text(json.dumps(rec("passed")))
        return Path(tmp.name)

    def test_only_missing_trials_are_run(self):
        existing = [rec("passed"), rec("failed"), rec("infra_error", DOCKER)]  # 2 scored for t1
        summary, stop, calls, _ = batch(
            ["t1", "t2"], [rec("passed"), rec("passed"), rec("passed"), rec("failed")],
            trials=3, fill=True, runs_dir=self.runs_dir(existing))
        self.assertIsNone(stop)
        self.assertEqual(calls, ["t1", "t2", "t2", "t2"])  # one for t1, three for t2
        self.assertEqual([row["have"] for row in summary], [2, 0])

    def test_complete_tasks_are_skipped(self):
        existing = [rec("passed")] * 3
        summary, stop, calls, _ = batch(["t1"], [], trials=3, fill=True,
                                        runs_dir=self.runs_dir(existing))
        self.assertEqual(calls, [])
        self.assertEqual(summary[0]["have"], 3)

    def test_other_models_do_not_count(self):
        existing = [rec("passed", model="some/other-model")] * 3
        summary, stop, calls, _ = batch(["t1"], [rec("passed")] * 2, trials=2, fill=True,
                                        runs_dir=self.runs_dir(existing))
        self.assertEqual(len(calls), 2)
        self.assertEqual(summary[0]["have"], 0)

    def test_without_fill_existing_runs_are_ignored(self):
        existing = [rec("passed")] * 5
        summary, stop, calls, _ = batch(["t1"], [rec("passed")] * 2, trials=2,
                                        runs_dir=self.runs_dir(existing))
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
