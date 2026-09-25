import contextlib
import io
import json
import os
import tempfile
import unittest

from currencylint.cli import main


class CliOutputTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("Total due: USD 19.999\n")
            handle.write("Refund: $42.50-\n")
            handle.write("all good: USD 1.00\n")

    def tearDown(self):
        os.remove(self.path)

    def _run(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = main(list(args))
        return status, out.getvalue()

    def test_text_format_is_the_default(self):
        status, output = self._run(self.path)
        self.assertEqual(status, 1)
        lines = output.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith(f"{self.path}:1:"))
        self.assertTrue(lines[1].startswith(f"{self.path}:2:"))

    def test_json_format_emits_one_object_per_line(self):
        status, output = self._run("--format", "json", self.path)
        self.assertEqual(status, 1)
        lines = output.splitlines()
        self.assertEqual(len(lines), 2)

        first = json.loads(lines[0])
        self.assertEqual(first["path"], self.path)
        self.assertEqual(first["line"], 1)
        self.assertEqual(first["rule"], "bad-decimal-precision")

        second = json.loads(lines[1])
        self.assertEqual(second["line"], 2)
        self.assertEqual(second["rule"], "trailing-sign")

    def test_clean_input_exits_zero_with_no_output(self):
        fd, path = tempfile.mkstemp(text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("USD 1.00\n")
            status, output = self._run(path)
            self.assertEqual(status, 0)
            self.assertEqual(output, "")
        finally:
            os.remove(path)

    def test_invalid_format_choice_is_rejected(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                main(["--format", "xml", self.path])


if __name__ == "__main__":
    unittest.main()
