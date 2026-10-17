from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from misa.cli import main

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class AnalyzeCommandTests(unittest.TestCase):
    def test_file_ok(self):
        code, out, _ = run(["analyze", str(SAMPLES / "en_ai_product.txt"), "--no-color"])
        self.assertEqual(code, 0)
        self.assertIn("AI-likeness", out)

    def test_json(self):
        code, out, _ = run(["analyze", str(SAMPLES / "zh_ai_report.txt"), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertGreater(data["score"], 60)
        self.assertEqual(data["lang"], "zh")

    def test_literal_text(self):
        code, out, _ = run(["analyze", "A short sentence with no cliches at all.", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("score", json.loads(out))

    def test_fail_above(self):
        code, _, _ = run(["analyze", str(SAMPLES / "en_ai_product.txt"), "--fail-above", "10", "--json"])
        self.assertEqual(code, 3)

    def test_empty_input(self):
        code, _, err = run(["analyze", "   "])
        self.assertEqual(code, 2)
        self.assertIn("empty", err)


class HumanizeCommandTests(unittest.TestCase):
    def test_text_only(self):
        code, out, _ = run(["humanize", str(SAMPLES / "en_ai_product.txt"), "--text-only"])
        self.assertEqual(code, 0)
        self.assertNotIn("delve into", out.lower())
        self.assertNotIn("Furthermore", out)

    def test_write_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            code, _, err = run(["humanize", str(SAMPLES / "zh_ai_report.txt"), "-o", str(target)])
            self.assertEqual(code, 0)
            self.assertTrue(target.is_file())
            self.assertNotIn("值得注意的是", target.read_text(encoding="utf-8"))

    def test_json(self):
        code, out, _ = run(["humanize", str(SAMPLES / "en_ai_guide.txt"), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertLess(data["after"]["score"], data["before"]["score"])


class ScanCommandTests(unittest.TestCase):
    def test_scan_text_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.txt"
            p.write_text("hello\u200bworld", encoding="utf-8")
            code, out, _ = run(["scan", str(p), "--no-color"])
            self.assertEqual(code, 0)
            self.assertIn("Invisible-character scan", out)

    def test_scan_png_json(self):
        from . import fixtures

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.png"
            p.write_bytes(fixtures.build_png(texts={"Software": "Firefly"}))
            code, out, _ = run(["scan", str(p), "--json"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data[0]["metadata"]["kind"], "png")


class OtherCommandTests(unittest.TestCase):
    def test_watermark_json(self):
        code, out, _ = run(["watermark", "--json", "--length", "40"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertGreater(data["marked"]["z"], 3)

    def test_clean_stdout(self):
        code, out, _ = run(["clean", "a\u200bb"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "ab")

    def test_demo_runs(self):
        code, out, _ = run(["demo", "--no-color"])
        self.assertEqual(code, 0)
        self.assertIn("watermark demo", out)

    def test_calibrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "human").mkdir()
            (root / "ai").mkdir()
            for name in ("en_human_diary.txt", "en_human_forum.txt", "zh_human_note.txt"):
                (root / "human" / name).write_text((SAMPLES / name).read_text(encoding="utf-8"), encoding="utf-8")
            for name in ("en_ai_product.txt", "en_ai_guide.txt", "zh_ai_report.txt"):
                (root / "ai" / name).write_text((SAMPLES / name).read_text(encoding="utf-8"), encoding="utf-8")
            target = root / "calib.json"
            code, out, _ = run(["calibrate", str(root), "--write", str(target), "--json"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertIn("features", data)
            self.assertIsInstance(data["features"], dict)
            self.assertTrue(target.is_file())

    def test_version(self):
        with self.assertRaises(SystemExit) as ctx:
            run(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
