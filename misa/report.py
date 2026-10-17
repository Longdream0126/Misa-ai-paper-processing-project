"""Terminal report rendering: turn structured results into readable text.

Standard library only, optional ANSI colour, no rich/colorama.
"""

from __future__ import annotations

import difflib
import json
import os
import sys
from typing import Any

from . import __attribution__

SIGNATURE = __attribution__

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
CYAN = "\x1b[36m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"

WIDTH = 68


def color_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


class Painter:
    def __init__(self, enabled: bool) -> None:
        self.on = enabled

    def __call__(self, text: str, code: str) -> str:
        return f"{code}{text}{RESET}" if self.on else text

    def bold(self, text: str) -> str:
        return self(text, BOLD)

    def dim(self, text: str) -> str:
        return self(text, DIM)

    def score_color(self, score: int) -> str:
        if score >= 70:
            return RED
        if score >= 40:
            return YELLOW
        return GREEN


def _hline(char: str = "─", width: int = WIDTH) -> str:
    return char * width


def _bar(value: float, width: int = 12, filled: str = "█", empty: str = "░") -> str:
    v = max(0.0, min(1.0, value))
    n = int(round(v * width))
    return filled * n + empty * (width - n)


def _dwidth(s: str) -> int:
    """Display width: CJK characters take two columns."""
    return sum(2 if ord(c) > 0x2E80 else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _dwidth(s))


def _rpad(s: str, width: int) -> str:
    return " " * max(0, width - _dwidth(s)) + s


def render_analysis(result, paint: Painter | None = None, show_sentences: int = 5) -> str:
    p = paint or Painter(color_enabled())
    d = result if isinstance(result, dict) else result.to_dict()
    lines: list[str] = []
    lines.append(p.dim(_hline()))
    head = f"{p.bold('AI-likeness')}  {d['lang'].upper()}  ·  {d['confidence']}"
    lines.append(head)
    sc = d["score"]
    band = d["band"]
    bar = _bar(sc / 100, 20)
    lines.append(f"  {p(bar, p.score_color(sc))}  {p(f'{sc:3d}', BOLD + p.score_color(sc))}/100  {p(band, p.score_color(sc))}")

    stats = d["stats"]
    unit_name = "characters" if stats.get("unit_key") == "char" else "words"
    bits = [f"{stats.get('units', 0)} {unit_name}", f"{stats.get('sentences', 0)} sentences"]
    if stats.get("paragraphs"):
        bits.append(f"{stats['paragraphs']} paragraphs")
    if stats.get("avg_sentence_len"):
        bits.append(f"avg {stats['avg_sentence_len']}/sentence")
    if stats.get("cliche_hits"):
        bits.append(f"{stats['cliche_hits']} clichés")
    lines.append(p.dim("  " + " · ".join(str(b) for b in bits)))
    lines.append(p.dim(_hline()))

    feats = sorted(d["features"], key=lambda f: -(f["weight"] * f["sub"]))
    lines.append(
        "  " + _pad("Feature", 14) + _rpad("Value", 8) + "  " + _rpad("Human", 6) + _rpad("AI", 6)
        + "   " + _pad("Tendency", 14) + _rpad("Weight", 5)
    )
    for f in feats:
        sub = f["sub"]
        arrow = "▲" if sub >= 0.66 else ("▽" if sub <= 0.33 else "·")
        col = RED if sub >= 0.66 else (GREEN if sub <= 0.33 else YELLOW)
        lines.append(
            "  " + _pad(f["label"], 14) + _rpad(f"{f['value']:.2f}", 8) + "  "
            + _rpad(f"{f['human_anchor']:g}", 6) + _rpad(f"{f['ai_anchor']:g}", 6) + "   "
            + p(_bar(sub, 12), col) + arrow + " " + _rpad(f"{f['weight']:.2f}", 5)
        )
    lines.append(p.dim(_hline()))

    if d["flags"]:
        lines.append(p.bold("  Findings"))
        for fl in d["flags"]:
            mark = {"high": "!!", "medium": " !", "low": "  "}.get(fl["level"], "  ")
            lines.append(f"  {p(mark, RED if fl['level'] == 'high' else YELLOW)} {p(fl['title'], BOLD)}")
            for chunk in _wrap(fl["detail"], 62):
                lines.append("     " + p.dim(chunk))
        lines.append(p.dim(_hline()))

    if show_sentences and d["sentences"]:
        top = sorted(d["sentences"], key=lambda s: -s["score"])[:show_sentences]
        if top and top[0]["score"] >= 45:
            lines.append(p.bold("  Most AI-like sentences"))
            for s in top:
                text = s["text"] if len(s["text"]) <= 64 else s["text"][:62] + "…"
                score_str = f"{s['score']:3d}"
                lines.append(f"  {p(score_str, RED)}  {text}")
                if s["reasons"]:
                    lines.append("       " + p.dim("；".join(s["reasons"])))
            lines.append(p.dim(_hline()))

    for chunk in _wrap(d["disclaimer"], WIDTH - 4):
        lines.append(p.dim("  " + chunk))
    lines.append(p.dim("  " + SIGNATURE))
    return "\n".join(lines)


