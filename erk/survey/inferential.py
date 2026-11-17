"""问卷差异与相关分析（scipy 封装）。

风险说明：本模块封装 scipy 的经典检验，仅用于基础差异/相关分析；
复杂抽样、多元校正等进阶情形应参考专业统计软件口径。
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy import stats


@dataclass
class TestResult:
    """单次检验的标准化结果。"""

    method: str
    statistic: float
    p_value: float
    df: float | None = None
    effect_size: float | None = None  # 效应量（Cohen's d / Cramer's V / r）

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "df": self.df,
            "effect_size": self.effect_size,
        }


def independent_t_test(a, b) -> TestResult:
    """独立样本 t 检验（Welch，不假定方差齐性）。"""
    a = _to_numeric(a)
    b = _to_numeric(b)
    t, p = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
    # Cohen's d
    d = _cohens_d(a, b)
    return TestResult("independent_t_test", float(t), float(p), effect_size=d)


def one_way_anova(*groups) -> TestResult:
    """单因素方差分析。"""
    groups = [_to_numeric(g) for g in groups]
    f, p = stats.f_oneway(*groups)
    return TestResult("one_way_anova", float(f), float(p))


def chi_square_test(contingency) -> TestResult:
    """卡方独立性检验（输入列联表）。"""
    chi2, p, dof, _ = stats.chi2_contingency(contingency)
    # Cramer's V
    n = contingency.sum()
    min_dim = min(contingency.shape) - 1
    v = float((chi2 / n / min_dim) ** 0.5) if (min_dim > 0 and n > 0) else None
    return TestResult("chi_square", float(chi2), float(p), df=dof, effect_size=v)


def pearson_correlation(x, y) -> TestResult:
    """皮尔逊相关（r 本身即效应量）。"""
    x = _to_numeric(x)
    y = _to_numeric(y)
    r, p = stats.pearsonr(x, y)
    return TestResult("pearson_correlation", float(r), float(p), effect_size=float(r))


def _to_numeric(s):
    import pandas as pd

    if not isinstance(s, pd.Series):
        s = pd.Series(s)
    return pd.to_numeric(s, errors="coerce").dropna().to_numpy()


def _cohens_d(a, b) -> float | None:
    """Cohen's d（合并标准差）。"""
    import numpy as np

    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return None
    return float((np.mean(a) - np.mean(b)) / pooled)
