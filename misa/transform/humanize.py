"""降 AI 率改写引擎（确定性规则，可 diff、可回滚）。

能做什么
--------
* 拆掉 AI 最爱的套话骨架（"值得注意的是""delve into"）
* 把膨胀的名词化写法还原成动词（"make a decision" → "decide"）
* 补回缩略形式（it is → it's），让句子有"毛边"
* 打散均匀的长句，制造长短句错落（burstiness）

不能做什么
----------
* 不能移除厂商嵌入的统计水印（那需要密钥，见 watermark/greenlist.py）
* 不能保证降低任何第三方检测器的输出（检测器本身并不可靠）
* 不会替你补充事实、数据、个人经历——**这些才是让文字真正像人的东西**

所有替换规则是确定性的：同样的输入永远得到同样的输出，方便 diff 与复核。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import i18n
from ..analysis import tokenize
from ..analysis.features import AnalysisResult, analyze
from . import cliches

LEVELS = ("light", "standard", "strong")


@dataclass
class Change:
    kind: str  # i18n key suffix under "change.*"
    count: int
    detail: str = ""

    def to_dict(self, locale: str | None = None) -> dict:
        return {
            "kind": i18n.t(f"change.{self.kind}", locale),
            "kind_key": self.kind,
            "detail": self.detail,
            "count": self.count,
        }


@dataclass
class HumanizeResult:
    text: str
    before: AnalysisResult
    after: AnalysisResult
    changes: list[Change]
    level: str
    lang: str
    warnings: list[dict] = field(default_factory=list)
    retention: float = 1.0

    @property
    def delta(self) -> int:
        return self.after.score - self.before.score

    def _render_warning(self, w: dict, locale: str | None) -> str:
        kind = w.get("kind")
        if kind == "retention":
            return i18n.t("warn.retention", locale, pct=f"{w['value']:.0%}")
        return i18n.t(f"warn.{kind}", locale)

    def to_dict(self, locale: str | None = None) -> dict:
        return {
            "text": self.text,
            "level": self.level,
            "lang": self.lang,
            "before": self.before.to_dict(locale),
            "after": self.after.to_dict(locale),
            "changes": [c.to_dict(locale) for c in self.changes],
            "warnings": [self._render_warning(w, locale) for w in self.warnings],
            "warning_kinds": [w.get("kind") for w in self.warnings],
            "retention": round(self.retention, 3),
            "delta": self.delta,
        }


# --------------------------------------------------------------------------
# 文本行遍历（跳过 ``` 围起来的代码块）
# --------------------------------------------------------------------------


def _iter_lines(text: str):
    in_fence = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            yield line, True
            continue
        yield line, in_fence


def _map_lines(text: str, fn) -> str:
    out: list[str] = []
    for line, is_code in _iter_lines(text):
        if is_code or not line.strip():
            out.append(line)
        else:
            out.append(fn(line))
    return "\n".join(out)


def _rewrite_sentences(text: str, lang: str, fn) -> tuple[str, int]:
    """逐句替换，fn(sentence) -> list[str]；返回(新文本, 被改动的句子数)。"""
    changed = 0
    joiner = "" if lang == "zh" else " "

    def line_fn(line: str) -> str:
        nonlocal changed
        sents = tokenize.split_sentences(line, lang)
        new: list[str] = []
        for s in sents:
            parts = fn(s)
            if parts != [s]:
                changed += 1
            new.extend(parts)
        return joiner.join(new) if new else line

    return _map_lines(text, line_fn), changed


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _cleanup(text: str, lang: str) -> str:
    def fn(line: str) -> str:
        line = re.sub(r"[ \t]{2,}", " ", line)
        line = re.sub(r"[ \t]+([,.;:!?，。；：！？、])", r"\1", line)
        if lang != "zh":
            line = re.sub(r"([,;:])(?=[A-Za-z])", r"\1 ", line)
        line = re.sub(r"\(\s+", "(", line)
        line = re.sub(r"\s+\)", ")", line)
        line = re.sub(r"[ \t]+$", "", line)
        line = re.sub(r"^\s*[,;]\s*", "", line)
        return line

    return _map_lines(text, fn).strip()


# --------------------------------------------------------------------------
# 短语表
# --------------------------------------------------------------------------


class _PhraseTable:
    def __init__(self, entries: list[tuple[str, str]], cjk: bool = False) -> None:
        self.cjk = cjk
        self.mapping = {k.lower(): v for k, v in entries}
        keys = sorted(self.mapping, key=len, reverse=True)
        alt = "|".join(re.escape(k) for k in keys)
        if cjk:
            self.rx = re.compile("(" + alt + ")", re.IGNORECASE)
        else:
            self.rx = re.compile(r"(?<![A-Za-z])(" + alt + r")(?![A-Za-z])", re.IGNORECASE)

    def apply(self, text: str) -> tuple[str, int]:
        out: list[str] = []
        pos = 0
        count = 0
        for m in self.rx.finditer(text):
            out.append(text[pos:m.start()])
            matched = m.group(0)
            new = self.mapping.get(matched.lower(), matched)
            if new == "":
                j = m.end()
                while j < len(text) and text[j] in " \t":
                    j += 1
                at_start = not text[:m.start()].strip() or bool(
                    re.search(r"[.!?…。！？]\s*$", text[:m.start()])
                )
                if at_start and j < len(text):
                    out.append(text[j].upper())
                    pos = j + 1
                else:
                    pos = j
            else:
                if not self.cjk and matched[:1].isupper():
                    new = _cap(new)
                out.append(new)
                pos = m.end()
            count += 1
        out.append(text[pos:])
        return "".join(out), count


_EN_TABLE = _PhraseTable(cliches.EN_REPLACEMENTS)
_ZH_TABLE = _PhraseTable(cliches.ZH_REPLACEMENTS, cjk=True)


def _apply_table(text: str, table: _PhraseTable) -> tuple[str, int]:
    total = 0

    def fn(line: str) -> str:
        nonlocal total
        new, n = table.apply(line)
        total += n
        return new

    return _map_lines(text, fn), total


def _apply_regex_rules(text: str, rules: list[tuple[str, str]]) -> tuple[str, int]:
    total = 0

    def fn(line: str) -> str:
        nonlocal total
        for pattern, repl in rules:
            line, n = re.subn(pattern, repl, line, flags=re.IGNORECASE)
            total += n
        return line

    return _map_lines(text, fn), total


def _apply_contractions(text: str) -> tuple[str, int]:
    total = 0
    ordered = sorted(cliches.EN_CONTRACTIONS.items(), key=lambda kv: -len(kv[0]))
    patterns = [(re.compile(r"\b" + re.escape(a) + r"\b", re.IGNORECASE), b) for a, b in ordered]

    def fn(line: str) -> str:
        nonlocal total
        for rx, short in patterns:
            def _sub(m: re.Match, short: str = short) -> str:
                nonlocal total
                total += 1
                src = m.group(0)
                return _cap(short) if src[:1].isupper() else short

            line = rx.sub(_sub, line)
        return line

    return _map_lines(text, fn), total


def _thin_openers(text: str, lang: str) -> tuple[str, int]:
    table = cliches.ZH_OPENER_THIN if lang == "zh" else cliches.EN_OPENER_THIN

    def fn(sent: str) -> list[str]:
        low = sent.lower()
        for opener, repl in table.items():
            if low.startswith(opener):
                rest = sent[len(opener):].lstrip()
                if not rest or repl == opener:
                    return [sent]
                if repl == "":
                    return [_cap(rest)]
                if lang == "zh":
                    return [repl + rest]
                if sent[:1].isupper():
                    repl = _cap(repl)
                return [repl + " " + rest]
        return [sent]

    return _rewrite_sentences(text, lang, fn)


# --------------------------------------------------------------------------
# 拆长句
# --------------------------------------------------------------------------

_EN_SPLITS = [
    (", and then ", "Then "),
    (", and ", "And "),
    (", but ", "But "),
    (", so ", "So "),
    (", which ", "This "),
    ("; ", ""),
    (" — ", ""),
    (" - ", ""),
]


def _split_en_sentence(sent: str, max_len: int) -> list[str]:
    body = sent.rstrip()
    terminal = ""
    if body and body[-1] in ".!?…":
        terminal = body[-1]
        body = body[:-1]
    if len(body.split()) <= max_len:
        return [sent]

    candidates: list[tuple[int, str, str]] = []
    for marker, prefix in _EN_SPLITS:
        start = body.find(marker)
        while start > 0:
            left = body[:start]
            right = body[start + len(marker):]
            lw, rw = len(left.split()), len(right.split())
            if lw >= 8 and rw >= 6:
                candidates.append((abs(lw - rw), left, prefix + right))
            start = body.find(marker, start + 1)

    if not candidates:
        return [sent]
    _, left, right = min(candidates, key=lambda c: c[0])
    left = left.rstrip(" ,;:")
    if left[-1:] not in ".!?":
        left += "."
    right = _cap(right)
    return [left, right + terminal]


_ZH_PAIRS = [
    ("只有", "才"), ("不仅", "而且"), ("不仅", "还"), ("虽然", "但"),
    ("因为", "所以"), ("如果", "就"), ("即使", "也"), ("无论", "都"),
    ("不管", "都"), ("越", "越"), ("既然", "就"),
]


def _zh_split_safe(body: str, left: str, right: str) -> bool:
    """拆句不能破坏「只有…才」「不仅…而且」这类关联结构。

    只要整句里出现成对的关联词，就干脆不拆——拆错一半会让句子变成残句。
    """
    for a, b in _ZH_PAIRS:
        if a in body and b in body:
            return False
    if left.rstrip().endswith(("的", "地", "得", "和", "与", "及", "或", "是", "把", "被")):
        return False
    return True


def _split_zh_sentence(sent: str, max_len: int) -> list[str]:
    body = sent.rstrip()
    terminal = ""
    if body and body[-1] in "。！？…":
        terminal = body[-1]
        body = body[:-1]
    if len(body) <= max_len:
        return [sent]
    best: tuple[int, str, str] | None = None
    for marker in ["，而且", "，并且", "，但是", "，不过", "，所以", "，因此", "，"]:
        start = body.find(marker)
        while start > 0:
            left = body[:start]
            right = body[start + len(marker):]
            if len(left) >= 12 and len(right) >= 10 and _zh_split_safe(body, left, right):
                diff = abs(len(left) - len(right))
                if best is None or diff < best[0]:
                    best = (diff, left, right)
            start = body.find(marker, start + 1)
    if best is None:
        return [sent]
    _, left, right = best
    if left[-1] not in "。！？…":
        left += "。"
    return [left, right + terminal]


def _split_long(text: str, lang: str, max_len: int) -> tuple[str, int]:
    fn = (lambda s: _split_zh_sentence(s, max_len)) if lang == "zh" else (
        lambda s: _split_en_sentence(s, max_len)
    )
    return _rewrite_sentences(text, lang, fn)


def _rhythm_pass(text: str, threshold: int = 3) -> tuple[str, int]:
    """连续 3 句以上长度几乎一样时，把其中最长的在逗号处断开。"""
    changed = 0
    lang = "en"

    def line_fn(line: str) -> str:
        nonlocal changed
        sents = tokenize.split_sentences(line, lang)
        if len(sents) < threshold:
            return line
        lens = [len(tokenize.en_words(s)) for s in sents]
        out: list[str] = []
        i = 0
        modified = False
        while i < len(sents):
            j = i + 1
            while j < len(sents) and abs(lens[j] - lens[i]) <= 3:
                j += 1
            run = j - i
            if run >= threshold:
                longest = max(range(i, j), key=lambda k: lens[k])
                body = sents[longest].rstrip()
                terminal = body[-1] if body and body[-1] in ".!?…" else ""
                core = body[:-1] if terminal else body
                cut = core.find(", ")
                if cut > 0 and len(core[:cut].split()) >= 5 and len(core[cut + 2:].split()) >= 4:
                    out.extend(sents[i:longest])
                    out.append(core[:cut].rstrip() + ".")
                    out.append(_cap(core[cut + 2:]) + terminal)
                    out.extend(sents[longest + 1:j])
                    changed += 1
                    modified = True
                    i = j
                    continue
            out.extend(sents[i:j])
            i = j
        return " ".join(out) if modified else line

    return _map_lines(text, line_fn), changed


# --------------------------------------------------------------------------
# 保真度
# --------------------------------------------------------------------------


def _cliche_words() -> set[str]:
    """替换表里出现过的词——它们本来就该被换掉，不算"内容丢失"。"""
    words: set[str] = set()
    for phrase, _ in cliches.EN_REPLACEMENTS:
        for w in tokenize.en_words(phrase):
            if len(w) > 3:
                words.add(w)
    for pattern, _ in cliches.EN_REGEX_REPLACEMENTS:
        for w in tokenize.en_words(pattern.replace("\\b", " ")):
            if len(w) > 3:
                words.add(w)
    return words


_CLICHE_WORDS = _cliche_words()


def _retention(a: str, b: str, lang: str) -> float:
    if lang == "zh":
        ca, cb = set(tokenize.zh_chars(a)), set(tokenize.zh_chars(b))
        return len(ca & cb) / len(ca) if ca else 1.0
    wa = [w for w in tokenize.en_words(a) if len(w) > 3 and w not in _CLICHE_WORDS]
    wb = set(tokenize.en_words(b))
    if not wa:
        return 1.0
    return sum(1 for w in wa if w in wb) / len(wa)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


def humanize(
    text: str,
    level: str = "standard",
    lang: str | None = None,
    use_contractions: bool = True,
    normalize_typography: bool = False,
) -> HumanizeResult:
    """Rewrite a passage into a more human-sounding version and report the delta."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, got {level!r}")
    lang = lang or tokenize.detect_language(text)
    source = text.strip()
    before = analyze(source, lang)
    changes: list[Change] = []
    warnings: list[dict] = []
    out = source

    if lang == "zh":
        if normalize_typography:
            n = 0
            for a, b in cliches.ZH_PUNCT_NORMALIZE:
                n += out.count(a)
                out = out.replace(a, b)
            if n:
                changes.append(Change("punct", n))
        out, n = _apply_table(out, _ZH_TABLE)
        if n:
            changes.append(Change("cliche", n))
        out, n = _apply_regex_rules(out, cliches.ZH_REGEX_REPLACEMENTS)
        if n:
            changes.append(Change("skeleton", n))
        out, n = _thin_openers(out, "zh")
        if n:
            changes.append(Change("opener", n))
        out, n = _split_long(out, "zh", 55 if level == "standard" else 42)
        if n:
            changes.append(Change("split", n))
    else:
        out, n = _apply_table(out, _EN_TABLE)
        if n:
            changes.append(Change("cliche", n))
        out, n = _apply_regex_rules(out, cliches.EN_REGEX_REPLACEMENTS)
        if n:
            changes.append(Change("skeleton", n))
        if level != "light" and use_contractions:
            out, n = _apply_contractions(out)
            if n:
                changes.append(Change("contraction", n))
        if level != "light":
            out, n = _thin_openers(out, "en")
            if n:
                changes.append(Change("opener", n))
            out, n = _split_long(out, "en", 30 if level == "standard" else 24)
            if n:
                changes.append(Change("split", n))
        if level == "strong":
            out, n = _rhythm_pass(out)
            if n:
                changes.append(Change("rhythm", n))

    out = _cleanup(out, lang)
    after = analyze(out, lang)
    retention = _retention(source, out, lang)

    if after.score >= before.score:
        warnings.append({"kind": "no_drop"})
    if retention < 0.78:
        warnings.append({"kind": "retention", "value": retention})
    if before.stats.get("units", 0) < 60:
        warnings.append({"kind": "short"})
    warnings.append({"kind": "responsibility"})

    return HumanizeResult(
        text=out,
        before=before,
        after=after,
        changes=changes,
        level=level,
        lang=lang,
        warnings=warnings,
        retention=retention,
    )
