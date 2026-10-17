"""Misa's AI Paper Processing Project — 本地 AI 写作信号分析 / 风格改写 / 隐形标记扫描。

本项目由 Misa 制作 · v0.1

设计原则
--------
1. 零第三方依赖：只用 Python 标准库，``pip install`` 之外不需要任何模型权重。
2. 本地运行：所有文本只在你的机器上处理，不上传任何服务器。
3. 说明边界：不承诺"绕过检测器"，只做可解释的统计信号测量与风格改写。
"""

from __future__ import annotations

__project__ = "Misa's AI Paper Processing Project"
__author__ = "Misa"
__version__ = "0.1.0"
__release__ = "0.1"
__attribution__ = f"本项目由 {__author__} 制作 · v{__release__}"

from .analysis.features import analyze, AnalysisResult  # noqa: E402
from .transform.humanize import humanize, HumanizeResult  # noqa: E402
from .watermark.unicode_scan import scan_invisible, clean_invisible  # noqa: E402

__all__ = [
    "__project__",
    "__author__",
    "__version__",
    "__attribution__",
    "analyze",
    "AnalysisResult",
    "humanize",
    "HumanizeResult",
    "scan_invisible",
    "clean_invisible",
]
