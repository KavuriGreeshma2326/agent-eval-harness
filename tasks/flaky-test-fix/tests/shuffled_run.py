"""Run the project's tests in a shuffled order chosen by the seed (like CI does)."""
import random
import sys
import unittest

seed = int(sys.argv[1])
sys.path.insert(0, "/app/project")
suite = unittest.TestLoader().discover("/app/project", pattern="test_*.py")


def flatten(s):
    for item in s:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


tests = list(flatten(suite))
random.Random(seed).shuffle(tests)
result = unittest.TextTestRunner(verbosity=0, stream=open("/dev/null", "w")).run(unittest.TestSuite(tests))
print(f"seed {seed}: ran {result.testsRun}, failures {len(result.failures)}, errors {len(result.errors)}")
sys.exit(0 if result.wasSuccessful() and result.testsRun == 7 else 1)
