import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, "-m", "verityflow", *args], cwd=str(ROOT),
                          capture_output=True, text=True)


class CliContractTests(unittest.TestCase):
    def test_missing_input_is_a_cli_error_not_a_traceback(self):
        r = run("graph", "-i", "definitely-missing.json")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("error:", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_output_directory_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "notes.json")
            src.write_text(json.dumps({"notes": []}), encoding="utf-8")
            out = Path(tmp, "nested", "report.json")
            r = run("graph", "-i", str(src), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())

    def test_version_works_after_the_subcommand(self):
        r = run("graph", "--version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("verityflow "))


if __name__ == "__main__":
    unittest.main()
