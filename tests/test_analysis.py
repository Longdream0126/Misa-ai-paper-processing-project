from __future__ import annotations

import unittest
from pathlib import Path

from misa.analysis import analyze
from misa.analysis.features import _calibrate
from misa.analysis.tokenize import (
    detect_language,
    en_words,
    make_matcher,
    split_paragraphs,
    split_sentences,
)

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


class TokenizeTests(unittest.TestCase):
    def test_abbreviation_not_split(self):
        sents = split_sentences("Dr. Smith went home. He slept well.", "en")
        self.assertEqual(len(sents), 2)
        self.assertTrue(sents[0].startswith("Dr. Smith"))

    def test_decimal_not_split(self):
        sents = split_sentences("The price was 3.5 dollars. Fine.", "en")
        self.assertEqual(len(sents), 2)

    def test_chinese_sentences(self):
        sents = split_sentences("第一句话。第二句话！第三句？", "zh")
        self.assertEqual(len(sents), 3)

    def test_language_detection(self):
        self.assertEqual(detect_language("这是一段中文。"), "zh")
        self.assertEqual(detect_language("This is English."), "en")
        self.assertEqual(detect_language("Python 3.15 里 dict 很快"), "en")

    def test_words(self):
        self.assertEqual(en_words("It's a test-case, 42."), ["it's", "a", "test", "case", "42"])

    def test_paragraphs(self):
        self.assertEqual(len(split_paragraphs("a\n\nb\n\n\nc")), 3)

    def test_matcher_counts_phrases(self):
        m = make_matcher("en")
        hits = m.find("We delve into the realm of ideas. Furthermore, we play a crucial role.")
        texts = [h.text.lower() for h in hits]
        self.assertIn("delve into", texts)
        self.assertIn("furthermore", texts)
        self.assertIn("play a crucial role", texts)

    def test_zh_matcher(self):
        m = make_matcher("zh")
        hits = m.find("值得注意的是，这个方案具有重要意义。")
        self.assertTrue(any("值得注意" in h.text for h in hits))


class ScoreTests(unittest.TestCase):
    def test_ai_samples_score_high(self):
        for name in ("en_ai_product.txt", "en_ai_guide.txt"):
            with self.subTest(name=name):
                self.assertGreater(analyze(sample(name)).score, 70)

    def test_human_samples_score_low(self):
        for name in ("en_human_diary.txt", "en_human_forum.txt"):
            with self.subTest(name=name):
                self.assertLess(analyze(sample(name)).score, 35)

    def test_chinese_samples(self):
        self.assertGreater(analyze(sample("zh_ai_report.txt")).score, 70)
        self.assertLess(analyze(sample("zh_human_post.txt")).score, 40)

    def test_language_detected(self):
        self.assertEqual(analyze(sample("zh_ai_report.txt")).lang, "zh")

    def test_empty_text(self):
        r = analyze("")
        self.assertEqual(r.score, 50)
        self.assertEqual(r.features, [])
        self.assertEqual(r.sentence_scores, [])

    def test_short_text_low_confidence(self):
        r = analyze("这是一个很短的句子。")
        self.assertIn(r.confidence, {"very_low", "low"})
        # 短文本不应该有句长变异这类需要多句的特征
        self.assertIsNone(r.feature("sent_cv"))

    def test_features_are_gated(self):
        r = analyze("One single short sentence.")
        keys = {f.key for f in r.features}
        self.assertNotIn("sent_cv", keys)
        self.assertNotIn("mattr", keys)

    def test_to_dict_serializable(self):
        import json
        d = analyze(sample("en_ai_guide.txt")).to_dict()
        json.dumps(d, ensure_ascii=False)
        for key in ("score", "features", "sentences", "stats", "flags", "disclaimer"):
            self.assertIn(key, d)

    def test_disclaimer_present(self):
        r = analyze("Some text here that is long enough to score.")
        self.assertIn("heuristic", r.disclaimer)

    def test_calibrate_monotonic(self):
        self.assertLess(_calibrate(0.1), _calibrate(0.5))
        self.assertLess(_calibrate(0.5), _calibrate(0.9))

    def test_calibration_override(self):
        from misa.analysis.calibration import Calibration

        text = sample("en_ai_product.txt")
        base = analyze(text)
        cal = Calibration(features={"cliche": {"human": 0.0, "ai": 1e6, "weight": 1.0}})
        tuned = analyze(text, calibration=cal)
        self.assertTrue(tuned.calibrated)
        self.assertNotEqual(base.score, tuned.score)
        self.assertLess(tuned.score, base.score)  # 锚点被拉到极高，套话不再显得异常


class SentenceTests(unittest.TestCase):
    def test_sentences_have_scores(self):
        r = analyze(sample("en_ai_product.txt"))
        self.assertTrue(r.sentence_scores)
        self.assertTrue(all(0 <= s.score <= 100 for s in r.sentence_scores))

    def test_ai_sentence_scores_higher(self):
        r = analyze(sample("en_ai_product.txt"))
        top = sorted(r.sentence_scores, key=lambda s: -s.score)[0]
        self.assertGreaterEqual(top.score, 60)
        self.assertTrue(top.reasons)


if __name__ == "__main__":
    unittest.main()
