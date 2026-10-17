"""用自己的语料重新标定权重。

内置锚点是在一小撮示例文本上手工调的，只能算"合理默认值"。如果你手上有一批
确实知道来源的文本（自己以前写的 / 明确由模型生成的），用它们重新拟合会准得多：

    mkdir 我的语料\\human 我的语料\\ai
    # human/ 放人写的，ai/ 放模型生成的
    misa calibrate 我的语料 --write calib.json
    misa analyze 草稿.txt --calibration calib.json

拟合方式很朴素：每个特征取两组的均值当锚点，用标准化的均值差当权重。样本少于
每组 5 篇时会给出警告——那种规模拟合出来的东西不比默认值可靠。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Calibration:
    features: dict[str, dict] = field(default_factory=dict)
    n_human: int = 0
    n_ai: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "n_human": self.n_human,
            "n_ai": self.n_ai,
            "notes": self.notes,
            "features": self.features,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Calibration":
        return cls(
            features=d.get("features", {}),
            n_human=d.get("n_human", 0),
            n_ai=d.get("n_ai", 0),
            notes=d.get("notes", []),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Calibration":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def apply(self, features: list) -> None:
        """把拟合出来的锚点与权重套到本次分析的特征上（原地修改）。"""
        for f in features:
            spec = self.features.get(f.key)
            if not spec:
                continue
            f.human_anchor = float(spec["human"])
            f.ai_anchor = float(spec["ai"])
            f.weight = float(spec["weight"])


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def fit(texts_human: list[str], texts_ai: list[str], lang: str | None = None) -> Calibration:
    from .features import analyze

    def collect(texts: list[str]) -> dict[str, list[float]]:
        out: dict[str, list[float]] = {}
        for t in texts:
            r = analyze(t, lang)
            for f in r.features:
                out.setdefault(f.key, []).append(f.value)
        return out

    h = collect(texts_human)
    a = collect(texts_ai)
    cal = Calibration(n_human=len(texts_human), n_ai=len(texts_ai))
    raw: dict[str, float] = {}

    for key in set(h) & set(a):
        hh, aa = h[key], a[key]
        if len(hh) < 2 or len(aa) < 2:
            continue
        mh, ma = _mean(hh), _mean(aa)
        diff = ma - mh
        if abs(diff) < 1e-9:
            continue
        pooled = math.sqrt((_std(hh) ** 2 + _std(aa) ** 2) / 2) or 1e-6
        sep = abs(diff) / (pooled + 0.12 * abs(diff))
        cal.features[key] = {"human": round(mh, 4), "ai": round(ma, 4), "sep": round(sep, 3)}
        raw[key] = sep

    total = sum(raw.values())
    if total > 0:
        for key, sep in raw.items():
            cal.features[key]["weight"] = round(sep / total, 4)
    else:
        cal.notes.append("两组文本在所有特征上都没有可区分的差异，用不了这套标定。")

    cal.features = dict(sorted(cal.features.items(), key=lambda kv: -kv[1]["weight"]))
    if cal.n_human < 5 or cal.n_ai < 5:
        cal.notes.append(
            f"样本量偏小（人类 {cal.n_human} 篇 / AI {cal.n_ai} 篇）。"
            "每组最好各准备 15 篇以上，且题材、长度尽量接近，否则拟合出来的只是体裁差异。"
        )
    return cal


def load_corpus_dir(root: str | Path) -> tuple[list[str], list[str]]:
    """读取 <root>/human/*.txt 与 <root>/ai/*.txt。"""
    root = Path(root)
    human_dir = next((d for d in (root / "human", root / "human_texts", root / "人写") if d.is_dir()), None)
    ai_dir = next((d for d in (root / "ai", root / "ai_texts", root / "机器") if d.is_dir()), None)
    if human_dir is None or ai_dir is None:
        raise FileNotFoundError(
            f"在 {root} 下找不到 human/ 和 ai/ 两个子目录。请按 "
            f"{root}\\human\\*.txt 与 {root}\\ai\\*.txt 放文件。"
        )

    def read_all(d: Path) -> list[str]:
        return [p.read_text(encoding="utf-8", errors="replace")
                for p in sorted(d.glob("*.txt")) if p.stat().st_size > 0]

    return read_all(human_dir), read_all(ai_dir)
