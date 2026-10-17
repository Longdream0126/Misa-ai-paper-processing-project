"""一个极小的二元语言模型，用来在本地"真的"生成带水印 / 不带水印的文本。

它的目的不是写出通顺的文章，而是让你亲眼看到：
同一个采样器，只因为采样时给绿名单加了偏置，检测 z 分数就从 0 附近跳到
几十；而换一把密钥去检测，z 又立刻回落到 0。

这解释了为什么"删除 AI 水印"在没有密钥时几乎不可能定向完成：
水印不是一段可以找到并删掉的字符串，而是整段文本的统计分布特征。
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .. import i18n
from ..analysis import tokenize
from .greenlist import GreenList, detect_text

FALLBACK_CORPUS = """
the quick brown fox jumps over the lazy dog while the dog sleeps in the sun
a small river runs behind the house and the water is cold in the morning
she walked to the market and bought bread milk and a bag of apples
the train was late again so we sat on the platform and talked about nothing
my brother keeps a notebook of every bird he sees from the kitchen window
the old bridge is closed for repairs and the bus now takes a longer route
we planted tomatoes in april and by august the vines had taken over the fence
he said the meeting would be short and then it lasted three hours
the library closes at six on fridays but stays open late on tuesdays
rain moved in from the west and the streets were empty by nine
the coffee here is strong and the seats by the window are always taken
she learned to swim at forty and now swims every morning before work
the cat sits on the warm stone and watches the birds in the hedge
our neighbor plays the piano badly but he plays it every single evening
the road turns north after the church and climbs toward the hills
i keep forgetting to water the plants on the balcony
the market sells fish on wednesdays and the queue starts before dawn
he fixed the bicycle with a wire and a piece of tape and it held for a week
the children built a fort out of chairs and blankets in the front room
winter came early that year and the lake froze before december
""".strip()


@dataclass
class ToyLM:
    text: str
    top_k: int = 40
    # 与一元分布插值：纯二元模型的候选太少，绿名单往往"无词可换"，
    # 水印强度会随密钥运气剧烈波动。插值后每个位置都有足够多的候选，
    # 绿名单偏置才稳定生效。
    uni_weight: float = 0.35

    def __post_init__(self) -> None:
        tokens = tokenize.en_words(self.text)
        if not tokens:
            tokens = ["the"]
        self.tokens = tokens
        self.counts: dict[str, Counter[str]] = {}
        for a, b in zip(tokens, tokens[1:]):
            self.counts.setdefault(a, Counter())[b] += 1
        self._top: dict[str, list[tuple[str, int]]] = {
            k: v.most_common(self.top_k) for k, v in self.counts.items()
        }
        uni = Counter(tokens).most_common(max(80, self.top_k * 3))
        total = sum(c for _, c in uni) or 1
        self._uni: dict[str, float] = {w: c / total for w, c in uni}
        self.start = tokens[0]

    def candidates(self, prev: str) -> list[tuple[str, float]]:
        """返回候选词及其混合概率（二元 + 一元插值）。"""
        dist: dict[str, float] = {}
        bi = self._top.get(prev)
        if bi:
            tot = sum(c for _, c in bi) or 1
            keep = 1.0 - self.uni_weight
            for w, c in bi:
                dist[w] = dist.get(w, 0.0) + keep * c / tot
        for w, p in self._uni.items():
            dist[w] = dist.get(w, 0.0) + self.uni_weight * p
        return sorted(dist.items(), key=lambda kv: -kv[1])[: self.top_k]

    def sample(
        self,
        length: int = 120,
        key: str | None = None,
        gamma: float = 0.25,
        delta: float = 6.0,
        seed: int = 0,
        temperature: float = 1.0,
    ) -> str:
        rng = random.Random(seed)
        gl = GreenList(key, gamma) if key else None
        cur = self.start
        out = [cur]
        for _ in range(length):
            cands = self.candidates(cur)
            words = [w for w, _ in cands]
            logits = [math.log(c + 1e-9) / max(0.1, temperature) for _, c in cands]
            if gl is not None:
                for i, w in enumerate(words):
                    if gl.is_green(w, cur):
                        logits[i] += delta
            m = max(logits)
            weights = [math.exp(v - m) for v in logits]
            total = sum(weights)
            r = rng.random() * total
            acc = 0.0
            pick = words[-1]
            for w, wt in zip(words, weights):
                acc += wt
                if acc >= r:
                    pick = w
                    break
            out.append(pick)
            cur = pick
        return " ".join(out)


def load_corpus() -> str:
    """优先用 data/samples 下的语料，找不到就用内置的几百词。"""
    root = Path(__file__).resolve().parents[2]
    samples = root / "data" / "samples"
    if samples.is_dir():
        chunks = []
        for p in sorted(samples.glob("*.txt")):
            try:
                chunks.append(p.read_text(encoding="utf-8"))
            except OSError:
                continue
        text = "\n".join(chunks)
        if len(tokenize.en_words(text)) >= 200:
            return text
    return FALLBACK_CORPUS


def demo(key: str = "misa-demo", length: int = 140, seed: int = 7,
         gamma: float = 0.25, delta: float = 6.0, locale: str | None = None) -> dict:
    """Sample a plain and a watermarked passage, then check both."""
    lm = ToyLM(load_corpus())
    plain = lm.sample(length=length, seed=seed)
    marked = lm.sample(length=length, key=key, gamma=gamma, delta=delta, seed=seed)

    # Six wrong keys: a single one can look "suspicious" by chance (|z| ≈ 2),
    # a small spread of null tests shows what noise looks like.
    wrong_keys = []
    for i in range(6):
        r = detect_text(marked, f"{key}#wrong{i}", gamma)
        wrong_keys.append({"label": f"wrong-{i + 1}", "z": round(r.z, 3),
                           "p_value": r.p_value, "level": r.level})

    return {
        "key": key,
        "gamma": gamma,
        "delta": delta,
        "plain_text": plain,
        "marked_text": marked,
        "plain": detect_text(plain, key, gamma).to_dict(locale),
        "marked": detect_text(marked, key, gamma).to_dict(locale),
        "marked_wrong_key": detect_text(marked, f"{key}#wrong0", gamma).to_dict(locale),
        "wrong_keys": wrong_keys,
        "note": i18n.t("wm.note", locale),
    }
