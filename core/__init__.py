"""StudyHack 平台 core 层 —— ERK 薄封装。

设计原则（严格对齐参赛要求）：
1. 只做「参数校验、结果封装、错误友好提示、报告后处理」，绝不复制/改写 ERK 核心计算逻辑；
2. 通过 sys.path 将 empirical-research-kit/src 加入导入路径，保证参赛作品可移植部署；
3. 所有统计计算直接调用 erk.*，确保对标 SPSS 26 / Stata 17 的准确性。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 定位 ERK 源码目录，按优先级：本地 vendored erk → 上级 empirical-research-kit/src。
# 本地开发用上级目录，云端部署时仅打包本目录，故优先使用 vendored 副本。
_ERK_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "erk",                                        # 本地 vendored
    Path(__file__).resolve().parent.parent.parent / "empirical-research-kit" / "src",      # 上级源码
]
for _p in _ERK_CANDIDATES:
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

__all__ = ["survey_service", "regression_service", "preprocessing_service", "report_service", "correlation"]
