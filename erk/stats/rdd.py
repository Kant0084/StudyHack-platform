"""RDD 断点回归（内置引擎预览）。

核心：处理由 running variable 是否跨越断点（cutoff）决定，
估计断点处的局部处理效应（LATE）。

实现：断点两侧局部线性回归（三角核加权），断点处两侧截距差 = 处理效应
（对标 rdrobust 的默认「局部线性 + 三角核」思路）。

风险说明（诚实标注）：
  - 带宽选择用简化规则（h = C·σ·n^(-1/5)），非 rdrobust 的 MSE 最优带宽；
  - 标准误为局部线性回归标准误，未做稳健校正；
    正式结果建议用 rdrobust（R/Stata）复核，并补 McCrary 密度检验、
    安慰剂断点、带宽敏感性（见 templates/decision.py 的必查诊断）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def _triangular_kernel(d: np.ndarray, h: float) -> np.ndarray:
    """三角核权重：w = (1 - |d|/h) · I(|d| < h)。"""
    w = 1 - np.abs(d) / h
    w[w < 0] = 0.0
    return w


def _local_linear_at_cutoff(x: np.ndarray, y: np.ndarray, h: float) -> tuple[float | None, float | None]:
    """在 x=0（断点）处的局部线性预测，返回 (截距, 截距标准误)。

    x 为已中心化的 running variable（d = x - cutoff）。
    """
    mask = _triangular_kernel(x, h) > 0
    if mask.sum() < 2:
        return None, None
    X = sm.add_constant(x[mask])
    w = _triangular_kernel(x[mask], h)
    model = sm.WLS(y[mask], X, weights=w).fit()
    return float(model.params[0]), float(model.bse[0])


def _ik_bandwidth(x: np.ndarray) -> float:
    """简化 Imbens-Kalyanaraman 带宽：h = 1.84 · σ · n^(-1/5)。"""
    n = len(x)
    sigma = np.std(x, ddof=1)
    return float(1.84 * sigma * n ** (-1 / 5))


@dataclass
class RddResult:
    """RDD 断点回归结果。"""

    method: str = "rdd"
    estimate: float = float("nan")
    se: float = float("nan")
    t_stat: float = float("nan")
    p_value: float = float("nan")
    bandwidth: float = float("nan")
    cutoff: float = 0.0
    n_left: int = 0
    n_right: int = 0

    @property
    def significant(self) -> bool:
        return not np.isnan(self.p_value) and self.p_value < 0.05

    def to_dict(self, detail: str = "standard") -> dict:
        payload = {
            "method": self.method,
            "estimate": self.estimate,
            "se": self.se,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
            "bandwidth": self.bandwidth,
            "cutoff": self.cutoff,
            "n_left": self.n_left,
            "n_right": self.n_right,
        }
        if detail == "agent":
            payload["warnings"] = self._warnings()
            payload["next_steps"] = [
                "建议补 McCrary 密度检验（断点处操纵检验）。",
                "建议做安慰剂断点检验与带宽敏感性分析。",
                "正式结果建议用 rdrobust（R/Stata）复核。",
            ]
        return payload

    def _warnings(self) -> list[str]:
        warnings = []
        if self.n_left < 30 or self.n_right < 30:
            warnings.append(
                f"断点两侧样本量（左 {self.n_left} / 右 {self.n_right}）偏少，"
                "局部线性估计可能不稳定。"
            )
        warnings.append(
            "带宽为简化 IK 规则、标准误未做稳健校正；正式结果建议用 rdrobust 复核。"
        )
        return warnings


def run_rdd(
    df: pd.DataFrame,
    dep: str,
    running_var: str,
    cutoff: float = 0.0,
    bandwidth: float | None = None,
) -> RddResult:
    """RDD 断点回归，估计断点处局部处理效应。

    running_var：驱动变量（决定处理的连续变量）。
    cutoff：断点（running_var >= cutoff 视为处理组）。
    """
    x = pd.to_numeric(df[running_var], errors="coerce").to_numpy(float)
    y = pd.to_numeric(df[dep], errors="coerce").to_numpy(float)
    d = x - cutoff  # 中心化

    if bandwidth is None:
        bandwidth = _ik_bandwidth(d)

    left = d < 0
    right = d >= 0

    int_l, se_l = _local_linear_at_cutoff(d[left], y[left], bandwidth)
    int_r, se_r = _local_linear_at_cutoff(d[right], y[right], bandwidth)

    if int_l is None or int_r is None:
        return RddResult(bandwidth=bandwidth, cutoff=cutoff, n_left=int(left.sum()), n_right=int(right.sum()))

    estimate = int_r - int_l
    se = float(np.sqrt(se_l**2 + se_r**2))
    t_stat = estimate / se if se > 0 else float("nan")
    p_value = float(2 * stats.norm.sf(abs(t_stat))) if not np.isnan(t_stat) else float("nan")

    return RddResult(
        estimate=estimate,
        se=se,
        t_stat=t_stat,
        p_value=p_value,
        bandwidth=bandwidth,
        cutoff=cutoff,
        n_left=int(left.sum()),
        n_right=int(right.sum()),
    )
