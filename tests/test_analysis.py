import unittest

from harness.analysis import auto_failure_label, calibration, outcome_of, pass_at_k


def rec(outcome, confidence=None, stop_reason=None):
    return {"outcome": outcome, "agent_info": {"confidence": confidence, "stop_reason": stop_reason}}


class PassAtKTests(unittest.TestCase):
    def test_no_passes(self):
        self.assertEqual(pass_at_k(5, 0, 1), 0.0)
        self.assertEqual(pass_at_k(5, 0, 3), 0.0)

    def test_all_pass(self):
        self.assertEqual(pass_at_k(5, 5, 1), 1.0)
        self.assertEqual(pass_at_k(5, 5, 3), 1.0)

    def test_pass_at_1_is_pass_rate(self):
        self.assertAlmostEqual(pass_at_k(5, 2, 1), 0.4)

    def test_pass_at_3_by_hand(self):
        # n=5, c=2: 1 - C(3,3)/C(5,3) = 1 - 1/10
        self.assertAlmostEqual(pass_at_k(5, 2, 3), 0.9)
        # n=5, c=1: 1 - C(4,3)/C(5,3) = 1 - 4/10
        self.assertAlmostEqual(pass_at_k(5, 1, 3), 0.6)

    def test_enough_passes_guarantee_success(self):
        # n=5, c=3, k=3: only 2 failures, so any 3 trials include a pass
        self.assertEqual(pass_at_k(5, 3, 3), 1.0)

    def test_k_larger_than_n(self):
        with self.assertRaises(ValueError):
            pass_at_k(2, 1, 3)


class CalibrationTests(unittest.TestCase):
    def test_brier_by_hand(self):
        cal = calibration([rec("passed", 0.9), rec("failed", 0.8)])
        # ((0.9-1)^2 + (0.8-0)^2) / 2 = (0.01 + 0.64) / 2
        self.assertAlmostEqual(cal["brier"], 0.325)
        self.assertEqual(cal["n"], 2)

    def test_ece_by_hand(self):
        records = [rec("passed", 0.9), rec("failed", 0.9), rec("failed", 0.1), rec("passed", 0.3)]
        cal = calibration(records)
        # bins: [0,0.2): conf 0.1, acc 0 -> gap 0.1; [0.2,0.4): conf 0.3, acc 1 -> gap 0.7;
        # [0.8,1.0]: conf 0.9, acc 0.5 -> gap 0.4.  ECE = 0.25*0.1 + 0.25*0.7 + 0.5*0.4
        self.assertAlmostEqual(cal["ece"], 0.4)

    def test_confidence_one_goes_in_last_bin(self):
        cal = calibration([rec("passed", 1.0)])
        self.assertEqual(cal["bins"][-1]["count"], 1)
        self.assertAlmostEqual(cal["ece"], 0.0)

    def test_perfect_calibration(self):
        records = [rec("passed", 1.0), rec("failed", 0.0)]
        cal = calibration(records)
        self.assertAlmostEqual(cal["brier"], 0.0)
        self.assertAlmostEqual(cal["ece"], 0.0)

    def test_missing_confidence_and_infra_errors(self):
        records = [rec("passed", 0.9), rec("failed", None, "max_steps"),
                   rec("infra_error", 0.5)]
        cal = calibration(records)
        self.assertEqual(cal["n"], 1)
        self.assertEqual(cal["no_confidence"], 1)

    def test_no_points(self):
        cal = calibration([rec("failed", None, "max_steps")])
        self.assertIsNone(cal["brier"])
        self.assertIsNone(cal["ece"])


class FailureLabelTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(auto_failure_label(rec("failed", 0.9, "done")), "overconfident_done")
        self.assertEqual(auto_failure_label(rec("failed", None, "max_steps")), "max_steps")
        self.assertEqual(auto_failure_label(rec("failed", None, "parse_errors")), "parse_errors")
        self.assertIsNone(auto_failure_label(rec("passed", 0.9, "done")))
        self.assertIsNone(auto_failure_label(rec("infra_error")))


class OutcomeTests(unittest.TestCase):
    def test_legacy_records(self):
        self.assertEqual(outcome_of({"passed": True, "error": None}), "passed")
        self.assertEqual(outcome_of({"passed": False, "error": None}), "failed")
        self.assertEqual(outcome_of({"passed": False, "error": "RateLimitError"}), "infra_error")


if __name__ == "__main__":
    unittest.main()
