"""数据预处理工具服务。

独立功能：去重、缺失值处理、长宽表转换、标准化/归一化、格式统一。
处理后可直接导出 Excel，也可跳转至分析模块继续处理。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def deduplicate(df: pd.DataFrame, subset: list[str] | None = None, keep: str = "first") -> pd.DataFrame:
    """去重。subset 为空则整行去重。"""
    return df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)


def handle_missing(df: pd.DataFrame, strategy: str = "drop", cols: list[str] | None = None) -> pd.DataFrame:
    """缺失值处理：drop / mean / median / mode。

    cols 为空则作用于全部列；仅数值列支持均值/中位数，分类列用众数兜底。
    """
    out = df.copy()
    targets = cols or list(df.columns)
    for c in targets:
        if c not in out.columns:
            continue
        if strategy == "drop":
            out = out.dropna(subset=[c])
        elif strategy == "mean":
            if pd.api.types.is_numeric_dtype(out[c]):
                out[c] = out[c].fillna(out[c].mean())
        elif strategy == "median":
            if pd.api.types.is_numeric_dtype(out[c]):
                out[c] = out[c].fillna(out[c].median())
        elif strategy == "mode":
            m = out[c].mode()
            if not m.empty:
                out[c] = out[c].fillna(m.iloc[0])
    return out.reset_index(drop=True)


def wide_to_long(df: pd.DataFrame, id_vars: list[str], value_vars: list[str],
                 var_name: str = "变量", value_name: str = "取值") -> pd.DataFrame:
    """宽表转长表（melt）。"""
    return df.melt(id_vars=id_vars, value_vars=value_vars, var_name=var_name, value_name=value_name)


def long_to_wide(df: pd.DataFrame, index: list[str], columns: str, values: str,
                 aggfunc: str = "mean") -> pd.DataFrame:
    """长表转宽表（pivot_table）。"""
    return df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc).reset_index()


def standardize(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """z-score 标准化（均值为 0，标准差为 1）。"""
    out = df.copy()
    targets = cols or out.select_dtypes(include=[np.number]).columns.tolist()
    for c in targets:
        if c in out.columns and pd.api.types.is_numeric_dtype(out[c]):
            s = out[c]
            sd = s.std(ddof=1)
            out[c] = (s - s.mean()) / sd if sd and sd > 0 else 0.0
    return out


def normalize(df: pd.DataFrame, cols: list[str] | None = None, lower: float = 0.0, upper: float = 1.0) -> pd.DataFrame:
    """min-max 归一化到 [lower, upper]。"""
    out = df.copy()
    targets = cols or out.select_dtypes(include=[np.number]).columns.tolist()
    for c in targets:
        if c in out.columns and pd.api.types.is_numeric_dtype(out[c]):
            s = out[c]
            lo, hi = s.min(), s.max()
            if hi > lo:
                out[c] = lower + (s - lo) / (hi - lo) * (upper - lower)
            else:
                out[c] = lower
    return out


def unify_format(df: pd.DataFrame) -> pd.DataFrame:
    """格式统一：去除列名首尾空白、数值列强制转数值（无法转则保留）。"""
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    for c in out.columns:
        try:
            out[c] = pd.to_numeric(out[c], errors="raise")
        except (ValueError, TypeError):
            pass
    return out
