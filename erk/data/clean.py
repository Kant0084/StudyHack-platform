"""数据清洗与变量构造。

边界说明：本模块只做「数据层面」的预处理（缩尾、缺失值、虚拟变量、
衍生变量），这类操作属于数据处理，工具可自行实现；统计推断本身
（回归、检验、内生性方法）一律交由专业软件，见 io/ 模块。
"""

from __future__ import annotations

import pandas as pd


def winsorize(s: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    """缩尾：将超出 [lower, upper] 分位数的值压缩到边界。

    风险说明：缩尾分位数的选择应结合样本与研究惯例，常用 1%/99% 或 5%/95%，
    具体取值须在论文中披露，工具不替用户「臆造」合理阈值。
    """
    lo, hi = s.quantile(lower), s.quantile(upper)
    return s.clip(lo, hi)


def drop_missing(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    """剔除指定列缺失的样本，返回新 DataFrame（不修改原数据）。"""
    cols = subset if subset is not None else df.columns.tolist()
    return df.dropna(subset=cols).reset_index(drop=True)


def to_dummy(df: pd.DataFrame, col: str, prefix: str | None = None) -> pd.DataFrame:
    """生成虚拟变量并拼接回原表，删除原列并丢弃一个基准组（避免共线性）。"""
    dummies = pd.get_dummies(df[col], prefix=prefix or col, drop_first=True)
    return pd.concat([df.drop(columns=[col]), dummies.astype(int)], axis=1)
