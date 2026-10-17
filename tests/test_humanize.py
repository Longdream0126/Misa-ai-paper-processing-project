from __future__ import annotations

import unittest
from pathlib import Path

from misa import humanize

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


class EnglishHumanizeTests(unittest.TestCase):
    def setUp(self):
        self.text = sample("en_ai_product.txt")

    def test_cliche_removed(self):
        out = humanize(self.text).text
        low = out.lower()
        for phrase in ("delve into", "it is important to note", "furthermore", "moreover"):
            self.assertNotIn(phrase, low)

    def test_contractions_added(self):
        out = humanize(self.text).text
        self.assertIn("it's", out.lower())

    def test_score_drops(self):
        res = humanize(self.text)
        self.assertLess(res.after.score, res.before.score)
        self.assertLess(res.delta, 0)

    def test_retention_reasonable(self):
        res = humanize(self.text)
        self.assertGreater(res.retention, 0.6)

    def test_text_preserved_when_clean(self):
        clean = "The cat sat on the mat. It was warm."
        res = humanize(clean)
        self.assertEqual(res.text.strip(), clean.strip())

    def test_code_fence_untouched(self):
        text = "We leverage this.\n\n```python\nutilize(leverage)\n```\n"
        out = humanize(text).text
        self.assertIn("utilize(leverage)", out)

    def test_light_level_skips_contractions(self):
        text = sample("en_ai_guide.txt")
        light = humanize(text, level="light").text
        standard = humanize(text, level="standard").text
        self.assertIn("you are", light)
        self.assertIn("you're", standard)

    def test_invalid_level(self):
        with self.assertRaises(ValueError):
            humanize("test", level="extreme")

    def test_idempotent(self):
        once = humanize(self.text).text
        twice = humanize(once).text
        self.assertEqual(once.strip(), twice.strip())

    def test_explicit_lang(self):
        res = humanize(self.text, lang="en")
        self.assertEqual(res.lang, "en")

    def test_changes_recorded(self):
        res = humanize(self.text)
        self.assertTrue(res.changes)
        self.assertTrue(all(c.count > 0 for c in res.changes))

    def test_warnings_present(self):
        res = humanize(self.text)
        self.assertTrue(res.warnings)


class ChineseHumanizeTests(unittest.TestCase):
    def setUp(self):
        self.text = sample("zh_ai_report.txt")

    def test_cliche_replaced(self):
        out = humanize(self.text).text
        self.assertNotIn("值得注意的是", out)
        self.assertNotIn("综上所述", out)
        self.assertNotIn("首先，", out)

    def test_score_drops(self):
        res = humanize(self.text)
        self.assertLess(res.after.score, res.before.score)

    def test_pair_structure_not_split(self):
        text = "只有把技术、流程与组织三者结合起来，才能真正发挥数据的价值，为企业发展奠定基础。"
        out = humanize(text, level="strong").text
        self.assertIn("只有", out)
        self.assertIn("才能", out)
        self.assertEqual(out.count("。"), 1)

    def test_short_text_stable(self):
        out = humanize("这段文字很短。", level="strong").text
        self.assertTrue(out.strip())


class StructureTests(unittest.TestCase):
    def test_to_dict(self):
        import json

        d = humanize(sample("en_ai_guide.txt")).to_dict()
        json.dumps(d, ensure_ascii=False)
        for key in ("text", "before", "after", "changes", "warnings", "retention"):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
