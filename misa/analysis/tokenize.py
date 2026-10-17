"""纯标准库的中英文分词 / 分句 / 分段落工具。

这里的"分词"不是语言学意义上的分词器：英文按正则取词，中文直接按字与
字符二元组处理。对本项目要算的统计量（句长变化、重复度、套话密度）来说，
这个精度足够，而且完全不需要下载模型。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import lexicons

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
EN_WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*|\d+(?:[.,]\d+)*")
EN_END_RE = re.compile(r"[.!?…]+[\"'”’)\]]*(?=\s|$)")
ZH_END_RE = re.compile(r"[。！？…!?]+[”’」』】）)]*")
ABBREV_TAIL_RE = re.compile(r"([A-Za-z](?:[A-Za-z.]*[A-Za-z])?)[.!?…]+[\"'”’)\]]*$")

PUNCT_CLASSES: dict[str, str] = {
    ".": "period", "。": "period", "．": "period",
    ",": "comma", "，": "comma", "、": "comma",
    ";": "semicolon", "；": "semicolon",
    ":": "colon", "：": "colon",
    "!": "exclaim", "！": "exclaim",
    "?": "question", "？": "question",
    "-": "dash", "—": "dash", "–": "dash", "－": "dash",
    "(": "paren", ")": "paren", "（": "paren", "）": "paren",
    '"': "quote", "“": "quote", "”": "quote", "'": "quote", "「": "quote",
    "」": "quote", "『": "quote", "』": "quote",
    "…": "ellipsis", "·": "middle", "/": "slash", "*": "star",
    "~": "tilde", "～": "tilde",
}

SENTENCE_END_CHARS = set(".!?…。！？")


def detect_language(text: str) -> str:
    """极简语言判定：CJK 字符占比 ≥ 25% 视为中文。"""
    cjk = len(CJK_RE.findall(text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = cjk + latin
    if total == 0:
        return "en"
    return "zh" if cjk / total >= 0.25 else "en"


def split_paragraphs(text: str) -> list[str]:
    """按空行切段；连续空行只切一次。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def _is_abbreviation(candidate: str) -> bool:
    m = ABBREV_TAIL_RE.search(candidate.strip())
    if not m:
        return False
    word = m.group(1)
    low = word.lower().replace(".", "")
    if not low:
        return False
    if low in {a.replace(".", "") for a in lexicons.EN_ABBREVIATIONS}:
        return True
    # 单个大写字母开头（人名缩写 J. K. Rowling）
    return len(word) == 1 and word.isupper()


def split_sentences_en(text: str) -> list[str]:
    out: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        start = 0
        for m in EN_END_RE.finditer(line):
            candidate = line[start:m.end()]
            if _is_abbreviation(candidate):
                continue
            piece = candidate.strip()
            if piece:
                out.append(piece)
            start = m.end()
        tail = line[start:].strip()
        if tail:
            out.append(tail)
    return out


def split_sentences_zh(text: str) -> list[str]:
    out: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        start = 0
        for m in ZH_END_RE.finditer(line):
            piece = line[start:m.end()].strip()
            if piece:
                out.append(piece)
            start = m.end()
        tail = line[start:].strip()
        if tail:
            out.append(tail)
    return out


def split_sentences(text: str, lang: str | None = None) -> list[str]:
    lang = lang or detect_language(text)
    return split_sentences_zh(text) if lang == "zh" else split_sentences_en(text)


def en_words(text: str) -> list[str]:
    return EN_WORD_RE.findall(text.lower())


def zh_chars(text: str) -> list[str]:
    return [c for c in text if CJK_RE.match(c)]


def count_units(text: str, lang: str | None = None) -> int:
    """一个"词量"单位：英文按词，中文按字（便于统一成"每百词"密度）。"""
    lang = lang or detect_language(text)
    return len(zh_chars(text)) if lang == "zh" else len(en_words(text))


def sentence_length(text: str, lang: str | None = None) -> int:
    lang = lang or detect_language(text)
    return len(zh_chars(text)) if lang == "zh" else len(en_words(text))


