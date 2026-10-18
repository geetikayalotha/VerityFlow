import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verityflow.model import _confidence  # noqa: E402


class ConfidenceValidationTests(unittest.TestCase):
    def test_valid_values(self):
        self.assertEqual(_confidence(0.5, "l1"), 0.5)
        self.assertEqual(_confidence("0", "l1"), 0.0)
        self.assertEqual(_confidence(None, "l1"), 1.0)

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValueError) as ctx:
            _confidence("high", "l1")
        self.assertIn("l1", str(ctx.exception))

    def test_rejects_nan_and_out_of_range(self):
        for bad in ("NaN", float("inf"), 2.5, -0.1):
            with self.assertRaises(ValueError) as ctx:
                _confidence(bad, "l7")
            self.assertIn("l7", str(ctx.exception))


class InputBoundaryTests(unittest.TestCase):
    def test_array_is_rejected_with_the_source(self):
        import tempfile, json, os
        from verityflow.cli import _read_input
        fd, path = tempfile.mkstemp(suffix=".json")
        os.write(fd, json.dumps([1, 2, 3]).encode())
        os.close(fd)
        try:
            with self.assertRaises(ValueError) as ctx:
                _read_input(path)
            self.assertIn(path, str(ctx.exception))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