def _tokens(text: str) -> list[str]:
    """Split text into unbreakable units: CJK per character, Latin per word."""
    out: list[str] = []
    buf = ""
    for ch in text:
        if ord(ch) > 0x2E80 or ch in "，。；：！？、（）「」『』—…":
            if buf:
                out.append(buf)
                buf = ""
            out.append(ch)
        elif ch in " \t":
            if buf:
                out.append(buf)
                buf = ""
            out.append(" ")
        else:
            buf += ch
    if buf:
        out.append(buf)
    return out


def _wrap(text: str, width: int) -> list[str]:
    """Wrap text: ASCII by spaces, mixed text keeps Latin words intact."""
    if not text:
        return [""]
    cjk = sum(1 for c in text if ord(c) > 0x2E80)
    if cjk / max(1, len(text)) < 0.2:
        import textwrap
        return textwrap.wrap(text, width=width) or [text]

    lines: list[str] = []
    cur = ""
    cur_w = 0
    for tok in _tokens(text):
        tw = _dwidth(tok)
        if cur_w + tw > width and cur:
            lines.append(cur.rstrip())
            cur = "" if tok == " " else tok
            cur_w = _dwidth(cur)
        else:
            cur += tok
            cur_w += tw
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [text]


def render_humanize(result, paint: Painter | None = None, show_text: bool = True) -> str:
    p = paint or Painter(color_enabled())
    d = result if isinstance(result, dict) else result.to_dict()
    before, after = d["before"]["score"], d["after"]["score"]
    lines = [p.dim(_hline()), f"{p.bold('Rewrite')}  strength {d['level']}  ·  {d['lang']}"]
    arrow = "↓" if after < before else ("↑" if after > before else "=")
    col = GREEN if after < before else RED
    lines.append(f"  {before} {p(arrow, col)} {p(str(after), BOLD + col)}   "
                 f"(delta {after - before:+d})  content kept {d['retention']:.0%}")
    if d["changes"]:
        lines.append(p.dim("  " + "；".join(f"{c['kind']}×{c['count']}" for c in d["changes"])))
    lines.append(p.dim(_hline()))
    for w in d["warnings"]:
        for i, chunk in enumerate(_wrap(w, WIDTH - 6)):
            lines.append(p(("  ! " if i == 0 else "    ") + chunk, YELLOW))
    if show_text:
        lines.append(p.dim(_hline()))
        lines.append(d["text"])
    lines.append(p.dim("  " + SIGNATURE))
    return "\n".join(lines)


def render_diff(before: str, after: str) -> str:
    diff = difflib.unified_diff(
        before.splitlines(), after.splitlines(), fromfile="before", tofile="after", lineterm="", n=0
    )
    return "\n".join(diff)


def render_invisible(scan: dict, paint: Painter | None = None) -> str:
    p = paint or Painter(color_enabled())
    level = scan.get("level", "none")
    col = {"high": RED, "medium": YELLOW, "low": CYAN}.get(level, GREEN)
    lines = [p.dim(_hline()), p.bold("Invisible-character scan")]
    lines.append(f"  {p(str(scan['total']), BOLD + col)} hits · {scan['chars']} characters")
    for cat in scan["categories"]:
        lines.append(f"\n  {p(cat['label'], BOLD)}  {cat['count']}  [{cat['risk']}]")
        for ch in cat["chars"][:6]:
            readable = ch["char"] if ch["char"].isprintable() else "␀"
            lines.append(f"    {readable!r:>6} {ch['codepoint']} {p(ch['name'], DIM)} ×{ch['count']}")
        for chunk in _wrap(cat["note"], WIDTH - 6):
            lines.append("    " + p.dim(chunk))
    if scan.get("long_runs"):
        lines.append("\n  " + p("Long runs of invisible characters", RED))
        for run in scan["long_runs"][:5]:
            lines.append(f"    offset {run['start']}, length {run['length']}, {run['codepoints'][:4]}…")
    if scan.get("mixed_script_words"):
        lines.append("\n  " + p("Mixed-script words", YELLOW))
        for w in scan["mixed_script_words"][:5]:
            lines.append(f"    {w['word']}  ({w['foreign']})")
    lines.append("")
    for chunk in _wrap(scan["verdict"], WIDTH - 4):
        lines.append("  " + chunk)
    lines.append(p.dim("  " + SIGNATURE))
    return "\n".join(lines)


