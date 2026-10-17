from __future__ import annotations

import unittest

from misa.watermark.unicode_scan import clean_invisible, scan_invisible

ZWSP = "\u200b"
ZWNJ = "\u200c"
TAG_A = "\U000E0041"  # 标签字符 A
VS16 = "\ufe0f"


class ScanTests(unittest.TestCase):
    def test_clean_text_has_no_hits(self):
        res = scan_invisible("这是一段完全正常的中文，no hidden chars.")
        self.assertEqual(res["total"], 0)
        self.assertEqual(res["categories"], [])
        self.assertEqual(res["level"], "none")

    def test_zero_width_detected(self):
        res = scan_invisible(f"hello{ZWSP}world{ZWSP}again")
        self.assertGreaterEqual(res["total"], 2)
        keys = {c["key"] for c in res["categories"]}
        self.assertIn("zero_width", keys)
        cat = next(c for c in res["categories"] if c["key"] == "zero_width")
        self.assertEqual(cat["count"], 2)
        self.assertEqual(cat["chars"][0]["codepoint"], "U+200B")

    def test_tag_chars_high_risk(self):
        text = "正常文字" + TAG_A + TAG_A + TAG_A
        res = scan_invisible(text)
        keys = {c["key"]: c for c in res["categories"]}
        self.assertIn("tag", keys)
        self.assertEqual(keys["tag"]["risk"], "high")

    def test_long_run_flagged(self):
        text = "hidden" + ZWSP * 12 + "payload"
        res = scan_invisible(text)
        self.assertTrue(res["long_runs"])
        self.assertGreaterEqual(res["long_runs"][0]["length"], 8)
        self.assertEqual(res["level"], "high")

    def test_mixed_script(self):
        # 拉丁 p + 西里尔 а，外观几乎一样
        res = scan_invisible("p\u0430ypal account")
        self.assertTrue(res["mixed_script_words"])
        self.assertEqual(res["mixed_script_words"][0]["foreign"], "西里尔")

    def test_clean_default(self):
        text = f"a{ZWSP}b{TAG_A}c{ZWNJ}d"
        cleaned, info = clean_invisible(text)
        self.assertEqual(cleaned, "abcd")
        self.assertEqual(info["total"], 3)

    def test_clean_keeps_variation_selector_by_default(self):
        text = f"heart{VS16}"
        cleaned, info = clean_invisible(text)
        self.assertEqual(cleaned, text)
        self.assertEqual(info["total"], 0)

    def test_clean_all_mode(self):
        text = f"heart{VS16}{ZWSP}"
        cleaned, info = clean_invisible(text, mode="all")
        self.assertEqual(cleaned, "heart")
        self.assertEqual(info["total"], 2)

    def test_space_normalization(self):
        text = "hello\u00a0world"
        cleaned, info = clean_invisible(text)
        self.assertEqual(cleaned, "hello world")

    def test_report_is_json_serializable(self):
        import json

        json.dumps(scan_invisible(f"x{ZWSP}y"), ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
