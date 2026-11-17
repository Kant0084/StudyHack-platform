"""问卷描述统计。"""

from __future__ import annotations

import pandas as pd


def frequency_table(series: pd.Series, dropna: bool = True) -> pd.DataFrame:
    """频数表（分类变量 / 量表题）。

    返回：index 为取值，列 count（频数）、percent（百分比）。
    """
    s = series.dropna() if dropna else series
    counts = s.value_counts().sort_index()
    total = len(s)
    if total == 0:
        empty = pd.DataFrame(columns=["count", "percent"])
        empty.index.name = series.name
        return empty
    df = pd.DataFrame(
        {
            "count": counts.values,
            "percent": (counts.values / total * 100).round(2),
        },
        index=counts.index,
    )
    df.index.name = series.name
    return df


def describe_continuous(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """连续变量描述统计：N、均值、标准差、中位数、最小、最大。"""
    cols = cols or list(df.columns)
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    return pd.DataFrame(
        {
            "n": sub.count(),
            "mean": sub.mean().round(3),
            "std": sub.std(ddof=1).round(3),
            "median": sub.median().round(3),
            "min": sub.min().round(3),
            "max": sub.max().round(3),
        }
    )
