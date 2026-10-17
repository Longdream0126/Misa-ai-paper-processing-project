"""Unicode 隐形字符扫描：真正能"无密钥"检测到的那一类隐形标记。

统计水印（SynthID 一类）需要密钥才能验证；但**字符级**的隐形标记不需要：
零宽字符、标签字符、变体选择符、双向控制符、跨文字系统同形字，这些都可
以直接从码点上看出来。它们常见于：

* 网页/PDF 复制粘贴带来的残留
* 用不可见字符整段藏字的"隐形提示词注入"
* 排版软件的软连字符
* 极少数情况下被当作粗糙的"所有权标记"
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from .. import i18n

ZERO_WIDTH = {
    0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x180E, 0x00AD,
    0x200E, 0x200F, 0x2061, 0x2062, 0x2063, 0x2064,
    0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F,
}

TAG_RANGE = (0xE0000, 0xE007F)
VARIATION_RANGES = [(0xFE00, 0xFE0F), (0xE0100, 0xE01EF)]
BIDI_RANGE = (0x202A, 0x202E)
BIDI_ISOLATE_RANGE = (0x2066, 0x2069)
ODD_SPACES = {
    0x00A0, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,
    0x2007, 0x2008, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000, 0x1680,
}

CIRCLED = {0x2460, 0x2461, 0x2462}  # ①②③ 不是隐形，但常被当列表符号

CATEGORIES = [
    ("zero_width", 0x200B),
    ("tag", TAG_RANGE[0]),
    ("variation", 0xFE00),
    ("bidi", BIDI_RANGE[0]),
    ("space", 0x00A0),
    ("homoglyph", 0x0430),
]

LATIN = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
CYRILLIC = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
GREEK = set("αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ")


@dataclass
class CharHit:
    char: str
    codepoint: str
    name: str
    count: int
    positions: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "char": self.char,
            "codepoint": self.codepoint,
            "name": self.name,
            "count": self.count,
            "positions": self.positions[:12],
        }


def classify(ch: str) -> str | None:
    cp = ord(ch)
    if cp in ZERO_WIDTH:
        return "zero_width"
    if TAG_RANGE[0] <= cp <= TAG_RANGE[1]:
        return "tag"
    if any(lo <= cp <= hi for lo, hi in VARIATION_RANGES):
        return "variation"
    if BIDI_RANGE[0] <= cp <= BIDI_RANGE[1] or BIDI_ISOLATE_RANGE[0] <= cp <= BIDI_ISOLATE_RANGE[1]:
        return "bidi"
    if cp in ODD_SPACES:
        return "space"
    return None


def _name(ch: str) -> str:
    return unicodedata.name(ch, "UNNAMED")


def scan_invisible(text: str, locale: str | None = None) -> dict:
    """Scan for invisible / confusable characters and return a JSON-ready report."""
    buckets: dict[str, dict[str, CharHit]] = {}
    hidden_positions: list[int] = []

    for i, ch in enumerate(text):
        cat = classify(ch)
        if cat is None:
            continue
        bucket = buckets.setdefault(cat, {})
        hit = bucket.get(ch)
        if hit is None:
            hit = CharHit(ch, f"U+{ord(ch):04X}", _name(ch), 0, [])
            bucket[ch] = hit
        hit.count += 1
        if len(hit.positions) < 12:
            hit.positions.append(i)
        hidden_positions.append(i)

    # A run of 8+ invisible characters is almost certainly a payload.
    runs = _find_runs(text, lambda c: classify(c) in {"zero_width", "tag", "variation", "bidi"})
    long_runs = [r for r in runs if r["length"] >= 8]

    mixed = _mixed_script_words(text)

    categories = []
    total = 0
    for key, _ in CATEGORIES:
        if key == "homoglyph":
            count = len(mixed)
            hits = []
        else:
            bucket = buckets.get(key, {})
            count = sum(h.count for h in bucket.values())
            hits = [h.to_dict() for h in sorted(bucket.values(), key=lambda x: -x.count)]
        if count == 0:
            continue
        total += count
        categories.append({
            "key": key,
            "label": i18n.t(f"inv.{key}", locale),
            "count": count,
            "chars": hits,
            "note": i18n.t(f"inv.{key}.note", locale),
            "risk": "high" if key in {"tag", "bidi"} else ("medium" if key == "zero_width" else "low"),
        })

    trailing = _trailing_space_lines(text)

    level = _verdict(total, long_runs, mixed, trailing)

    return {
        "total": total,
        "categories": categories,
        "long_runs": long_runs[:10],
        "mixed_script_words": mixed[:20],
        "trailing_space_lines": trailing,
        "verdict": i18n.t(f"inv.verdict.{level}", locale),
        "level": level,
        "chars": len(text),
    }


def _find_runs(text: str, pred) -> list[dict]:
    runs: list[dict] = []
    start = -1
    for i, ch in enumerate(text):
        if pred(ch):
            if start < 0:
                start = i
        else:
            if start >= 0:
                runs.append({"start": start, "length": i - start,
                             "codepoints": [f"U+{ord(c):04X}" for c in text[start:i][:8]]})
                start = -1
    if start >= 0:
        runs.append({"start": start, "length": len(text) - start,
                     "codepoints": [f"U+{ord(c):04X}" for c in text[start:start + 8]]})
    return runs


def _mixed_script_words(text: str) -> list[dict]:
    out: list[dict] = []
    word: list[str] = []
    for ch in text + " ":
        if ch.isalpha() and not ("\u4e00" <= ch <= "\u9fff"):
            word.append(ch)
            continue
        if len(word) >= 2:
            has_latin = any(c in LATIN for c in word)
            has_cyr = any(c in CYRILLIC for c in word)
            has_greek = any(c in GREEK for c in word)
            if has_latin and (has_cyr or has_greek):
                out.append({
                    "word": "".join(word),
                    "codepoints": [f"U+{ord(c):04X}" for c in word],
                    "foreign": "西里尔" if has_cyr else "希腊",
                    "foreign_key": "cyrillic" if has_cyr else "greek",
                })
        word = []
    return out


def _trailing_space_lines(text: str) -> int:
    return sum(1 for line in text.split("\n") if re_trailing(line))


def re_trailing(line: str) -> bool:
    return line != line.rstrip(" \t") and bool(line.strip())


def _verdict(total: int, long_runs: list[dict], mixed: list[dict], trailing: int) -> str:
    if long_runs or total >= 20 or mixed:
        return "high"
    if total > 0:
        return "medium"
    if trailing > 0:
        return "low"
    return "none"


def clean_invisible(text: str, mode: str = "default", replace_space: bool = True) -> tuple[str, dict]:
    """删除隐形字符。mode: default(零宽+标签+双向+软连字符) / all(含变体选择符) / zero-width。"""
    removed: dict[str, int] = {}
    out: list[str] = []

    for ch in text:
        cat = classify(ch)
        if cat is None:
            out.append(ch)
            continue
        if cat == "space":
            out.append(" " if replace_space else ch)
            removed[cat] = removed.get(cat, 0) + 1
            continue
        if mode == "zero-width":
            drop = cat == "zero_width"
        elif mode == "all":
            drop = True
        else:
            drop = cat in {"zero_width", "tag", "bidi"}
        if drop:
            removed[cat] = removed.get(cat, 0) + 1
        else:
            out.append(ch)

    return "".join(out), {"removed": removed, "total": sum(removed.values()), "mode": mode}
