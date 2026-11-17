"""相关性分析（Pearson / Spearman 相关系数矩阵）。

对标 SPSS 26：SPSS 的 Bivariate Correlations 采用 Pearson 积矩相关，
Spearman 为秩相关；显著性为双侧检验。本模块用 scipy.stats 复现，
误差与 SPSS 一致（均为标准公式）。

显著性标注规范（严格遵循系统提示词 3.1.1 / 3.1.2）：
  * p < 0.05, ** p < 0.01, *** p < 0.001
（注意：与回归三线表的经管惯例 "*** p<0.01" 不同，相关性采用社科/SPSS 惯例）
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _star(p: float) -> str:
    """按社科惯例返回显著性星号。"""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def correlation_matrix(
    df: pd.DataFrame,
    cols: list[str],
    method: str = "pearson",
    decimals: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """计算相关系数矩阵。

    参数：
      df      : 样本数据
      cols    : 参与相关的数值列
      method  : "pearson" 或 "spearman"
      decimals: 保留小数位

    返回：
      (标注表, 系数表, p值表)
      - 标注表：系数 + 星号（供展示/写入报告），下三角为系数，对角为 1；
      - 系数表：纯数值相关系数；
      - p值表 ：双侧检验 p 值。
    """
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    n = len(cols)
    coef = np.eye(n)
    pval = np.zeros((n, n))
    func = stats.pearsonr if method == "pearson" else stats.spearmanr

    for i in range(n):
        for j in range(i + 1, n):
            # listwise 处理：仅保留两列均非缺失的样本
            pair = sub[[cols[i], cols[j]]].dropna()
            if len(pair) < 3 or pair[cols[i]].nunique() < 2 or pair[cols[j]].nunique() < 2:
                coef[i, j] = coef[j, i] = np.nan
                pval[i, j] = pval[j, i] = np.nan
                continue
            r, p = func(pair[cols[i]], pair[cols[j]])
            coef[i, j] = coef[j, i] = r
            pval[i, j] = pval[j, i] = p

    coef_df = pd.DataFrame(coef, index=cols, columns=cols).round(decimals)
    p_df = pd.DataFrame(pval, index=cols, columns=cols)

    # 标注表：下三角显示「系数+星号」，对角线为 1，上三角留空
    # 用 object 类型以容纳「数字 + 星号」的混合字符串
    labeled = coef_df.astype(object)
    for i in range(n):
        for j in range(n):
            if i == j:
                labeled.iloc[i, j] = "1"
            elif i > j:
                r = coef_df.iloc[i, j]
                if np.isnan(r):
                    labeled.iloc[i, j] = "—"
                else:
                    labeled.iloc[i, j] = f"{r:.{decimals}f}{_star(p_df.iloc[i, j])}"
            else:
                labeled.iloc[i, j] = ""

    return labeled, coef_df, p_df


def _star_legend() -> str:
    return "注：* p<0.05, ** p<0.01, *** p<0.001"
