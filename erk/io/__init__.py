"""三大统计软件对接层。

负责「脚本生成 → 静默运行 → 日志解析 → 结果标准化」，是「专业计算交给
专业软件」原则的落点。所有回读结果归一为 stats.regression.RegressionResult。

统一契约：EngineAdapter.run() 永不抛异常，软件未安装/不支持/错误都归一为
EngineEstimate(status=ok/skipped/unavailable/error)，缺失即降级而非崩溃。
"""

from erk.io.base import (
    STATUS_ERROR,
    STATUS_OK,
    STATUS_SKIPPED,
    STATUS_UNAVAILABLE,
    EngineAdapter,
    EngineEstimate,
)
from erk.io.r import RAdapter
from erk.io.spss import SpssAdapter, find_spss
from erk.io.stata import StataAdapter, find_stata

__all__ = [
    "EngineAdapter",
    "EngineEstimate",
    "StataAdapter",
    "RAdapter",
    "SpssAdapter",
    "find_stata",
    "find_spss",
    "STATUS_OK",
    "STATUS_SKIPPED",
    "STATUS_UNAVAILABLE",
    "STATUS_ERROR",
]