def render_meta(report, paint: Painter | None = None) -> str:
    p = paint or Painter(color_enabled())
    d = report.to_dict() if hasattr(report, "to_dict") else report
    lines = [p.dim(_hline()), f"{p.bold('Metadata / content credentials')}  {d['name']}  ({d['kind']}, {_size(d['size'])})"]
    if d["findings"]:
        for f in d["findings"]:
            risk = f["risk"]
            mark = p("!!", RED) if risk == "high" else (p(" !", YELLOW) if risk == "warn" else p(" ·", DIM))
            val = f["value"]
            if len(val) > 56:
                val = val[:54] + "…"
            lines.append(f"  {mark} {_pad(f['key'], 16)}{val}   {p(f['source'], DIM)}")
    else:
        lines.append("  " + p("No readable metadata fields.", GREEN))
    if d["has_c2pa"]:
        lines.append("  " + p("C2PA / JUMBF content credential found", RED + BOLD))
    if d["ai_hints"]:
        lines.append("\n  " + p("AI-generation traces", YELLOW))
        for hint in d["ai_hints"]:
            lines.append("    · " + hint)
    if d.get("structure"):
        items = ", ".join(f"{k}={v}" for k, v in d["structure"].items())
        lines.append("\n  " + p("Structure: " + items[:200], DIM))
    for note in d.get("notes", []):
        for chunk in _wrap(note, WIDTH - 6):
            lines.append("  " + p.dim(chunk))
    lines.append(p.dim("  " + SIGNATURE))
    return "\n".join(lines)


def _size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def render_watermark(demo: dict, paint: Painter | None = None) -> str:
    p = paint or Painter(color_enabled())
    lines = [p.dim(_hline()), p.bold("Statistical watermark demo (green-list)")]
    lines.append(f"  key {p(demo['key'], CYAN)} · γ={demo['gamma']} · δ={demo['delta']}")
    lines.append(p.dim(_hline()))

    def block(title: str, text: str, res: dict, tone: str) -> None:
        lines.append(f"\n  {p(title, BOLD)}")
        for chunk in _wrap(text, WIDTH - 4):
            lines.append("    " + p.dim(chunk))
        lines.append(
            f"    green {res['green']}/{res['n_pairs']} = {res['green_ratio']:.2%}"
            f"    z = {p(f'{res[chr(122)]:.2f}', tone)}    p = {res['p_value']:.2e}"
        )
        for chunk in _wrap(res["verdict"], WIDTH - 6):
            lines.append("    " + p(chunk, tone))

    block("1. No watermark, checked with the right key", demo["plain_text"], demo["plain"], GREEN)
    block("2. Watermarked, checked with the right key", demo["marked_text"], demo["marked"], RED)

    wrong = demo.get("wrong_keys") or []
    if wrong:
        lines.append(f"\n  {p('3. Same text, checked with 6 wrong keys', BOLD)}")
        for chunk in _wrap(demo["marked_text"], WIDTH - 4):
            lines.append("    " + p.dim(chunk))
        spread = "   ".join(f"{w['label']}: z={w['z']:+.2f}" for w in wrong)
        for chunk in _wrap(spread, WIDTH - 4):
            lines.append("    " + p(chunk, YELLOW))
        lo = min(w["z"] for w in wrong)
        hi = max(w["z"] for w in wrong)
        lines.append(f"    z ranges {lo:+.2f} to {hi:+.2f}; the right key gives z = {demo['marked']['z']:.2f}")
        for chunk in _wrap("The green-list test is one-sided: only a surplus of green tokens counts. "
                           "Wrong keys scatter around zero and occasionally reach ±2–3, so a single "
                           "run needs a p-value and a sample size, not just a z number.",
                           WIDTH - 6):
            lines.append("    " + p.dim(chunk))
    else:
        block("3. Same text, checked with a wrong key", demo["marked_text"],
              demo["marked_wrong_key"], YELLOW)
    lines.append(p.dim(_hline()))
    for chunk in _wrap(demo["note"], WIDTH - 4):
        lines.append("  " + chunk)
    lines.append(p.dim("  " + SIGNATURE))
    return "\n".join(lines)


def to_json(obj: Any) -> str:
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    return json.dumps(obj, ensure_ascii=False, indent=2)