def count_punctuation(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        cls = PUNCT_CLASSES.get(ch)
        if cls:
            counts[cls] = counts.get(cls, 0) + 1
    return counts


def count_contractions(text: str) -> int:
    total = 0
    for w in EN_WORD_RE.findall(text.lower()):
        if w.replace("’", "'") in lexicons.EN_CONTRACTIONS:
            total += 1
    return total


def is_contraction(word: str) -> bool:
    return word.lower().replace("’", "'") in lexicons.EN_CONTRACTIONS


def syllables(word: str) -> int:
    """粗糙音节估计，够算 Flesch 阅读难度。"""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(groups))


# --------------------------------------------------------------------------
# 套话匹配
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PhraseHit:
    text: str
    start: int
    end: int
    weight: float
    kind: str  # "phrase" | "pattern"
    sentence_index: int = -1


class PhraseMatcher:
    """把长短语表压成一个正则，同时支持可变的骨架正则。

    长短语优先匹配（按长度倒序排进 alternation），命中后其区间会被标记，
    后续正则命中若与之重叠则丢弃，避免同一句话被重复计分。
    """

    def __init__(
        self,
        strong: list[str],
        weak: list[str],
        patterns: list[tuple[str, float]],
        weak_weight: float = 0.3,
    ) -> None:
        self.weights: dict[str, float] = {}
        for p in strong:
            self.weights[p.lower()] = 1.0
        for p in weak:
            self.weights[p.lower()] = weak_weight
        ordered = sorted(self.weights, key=len, reverse=True)
        alternation = "|".join(re.escape(p) for p in ordered)
        self._plain = (
            re.compile(r"(?<![A-Za-z])(" + alternation + r")(?![A-Za-z])", re.IGNORECASE)
            if alternation
            else None
        )
        self._patterns = [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]

    def find(self, text: str) -> list[PhraseHit]:
        """先收集所有候选，再按"长的优先"贪心去重，避免 'crucial' 抢掉
        'play a crucial role' 这类更具体的骨架。"""
        candidates: list[PhraseHit] = []
        if self._plain is not None:
            for m in self._plain.finditer(text):
                key = m.group(1).lower()
                candidates.append(
                    PhraseHit(m.group(1), m.start(), m.end(), self.weights[key], "phrase")
                )
        for rx, weight in self._patterns:
            for m in rx.finditer(text):
                candidates.append(
                    PhraseHit(m.group(0), m.start(), m.end(), weight, "pattern")
                )

        candidates.sort(key=lambda h: (-(h.end - h.start), h.start))
        accepted: list[PhraseHit] = []
        spans: list[tuple[int, int]] = []
        for hit in candidates:
            if any(not (hit.end <= a or hit.start >= b) for a, b in spans):
                continue
            spans.append((hit.start, hit.end))
            accepted.append(hit)
        accepted.sort(key=lambda h: h.start)
        return accepted

    def weighted_count(self, text: str) -> float:
        return sum(h.weight for h in self.find(text))


class SentenceIndex:
    """把句子列表映射回原文偏移，方便给每条命中定位到句子。"""

    def __init__(self, text: str, sentences: list[str]) -> None:
        self.spans: list[tuple[int, int]] = []
        cursor = 0
        for sent in sentences:
            idx = text.find(sent, cursor)
            if idx < 0:
                idx = cursor
            self.spans.append((idx, idx + len(sent)))
            cursor = idx + len(sent)

    def locate(self, pos: int) -> int:
        for i, (s, e) in enumerate(self.spans):
            if s <= pos < e:
                return i
        return -1


def make_matcher(lang: str) -> PhraseMatcher:
    if lang == "zh":
        return PhraseMatcher(
            lexicons.ZH_CLICHES_STRONG,
            lexicons.ZH_CLICHES_WEAK,
            lexicons.ZH_CLICHE_PATTERNS,
        )
    return PhraseMatcher(
        lexicons.EN_CLICHES_STRONG,
        lexicons.EN_CLICHES_WEAK,
        lexicons.EN_CLICHE_PATTERNS,
    )
