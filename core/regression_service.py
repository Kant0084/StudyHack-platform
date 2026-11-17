"""经管实证分析服务（薄封装 erk.stats + erk.data）。

输入：面板/截面数据 DataFrame。
输出：结构化结果 dict（预处理 → 描述统计 → 相关 → 基准回归 → 分组回归）。

回归计算调用 ERK 内置 OLS 引擎（对标 Stata 17 reg），仅封装参数与结果。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.correlation import correlation_matrix
from core.stats_interpret import interpret_coef

from erk.stats.regression import run_ols
from erk.data.clean import winsorize, drop_missing
from erk.config import Config


# ---- 预处理 ----

def preprocess(
    df: pd.DataFrame,
    missing: str = "drop",
    winsor_lower: float | None = 0.01,
    winsor_upper: float | None = None,
    winsor_cols: list[str] | None = None,
    standardize: bool = False,
    std_cols: list[str] | None = None,
) -> pd.DataFrame:
    """数据预处理（默认自动执行）。

    参数：
      missing      : "drop" 删除缺失 / "mean" 均值填充 / "median" 中位数填充 / "none"
      winsor_lower : 缩尾下分位（None 表示不缩尾）；upper 默认 = 1 - lower
      winsor_cols  : 缩尾的数值列（None = 全部数值列）
      standardize  : 是否对数值变量 z-score 标准化
      std_cols     : 标准化列（None = 全部数值列）
    """
    out = df.copy()
    num_cols = out.select_dtypes(include=[np.number]).columns.tolist()

    # 缺失值处理
    if missing == "drop":
        out = drop_missing(out)
    elif missing in ("mean", "median"):
        for c in num_cols:
            out[c] = out[c].fillna(out[c].mean() if missing == "mean" else out[c].median())

    # 缩尾（仅数值列，保护用户未指定的分类列）
    if winsor_lower is not None:
        upper = winsor_upper if winsor_upper is not None else 1 - winsor_lower
        targets = winsor_cols or num_cols
        for c in targets:
            if c in out.columns:
                out[c] = winsorize(out[c], lower=winsor_lower, upper=upper)

    # 标准化（z-score）
    if standardize:
        targets = std_cols or num_cols
        for c in targets:
            if c in out.columns:
                s = out[c]
                sd = s.std(ddof=1)
                out[c] = (s - s.mean()) / sd if sd and sd > 0 else s - s.mean()

    return out.reset_index(drop=True)


# ---- 描述统计（中文列名） ----

def describe(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    d = pd.DataFrame(
        {
            "观测值": sub.count(),
            "均值": sub.mean().round(3),
            "标准差": sub.std(ddof=1).round(3),
            "最小值": sub.min().round(3),
            "中位数": sub.median().round(3),
            "最大值": sub.max().round(3),
        }
    )
    return d


# ---- 回归结果封装 ----

def _result_to_dict(r, dep: str) -> dict:
    """把 RegressionResult 转成页面友好结构。"""
    tidy = r.tidy()
    return {
        "dep": dep,
        "nobs": r.nobs,
        "r2": r.r2,
        "adj_r2": r.adj_r2,
        "f_stat": None,
        "label": r.label,
        "fe": list(r.fe),
        "cluster": r.cluster,
        "tidy": tidy,
        "warnings": r.to_dict("agent").get("warnings", []),
    }


def _f_statistic(r, n_indep: int) -> float | None:
    """整体显著性 F 统计量（ERK 未存，此处按标准公式补算）。

    F = (R²/k) / ((1-R²)/(n-k-1))，其中 k 为自变量个数（含固定效应 dummy 数）。
    该公式对应 Stata reg 输出的 F 检验（不含聚类校正口径）。
    """
    k = n_indep + len(r.fe)
    n = r.nobs
    if r.r2 >= 1.0 or (n - k - 1) <= 0 or k <= 0:
        return None
    return (r.r2 / k) / ((1 - r.r2) / (n - k - 1))


def run_baseline(
    df: pd.DataFrame,
    dep: str,
    indep: list[str],
    fe: list[str] | None = None,
    cluster: str | None = None,
    label: str = "(1)",
) -> dict:
    """基准 OLS 回归。"""
    r = run_ols(df, dep, indep, fe=fe, cluster=cluster, label=label)
    d = _result_to_dict(r, dep)
    d["f_stat"] = _f_statistic(r, len(indep))
    # 补充解读：对第一个自变量（通常为核心解释变量）生成解读
    if indep:
        first = indep[0]
        if first in r.params:
            d["interpret"] = interpret_coef(first, r.params[first], r.pvalues[first])
    return d


def run_grouped(
    df: pd.DataFrame,
    dep: str,
    indep: list[str],
    group_col: str,
    fe: list[str] | None = None,
    cluster: str | None = None,
) -> dict:
    """分组回归（异质性分析）。按 group_col 取值分组，每组跑一次 OLS。"""
    groups = sorted(df[group_col].dropna().unique())
    results = []
    for g in groups:
        sub = df[df[group_col] == g]
        if len(sub) <= len(indep) + 3:
            results.append({"group": str(g), "error": f"样本量不足（n={len(sub)}）"})
            continue
        try:
            r = run_ols(sub, dep, indep, fe=fe, cluster=cluster, label=str(g))
            d = _result_to_dict(r, dep)
            d["f_stat"] = _f_statistic(r, len(indep))
            results.append({"group": str(g), **d})
        except Exception as exc:  # noqa: BLE001
            results.append({"group": str(g), "error": str(exc)})
    return {"group_col": group_col, "groups": [str(g) for g in groups], "results": results}


def analyze_regression(
    df: pd.DataFrame,
    dep: str,
    indep: list[str],
    fe: list[str] | None = None,
    cluster: str | None = None,
    missing: str = "drop",
    winsor_lower: float | None = 0.01,
    standardize: bool = False,
    group_col: str | None = None,
) -> dict:
    """经管实证全链路分析。"""
    # 预处理
    df_clean = preprocess(
        df, missing=missing, winsor_lower=winsor_lower, standardize=standardize
    )
    result: dict = {"n_before": len(df), "n_after": len(df_clean)}

    # 描述统计
    desc_cols = [dep] + indep
    desc_cols = [c for c in desc_cols if c in df_clean.columns]
    result["descriptives"] = describe(df_clean, desc_cols)

    # 相关性矩阵（Pearson）
    if len(desc_cols) >= 2:
        labeled, coef, pval = correlation_matrix(df_clean, desc_cols, method="pearson")
        result["correlation"] = {"labeled": labeled, "coef": coef, "p": pval}

    # 基准回归
    result["baseline"] = run_baseline(df_clean, dep, indep, fe=fe, cluster=cluster)

    # 分组回归（可选）
    if group_col and group_col in df_clean.columns:
        result["grouped"] = run_grouped(df_clean, dep, indep, group_col, fe=fe, cluster=cluster)

    return result
