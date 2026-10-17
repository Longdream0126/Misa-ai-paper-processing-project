"""AI 写作信号分析引擎。

不是"AI 检测器"——没有任何本地统计量能可靠判定文本作者。这里做的是：
把检测产品常用的那几类信号（句长分布、用词丰富度、套话密度、虚词/缩略
比例、可压缩性）算出来，加权成一个 0-100 的"AI 相似度"，并逐项解释它是
怎么来的，让你自己判断这份文本像不像机器写的。

分数高 = 更像"AI 默认文风"，而不是"一定是 AI 写的"。
"""

from __future__ import annotations

import math
import re
import zlib
from collections import Counter
from dataclasses import dataclass, field

from .. import i18n
from . import lexicons, tokenize

DISCLAIMER = i18n.CATALOG["app.disclaimer"]["en"]


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _cv(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var) / mean


def _entropy(values: list[int], bins: list[tuple[int, int]]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    counts = [0] * len(bins)
    for v in values:
        for i, (lo, hi) in enumerate(bins):
            if lo <= v <= hi:
                counts[i] += 1
                break
    total = sum(counts)
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c:
            p = c / total
            h -= p * math.log2(p)
    max_h = math.log2(len(bins))
    return h / max_h if max_h else 0.0


def _mattr(words: list[str], window: int = 50) -> float:
    n = len(words)
    if n <= window:
        return len(set(words)) / n if n else 0.0
    ratios = []
    for i in range(0, n - window + 1, max(1, window // 2)):
        chunk = words[i:i + window]
        ratios.append(len(set(chunk)) / window)
    return sum(ratios) / len(ratios) if ratios else 0.0


def _compress_ratio(text: str) -> float:
    raw = text.encode("utf-8")
    if not raw:
        return 0.0
    return len(zlib.compress(raw, 9)) / len(raw)


def _repeat_rate(items: list[str]) -> float:
    if not items:
        return 0.0
    return 1.0 - len(set(items)) / len(items)


def _readability_en(text: str) -> float:
    sentences = max(1, len(tokenize.split_sentences_en(text)))
    words = tokenize.en_words(text)
    if not words:
        return 0.0
    syl = sum(tokenize.syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syl / len(words))


@dataclass
class Feature:
    """One measurable signal. Text lives in i18n, keyed by ``key``."""

    key: str
    value: float
    human_anchor: float
    ai_anchor: float
    weight: float
    unit_key: str = ""

    @property
    def sub(self) -> float:
        """0 at the human anchor, 1 at the AI anchor, linear in between."""
        span = self.ai_anchor - self.human_anchor
        if abs(span) < 1e-9:
            return 0.0
        return _clamp01((self.value - self.human_anchor) / span)

    def label(self, locale: str | None = None) -> str:
        return i18n.t(f"feat.{self.key}.label", locale)

    def detail(self, locale: str | None = None) -> str:
        return i18n.t(f"feat.{self.key}.detail", locale)

    def unit(self, locale: str | None = None) -> str:
        return i18n.t(f"unit.{self.unit_key}", locale) if self.unit_key else ""

    def to_dict(self, locale: str | None = None) -> dict:
        return {
            "key": self.key,
            "label": self.label(locale),
            "value": round(self.value, 4),
            "unit": self.unit(locale),
            "unit_key": self.unit_key,
            "human_anchor": self.human_anchor,
            "ai_anchor": self.ai_anchor,
            "weight": self.weight,
            "sub": round(self.sub, 4),
            "detail": self.detail(locale),
        }


@dataclass
class SentenceScore:
    index: int
    text: str
    score: int
    reasons: list[str] = field(default_factory=list)

    def to_dict(self, locale: str | None = None) -> dict:
        return {
            "index": self.index,
            "text": self.text,
            "score": self.score,
            "reasons": [_render_reason(r, locale) for r in self.reasons],
            "reason_keys": [r.get("kind") for r in self.reasons],
        }


@dataclass
class AnalysisResult:
    text: str
    lang: str
    score: int
    band: str
    band_key: str
    confidence: str
    features: list[Feature]
    sentence_scores: list[SentenceScore]
    stats: dict
    flags: list[dict]
    disclaimer: str = DISCLAIMER
    calibrated: bool = False

    @property
    def raw(self) -> float:
        total_w = sum(f.weight for f in self.features) or 1.0
        return sum(f.weight * f.sub for f in self.features) / total_w

    def feature(self, key: str) -> Feature | None:
        for f in self.features:
            if f.key == key:
                return f
        return None

    def to_dict(self, locale: str | None = None) -> dict:
        return {
            "lang": self.lang,
            "score": self.score,
            "band": i18n.t(f"result.band.{self.band_key}", locale),
            "band_key": self.band_key,
            "confidence": i18n.t(f"result.conf.{self.confidence}", locale),
            "confidence_key": self.confidence,
            "raw": round(self.raw, 4),
            "features": [f.to_dict(locale) for f in self.features],
            "sentences": [s.to_dict(locale) for s in self.sentence_scores],
            "stats": self.stats,
            "flags": [_render_flag(fl, locale) for fl in self.flags],
            "calibrated": self.calibrated,
            "disclaimer": i18n.t("app.disclaimer", locale),
        }


BANDS = [
    (0, 20, "human"),
    (20, 40, "lean_human"),
    (40, 60, "mixed"),
    (60, 80, "lean_ai"),
    (80, 101, "ai"),
]

def _band(score: int) -> str:
    for lo, hi, key in BANDS:
        if lo <= score < hi:
            return key
    return "ai"


SENT_BINS = [(1, 8), (9, 16), (17, 24), (25, 32), (33, 40), (41, 56), (57, 9999)]
ZH_SENT_BINS = [(1, 10), (11, 18), (19, 26), (27, 34), (35, 44), (45, 60), (61, 9999)]


def _transition_starts(sentences: list[str]) -> int:
    hits = 0
    for s in sentences:
        low = s.lower().strip(" \"'“‘(")
        for t in lexicons.EN_TRANSITIONS:
            if low.startswith(t):
                hits += 1
                break
    return hits


def _opener_dup_rate(sentences: list[str]) -> float:
    openers = []
    for s in sentences:
        words = tokenize.en_words(s)[:2]
        if words:
            openers.append(" ".join(words))
    if not openers:
        return 0.0
    return 1.0 - len(set(openers)) / len(openers)


def _nominalization_rate(words: list[str], n_words: int) -> float:
    if not n_words:
        return 0.0
    count = sum(1 for w in words if len(w) >= 7 and w.endswith(lexicons.EN_NOMINAL_SUFFIXES))
    return count / n_words * 100


def _per100(count: float, units: int) -> float:
    return count / units * 100 if units else 0.0


def analyze(text: str, lang: str | None = None, calibration=None) -> AnalysisResult:
    """对一段文本打分（0-100，越高越像 AI 默认文风）。

    calibration: 可选的 analysis.calibration.Calibration，用自定义语料拟合的锚点/权重。
    """
    lang = lang or tokenize.detect_language(text)
    text = text.strip()
    matcher = tokenize.make_matcher(lang)
    paragraphs = tokenize.split_paragraphs(text)
    sentences = tokenize.split_sentences(text, lang)
    sindex = tokenize.SentenceIndex(text, sentences)
    hits = matcher.find(text)

    features: list[Feature] = []
    flags: list[dict] = []

    para_sent_counts = [len(tokenize.split_sentences(p, lang)) for p in paragraphs]
    sent_lens = [tokenize.sentence_length(s, lang) for s in sentences]
    sent_lens = [n for n in sent_lens if n > 0]

    stats: dict = {
        "paragraphs": len(paragraphs),
        "sentences": len(sentences),
        "cliche_hits": len(hits),
        "cliche_examples": _top_cliches(hits),
    }

    if lang == "zh":
        chars = tokenize.zh_chars(text)
        n_units = len(chars)
        stats["characters"] = len(text)
        stats["units"] = n_units
        stats["unit_key"] = "char"
        stats["avg_sentence_len"] = round(sum(sent_lens) / len(sent_lens), 1) if sent_lens else 0
        _zh_features(features, text, characters=chars, n_units=n_units, sent_lens=sent_lens,
                     para_sent_counts=para_sent_counts, hits=hits, stats=stats)
    else:
        words = tokenize.en_words(text)
        n_units = len(words)
        stats["words"] = n_units
        stats["units"] = n_units
        stats["unit_key"] = "word"
        stats["avg_sentence_len"] = round(sum(sent_lens) / len(sent_lens), 1) if sent_lens else 0
        stats["readability_flesch"] = round(_readability_en(text), 1)
        _en_features(features, text, words=words, n_units=n_units, sent_lens=sent_lens,
                     paragraphs=paragraphs, para_sent_counts=para_sent_counts,
                     sentences=sentences, hits=hits, stats=stats)

    if lang == "zh":
        zh_chars_all = tokenize.zh_chars(text)
        stats["type_token_ratio"] = round(len(set(zh_chars_all)) / max(1, len(zh_chars_all)), 3)
    else:
        all_words = tokenize.en_words(text)
        stats["type_token_ratio"] = round(len(set(all_words)) / max(1, len(all_words)), 3)
    stats["compressibility"] = round(_compress_ratio(text), 3)

    calibrated = False
    if calibration is not None:
        calibration.apply(features)
        calibrated = True

    raw = (sum(f.weight * f.sub for f in features) / sum(f.weight for f in features)) if features else 0.5
    confidence, factor = _confidence(n_units, lang, len(sentences))
    score = _calibrate(raw, factor) if features else 50
    band_key = _band(score)

    final_score = score
    flags.extend(_build_flags(features, hits, sentences, para_sent_counts, n_units, lang))
    sentence_scores = _sentence_scores(sentences, lang, matcher, sent_lens, sindex)

    return AnalysisResult(
        text=text,
        lang=lang,
        score=final_score,
        band=band_key,
        band_key=band_key,
        confidence=confidence,
        features=features,
        sentence_scores=sentence_scores,
        stats=stats,
        flags=flags,
        calibrated=calibrated,
    )


def _top_cliches(hits: list[tokenize.PhraseHit], limit: int = 6) -> list[dict]:
    counter: Counter[str] = Counter()
    weights: dict[str, float] = {}
    for h in hits:
        key = h.text.lower().strip()
        counter[key] += 1
        weights[key] = h.weight
    out = []
    for phrase, count in counter.most_common(limit):
        out.append({"phrase": phrase, "count": count, "weight": weights[phrase]})
    return out


def _confidence(n_units: int, lang: str, n_sentences: int) -> tuple[str, float]:
    if lang == "zh":
        thresholds = (300, 140, 60)
    else:
        thresholds = (180, 90, 40)
    if n_units >= thresholds[0] and n_sentences >= 3:
        return "high", 1.0
    if n_units >= thresholds[1] and n_sentences >= 2:
        return "medium", 0.82
    if n_units >= thresholds[2]:
        return "low", 0.6
    return "very_low", 0.38


def _calibrate(raw: float, factor: float = 1.0, center: float = 0.42, steep: float = 7.5) -> int:
    """把加权子分压成 0-100；样本不足时向 50 收缩。"""
    logistic = 1.0 / (1.0 + math.exp(-steep * (raw - center)))
    pct = 50.0 + (logistic * 100.0 - 50.0) * factor
    return int(round(max(0.0, min(100.0, pct))))


def _en_features(
    features: list[Feature],
    text: str,
    words: list[str],
    n_units: int,
    sent_lens: list[int],
    paragraphs: list[str],
    para_sent_counts: list[int],
    sentences: list[str],
    hits: list[tokenize.PhraseHit],
    stats: dict,
) -> None:
    n_sent = max(1, len(sentences))
    cliche = _per100(sum(h.weight for h in hits), n_units)
    contraction = _per100(tokenize.count_contractions(text), n_units)
    sent_cv = _cv([float(n) for n in sent_lens])
    sent_ent = _entropy(sent_lens, SENT_BINS)
    nom = _nominalization_rate(words, n_units)
    trans = _per100(_transition_starts(sentences), n_sent)
    para_cv = _cv([float(n) for n in para_sent_counts])
    trigrams = [f"{a} {b} {c}" for a, b, c in zip(words, words[1:], words[2:])]
    tri_rep = _repeat_rate(trigrams)
    mattr = _mattr(words)
    counts = Counter(words)
    hapax = sum(1 for w, c in counts.items() if c == 1) / max(1, len(counts))
    punct = tokenize.count_punctuation(text)
    punct_div = _punct_diversity(punct)
    word_len = sum(len(w) for w in words) / n_units if n_units else 0
    informal = _per100(sum(1 for w in words if w in lexicons.EN_INFORMAL), n_units)
    question = _per100(text.count("?") + text.count("？"), n_sent)
    opener_dup = _opener_dup_rate(sentences)
    short_rate = sum(1 for n in sent_lens if n <= 8) / max(1, len(sent_lens))

    def add(feature: Feature, need_units: int = 0, need_sents: int = 0,
            need_paras: int = 0) -> None:
        """样本不足的特征直接不参与评分，避免用小样本算出极端值。"""
        if n_units < need_units or len(sentences) < need_sents or len(paragraphs) < need_paras:
            return
        features.append(feature)

    add(Feature("cliche", cliche, 0.0, 1.8, 0.19, "per100w"), need_units=12)
    add(Feature("contraction", contraction, 1.6, 0.15, 0.12, "per100w"), need_units=35)
    add(Feature("sent_cv", sent_cv, 0.62, 0.27, 0.15, "cv"), need_sents=4)
    add(Feature("nominalization", nom, 1.8, 4.2, 0.09, "per100w"), need_units=40)
    add(Feature("transition", trans, 8.0, 34.0, 0.10, "per100s"), need_sents=4)
    add(Feature("short", short_rate, 0.14, 0.02, 0.09, "ratio"), need_sents=4)
    add(Feature("trigram", tri_rep, 0.012, 0.05, 0.06, "ratio"), need_units=70)
    add(Feature("mattr", mattr, 0.80, 0.66, 0.04, "mattr"), need_units=90)
    add(Feature("hapax", hapax, 0.58, 0.40, 0.03, "ratio"), need_units=90)
    add(Feature("word_len", word_len, 4.3, 4.9, 0.03, "chars"), need_units=20)
    add(Feature("informal", informal, 1.8, 0.12, 0.06, "per100w"), need_units=35)
    add(Feature("question", question, 8.0, 1.5, 0.02, "per100s"), need_sents=6)
    add(Feature("opener", opener_dup, 0.03, 0.12, 0.02, "ratio"), need_sents=6)

    stats["contractions"] = int(tokenize.count_contractions(text))
    stats["paragraph_sentences"] = para_sent_counts
    stats["sent_len_cv"] = round(sent_cv, 3)
    stats["sent_len_entropy"] = round(sent_ent, 3)
    stats["punct_counts"] = punct
    stats["punct_diversity"] = round(punct_div, 3)
    stats["distinct_words"] = len(counts)


def _zh_features(
    features: list[Feature],
    text: str,
    characters: list[str],
    n_units: int,
    sent_lens: list[int],
    para_sent_counts: list[int],
    hits: list[tokenize.PhraseHit],
    stats: dict,
) -> None:
    n_sent = max(1, len(tokenize.split_sentences(text, "zh")))
    n_para = len(para_sent_counts)
    cliche = _per100(sum(h.weight for h in hits), n_units)
    sent_cv = _cv([float(n) for n in sent_lens])
    sent_ent = _entropy(sent_lens, ZH_SENT_BINS)
    para_cv = _cv([float(n) for n in para_sent_counts])
    bigrams = [characters[i] + characters[i + 1] for i in range(len(characters) - 1)]
    bigram_rep = _repeat_rate(bigrams)
    particle = _per100(sum(1 for c in characters if c in lexicons.ZH_PARTICLES), n_units)
    informal = _per100(sum(text.count(w) for w in lexicons.ZH_INFORMAL), n_units)
    punct = tokenize.count_punctuation(text)
    punct_div = _punct_diversity(punct)
    short_rate = sum(1 for n in sent_lens if n <= 12) / max(1, len(sent_lens))

    def add(feature: Feature, need_units: int = 0, need_sents: int = 0,
            need_paras: int = 0) -> None:
        if n_units < need_units or n_sent < need_sents or n_para < need_paras:
            return
        features.append(feature)

    add(Feature("cliche", cliche, 0.15, 2.4, 0.28, "per100w"), need_units=12)
    add(Feature("particle", particle, 1.2, 0.10, 0.16, "per100w"), need_units=25)
    add(Feature("short", short_rate, 0.15, 0.02, 0.14, "ratio"), need_sents=4)
    add(Feature("sent_cv", sent_cv, 0.44, 0.32, 0.10, "cv"), need_sents=4)
    add(Feature("informal", informal, 1.0, 0.08, 0.10, "per100w"), need_units=25)
    add(Feature("bigram", bigram_rep, 0.16, 0.30, 0.10, "ratio"), need_units=60)

    stats["particles"] = int(sum(1 for c in characters if c in lexicons.ZH_PARTICLES))
    stats["paragraph_sentences"] = para_sent_counts
    stats["sent_len_cv"] = round(sent_cv, 3)
    stats["sent_len_entropy"] = round(sent_ent, 3)
    stats["punct_counts"] = punct
    stats["punct_diversity"] = round(punct_div, 3)
    stats["distinct_chars"] = len(set(characters))


def _punct_diversity(counts: dict[str, int]) -> float:
    if not counts:
        return 0.0
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c:
            p = c / total
            h -= p * math.log2(p)
    return h / math.log2(12) if h else 0.0


def _build_flags(
    features: list[Feature],
    hits: list[tokenize.PhraseHit],
    sentences: list[str],
    para_sent_counts: list[int],
    n_units: int,
    lang: str,
) -> list[dict]:
    """Structured findings; the display layer turns them into sentences."""
    flags: list[dict] = []
    top = sorted(features, key=lambda f: f.weight * f.sub, reverse=True)
    for f in top[:4]:
        if f.sub >= 0.55:
            flags.append({
                "level": "high" if f.sub >= 0.8 else "medium",
                "type": "feature",
                "feature": f.key,
                "direction": "high" if f.ai_anchor > f.human_anchor else "low",
                "value": round(f.value, 2),
                "unit_key": f.unit_key,
            })

    if hits:
        flags.append({
            "level": "medium",
            "type": "cliche",
            "count": len(hits),
            "examples": [{"phrase": p["phrase"], "count": p["count"]} for p in _top_cliches(hits, 5)],
        })

    if lang == "en" and n_units >= 60:
        f = next((x for x in features if x.key == "contraction"), None)
        if f and f.value < 0.3:
            flags.append({"level": "medium", "type": "contraction"})
    return flags


def _render_flag(flag: dict, locale: str | None) -> dict:
    kind = flag.get("type")
    if kind == "feature":
        label = i18n.t(f"feat.{flag['feature']}.label", locale)
        unit = i18n.t(f"unit.{flag['unit_key']}", locale) if flag.get("unit_key") else ""
        value = f"{flag['value']:.0%}" if flag.get("unit_key") == "ratio" else f"{flag['value']:.2f}"
        shown = f"{value} {unit}".strip()
        detail = i18n.t(f"feat.{flag['feature']}.detail", locale)
        return {
            "level": flag["level"],
            "title": i18n.t(f"flag.{flag['direction']}", locale, label=label),
            "detail": f"{shown}. {detail}" if locale != "zh-CN" else f"{shown}。{detail}",
        }
    if kind == "cliche":
        examples = ", ".join(f"“{e['phrase']}”×{e['count']}" for e in flag["examples"])
        return {
            "level": flag["level"],
            "title": i18n.t("flag.cliche.title", locale),
            "detail": i18n.t("flag.cliche.detail", locale, n=flag["count"], examples=examples)
            + " " + i18n.t("flag.cliche.why", locale),
        }
    if kind == "contraction":
        return {
            "level": flag["level"],
            "title": i18n.t("flag.contraction.title", locale),
            "detail": i18n.t("flag.contraction.detail", locale),
        }
    return {"level": flag.get("level", "low"), "title": "", "detail": ""}


def _sentence_scores(
    sentences: list[str],
    lang: str,
    matcher: tokenize.PhraseMatcher,
    sent_lens: list[int],
    sindex: tokenize.SentenceIndex,
) -> list[SentenceScore]:
    if not sentences:
        return []
    lens = [max(1, tokenize.sentence_length(s, lang)) for s in sentences]
    mean_len = sum(lens) / len(lens)
    scores: list[SentenceScore] = []
    for i, s in enumerate(sentences):
        reasons: list[dict] = []
        hits = matcher.find(s)
        w = sum(h.weight for h in hits)
        s_cliche = _clamp01(w / 1.6)
        if w > 0:
            reasons.append({"kind": "cliche", "items": [h.text for h in hits[:3]]})
        if lang == "en":
            words = tokenize.en_words(s)
            nom = _per100(sum(1 for x in words if len(x) >= 7 and x.endswith(lexicons.EN_NOMINAL_SUFFIXES)), len(words)) if words else 0
            s_nom = _clamp01(nom / 6.0)
            if nom >= 6:
                reasons.append({"kind": "nominal", "value": round(nom)})
            s_contr = 0.0 if tokenize.count_contractions(s) else 1.0
            if s_contr and mean_len > 8:
                reasons.append({"kind": "no_contraction"})
            low = s.lower().strip(" \"'“‘(")
            s_trans = 1.0 if any(low.startswith(t) for t in lexicons.EN_TRANSITIONS) else 0.0
            if s_trans:
                reasons.append({"kind": "transition"})
            chars = list(s.lower())
        else:
            s_nom = 0.0
            s_contr = 0.0
            s_trans = 0.0
            chars = tokenize.zh_chars(s)
        # Predictability: higher character-bigram repetition means more templated.
        bigrams = [chars[j] + chars[j + 1] for j in range(len(chars) - 1)] if len(chars) > 1 else []
        s_pred = _clamp01(_repeat_rate(bigrams) * 2.2)
        # The closer a sentence is to the document mean length, the more uniform.
        dev = abs(lens[i] - mean_len) / max(4.0, mean_len * 0.75)
        s_uniform = 1.0 - _clamp01(dev)
        if s_uniform > 0.85 and len(sentences) >= 4:
            reasons.append({"kind": "uniform"})
        raw = 0.42 * s_cliche + 0.16 * s_nom + 0.12 * s_contr + 0.10 * s_trans + 0.10 * s_pred + 0.10 * s_uniform
        score = int(round(max(0.0, min(100.0, (raw - 0.08) / 0.72 * 100))))
        scores.append(SentenceScore(i, s, score, reasons[:3]))
    return scores


def _render_reason(reason: dict, locale: str | None) -> str:
    kind = reason.get("kind")
    if kind == "cliche":
        return i18n.t("reason.cliche", locale, items=", ".join(reason["items"]))
    if kind == "nominal":
        return i18n.t("reason.nominal", locale, n=reason["value"])
    return i18n.t(f"reason.{kind}", locale)
