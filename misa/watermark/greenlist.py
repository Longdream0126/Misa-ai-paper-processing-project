"""统计水印（green-list / 绿名单）的检测与演示实现。

原理（Kirchenbauer et al. 2023 的二元绿名单方案，SynthID-Text 等工业实现
的精神相同，只是采样算法更复杂）：

1. 生成时，用密钥 + 上一个 token 做哈希，把词表随机劈成绿名单（γ 比例）和
   红名单（其余）。
2. 采样时给绿名单的 token 加一个偏置 δ，于是生成出来的文本里绿 token 明显
   偏多。
3. 验证时，验证方用同一把密钥重算每个位置的绿名单，统计绿 token 占比，
   得到 z 分数。没水印的文本 z ≈ 0，有水印的 z 会很大。

**关键结论**：没有密钥就无法验证水印，也无法"定向"删除它。
把文本改写到面目全非当然能破坏水印——但那同时也就破坏了你要交付的内容。
网上号称"一键去水印"的工具，绝大多数只是改标点、换同义词，对真水印无效。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .. import i18n


def stable_id(token: str) -> int:
    """把任意字符串映射成稳定的 32 位整数，代替真模型的 token id。"""
    return int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest(), "big")


def _mix(a: int, b: int, key: bytes) -> int:
    h = hashlib.blake2b(key, digest_size=8)
    h.update(a.to_bytes(8, "big"))
    h.update(b.to_bytes(8, "big"))
    return int.from_bytes(h.digest(), "big")


@dataclass
class GreenList:
    key: str
    gamma: float = 0.25

    def __post_init__(self) -> None:
        self._key = self.key.encode("utf-8")
        self._threshold = int(self.gamma * 1000)

    def is_green(self, token: str, prev_token: str) -> bool:
        h = _mix(stable_id(prev_token), stable_id(token), self._key)
        return h % 1000 < self._threshold

    def green_count(self, tokens: list[str]) -> int:
        return sum(1 for a, b in zip(tokens, tokens[1:]) if self.is_green(b, a))


@dataclass
class WatermarkResult:
    n_pairs: int
    green: int
    z: float
    p_value: float
    gamma: float
    level: str

    @property
    def verdict(self) -> str:
        return i18n.t(f"wm.verdict.{self.level}")

    def to_dict(self, locale: str | None = None) -> dict:
        return {
            "n_pairs": self.n_pairs,
            "green": self.green,
            "green_ratio": round(self.green / self.n_pairs, 4) if self.n_pairs else 0.0,
            "gamma": self.gamma,
            "z": round(self.z, 3),
            "p_value": self.p_value,
            "verdict": i18n.t(f"wm.verdict.{self.level}", locale),
            "level": self.level,
        }


def detect(tokens: list[str], key: str, gamma: float = 0.25) -> WatermarkResult:
    """Check a token sequence for a green-list watermark using *key*."""
    gl = GreenList(key, gamma)
    n = max(0, len(tokens) - 1)
    if n == 0:
        return WatermarkResult(0, 0, 0.0, 1.0, gamma, "too_short")
    green = gl.green_count(tokens)
    p = gamma
    expected = n * p
    sd = math.sqrt(n * p * (1 - p))
    z = (green - expected) / sd if sd else 0.0
    p_value = 0.5 * math.erfc(z / math.sqrt(2))
    if z >= 4.0:
        level = "strong"
    elif z >= 2.5:
        level = "medium"
    else:
        level = "none"
    return WatermarkResult(n, green, z, max(0.0, min(1.0, p_value)), gamma, level)


def detect_text(text: str, key: str, gamma: float = 0.25) -> WatermarkResult:
    from ..analysis import tokenize
    return detect(tokenize.en_words(text), key, gamma)
