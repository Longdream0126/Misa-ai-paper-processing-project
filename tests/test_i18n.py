from __future__ import annotations

import unittest
from pathlib import Path

from misa import analyze, i18n

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


class CatalogueTests(unittest.TestCase):
    def test_all_locales_complete(self):
        missing = i18n.missing()
        for loc, keys in missing.items():
            with self.subTest(locale=loc):
                self.assertEqual(keys, [], f"{loc} is missing {len(keys)} keys")

    def test_four_locales(self):
        self.assertEqual(list(i18n.LOCALES), ["en", "zh-CN", "zh-TW", "ja"])
        self.assertEqual(set(i18n.LOCALE_NAMES), set(i18n.LOCALES))

    def test_normalize(self):
        self.assertEqual(i18n.normalize("zh"), "zh-CN")
        self.assertEqual(i18n.normalize("zh_CN"), "zh-CN")
        self.assertEqual(i18n.normalize("zh-Hant"), "zh-TW")
        self.assertEqual(i18n.normalize("en-US"), "en")
        self.assertEqual(i18n.normalize("ja-JP"), "ja")
        self.assertIsNone(i18n.normalize("fr"))

    def test_resolve_falls_back_to_english(self):
        self.assertEqual(i18n.resolve("fr"), i18n.system_locale() or "en")
        self.assertEqual(i18n.resolve("en"), "en")

    def test_translation_differs_per_locale(self):
        seen = {loc: i18n.t("tab.analyze", loc) for loc in i18n.LOCALES}
        self.assertEqual(seen["en"], "Analyze")
        self.assertEqual(seen["zh-CN"], "分析")
        self.assertEqual(seen["ja"], "分析")
        self.assertGreaterEqual(len(set(seen.values())), 2)

    def test_formatting(self):
        self.assertIn("7", i18n.t("stat.sentences", "en", n=7))
        self.assertIn("7", i18n.t("stat.sentences", "ja", n=7))

    def test_unknown_key_returns_key(self):
        self.assertEqual(i18n.t("no.such.key", "en"), "no.such.key")

    def test_strings_export(self):
        s = i18n.strings("ja")
        self.assertEqual(s["tab.humanize"], "書き換え")
        self.assertNotIn("{", s["tab.analyze"])


class LocalizedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.text = (SAMPLES / "en_ai_product.txt").read_text(encoding="utf-8")

    def test_english_default(self):
        d = analyze(self.text).to_dict("en")
        self.assertEqual(d["band"], "Strongly AI-like")
        self.assertTrue(any(f["label"] == "Cliché density" for f in d["features"]))

    def test_chinese_output(self):
        d = analyze(self.text).to_dict("zh-CN")
        self.assertEqual(d["band"], "高度 AI 化")
        self.assertTrue(any(f["label"] == "套话密度" for f in d["features"]))
        self.assertIn("启发式", d["disclaimer"])

    def test_japanese_output(self):
        d = analyze(self.text).to_dict("ja")
        self.assertIn("信頼度", d["confidence"])
        self.assertTrue(any("定型表現" in f["label"] for f in d["features"]))

    def test_traditional_chinese_output(self):
        zh = analyze(self.text).to_dict("zh-CN")
        tw = analyze(self.text).to_dict("zh-TW")
        self.assertNotEqual(zh["disclaimer"], tw["disclaimer"])

    def test_flags_localized(self):
        en = analyze(self.text).to_dict("en")
        zh = analyze(self.text).to_dict("zh-CN")
        self.assertTrue(en["flags"])
        self.assertNotEqual(en["flags"][0]["title"], zh["flags"][0]["title"])


if __name__ == "__main__":
    unittest.main()
