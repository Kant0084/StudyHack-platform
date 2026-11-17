"""统一结果契约的通用辅助。

借鉴 StatsPAI 的「单一 JSON 安全序列化器」设计：所有 to_dict / 未来 MCP
序列化都汇到 to_jsonable 一处，避免 numpy 标量、NaN/Inf、DataFrame 导致
JSON 序列化失败。

信封三档 detail 语义（供各结果类复用）：
  - minimal : 核心估计量 + 样本量（Agent 低 token 消费）
  - standard: 完整结果
  - agent   : standard + warnings + next_steps（学术风险提示与建议）
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

_MAX_DEPTH = 6


def to_jsonable(obj: Any, depth: int = 0) -> Any:
    """把任意对象转为 JSON 安全结构（numpy→python、NaN/Inf→None、截断 DataFrame）。

    深度超限时退回 str() 兜底，保证序列化永不因类型问题失败。
    """
    if depth > _MAX_DEPTH:
        return str(obj)

    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, np.ndarray):
        return [to_jsonable(x, depth + 1) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {k: to_jsonable(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x, depth + 1) for x in obj]
    if isinstance(obj, pd.DataFrame):
        return to_jsonable(obj.head(20).to_dict("records"), depth + 1)
    if isinstance(obj, pd.Series):
        return to_jsonable(obj.head(20).to_dict(), depth + 1)

    return str(obj)
