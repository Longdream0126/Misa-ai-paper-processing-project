from __future__ import annotations

import unittest

from misa.analysis import tokenize
from misa.watermark.greenlist import GreenList, detect, detect_text
from misa.watermark.toy_lm import demo

from . import fixtures

KEY = "unit-test-key"


class GreenListTests(unittest.TestCase):
    def test_deterministic(self):
        a = GreenList(KEY).is_green("apple", "the")
        b = GreenList(KEY).is_green("apple", "the")
        self.assertEqual(a, b)

    def test_key_changes_mask(self):
        gl1, gl2 = GreenList(KEY), GreenList("other-key")
        differs = any(gl1.is_green(w, "the") != gl2.is_green(w, "the") for w in
                      ["alpha", "beta", "gamma", "delta", "epsilon"])
        self.assertTrue(differs)

    def test_gamma_ratio(self):
        gl = GreenList(KEY, gamma=0.25)
        words = [f"w{i:03d}" for i in range(2000)]
        ratio = sum(1 for w in words if gl.is_green(w, "context")) / len(words)
        self.assertAlmostEqual(ratio, 0.25, delta=0.05)


class DetectTests(unittest.TestCase):
    def test_watermarked_is_flagged(self):
        text = fixtures.make_watermarked_text(20, KEY)
        res = detect_text(text, KEY)
        self.assertEqual(res.n_pairs, 20)
        self.assertEqual(res.green, 20)
        self.assertGreater(res.z, 4)
        self.assertEqual(res.level, "strong")
        self.assertLess(res.p_value, 1e-3)

    def test_wrong_key_not_flagged(self):
        text = fixtures.make_watermarked_text(20, KEY)
        res = detect_text(text, "wrong-key")
        self.assertLess(abs(res.z), 4)

    def test_plain_text_not_flagged(self):
        words = "the quick brown fox jumps over the lazy dog and then it runs away into the field".split()
        res = detect(words, KEY)
        self.assertLess(abs(res.z), 3)
        self.assertEqual(res.level, "none")

    def test_too_short(self):
        res = detect(["only"], KEY)
        self.assertEqual(res.n_pairs, 0)
        self.assertIn("too short", res.verdict)

    def test_to_dict(self):
        res = detect_text(fixtures.make_watermarked_text(10, KEY), KEY)
        d = res.to_dict()
        for key in ("n_pairs", "green", "green_ratio", "z", "p_value", "verdict"):
            self.assertIn(key, d)


class DemoTests(unittest.TestCase):
    def test_demo_separates(self):
        d = demo(KEY, length=80, seed=3)
        self.assertLess(d["plain"]["z"], 3)
        self.assertGreater(d["marked"]["z"], 4)
        self.assertLess(d["marked_wrong_key"]["z"], 4)
        self.assertIn("plain_text", d)
        self.assertNotEqual(d["plain_text"], d["marked_text"])

    def test_demo_reports_wrong_key_spread(self):
        d = demo(KEY, length=120, seed=7)
        self.assertEqual(len(d["wrong_keys"]), 6)
        zs = [w["z"] for w in d["wrong_keys"]]
        self.assertLess(max(abs(z) for z in zs), 4)
        self.assertTrue(all(w["level"] != "strong" for w in d["wrong_keys"]))

    def test_demo_same_length(self):
        d = demo(KEY, length=60)
        a = len(tokenize.en_words(d["plain_text"]))
        b = len(tokenize.en_words(d["marked_text"]))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
