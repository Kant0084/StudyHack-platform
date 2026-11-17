"""问卷智能分析服务（薄封装 erk.survey）。

输入：问卷星/腾讯问卷原生导出的 DataFrame（宽表，题目为表头）。
输出：结构化结果 dict，供页面层展示与报告层消费。

题型识别、信效度计算全部调用 ERK 内核，仅做结果封装与学术解读补充。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.correlation import correlation_matrix
from core.stats_interpret import (
    interpret_alpha,
    interpret_factor,
    interpret_kmo_bartlett,
)

from erk.survey.importer import QuestionnaireImporter
from erk.survey.factor_analysis import factor_analysis


def _safe(obj, key, default):
    return getattr(obj, key, default)


def analyze_survey(df: pd.DataFrame, scale_cols: list[str] | None = None, n_factors: int | None = None) -> dict:
    """问卷全链路分析。

    参数：
      df        : 问卷数据（宽表）
      scale_cols: 量表题列名；None 时由 ERK 自动识别
      n_factors : 因子数；None 时用 Kaiser 准则

    返回 dict：
      variables / scale_cols / n_samples / reliability / validity /
      descriptives / correlation / frequency（供页面渲染）
    """
    ds = QuestionnaireImporter.from_dataframe(df)
    auto_scale = ds.scale_columns
    scale_cols = scale_cols if scale_cols else auto_scale

    result: dict = {
        "variables": [v.to_dict() for v in ds.variables],
        "scale_cols": list(scale_cols),
        "auto_scale_cols": list(auto_scale),
        "n_samples": ds.n_samples,
        "type_dist": _type_distribution(ds),
    }

    # 1) 信度（需 ≥2 个量表题）
    if len(scale_cols) >= 2:
        rel = ds.reliability(scale_cols)
        item_df = pd.DataFrame(
            {
                "题项": scale_cols,
                "项总计相关(CITC)": rel.item_total,
                "删除后α系数": rel.alpha_if_deleted,
            }
        )
        result["reliability"] = {
            "alpha": rel.alpha,
            "n_items": rel.n_items,
            "n_samples": rel.n_samples,
            "item_table": item_df,
            "interpret": interpret_alpha(rel.alpha),
            "warnings": rel.to_dict("agent").get("warnings", []),
        }
        result["rel"] = rel  # 供报告层复用
    else:
        result["reliability"] = None

    # 2) 效度（需 ≥3 个量表题）
    if len(scale_cols) >= 3:
        rel = result.get("rel")
        kmo = rel.kmo if rel is not None else float("nan")
        bartlett_p = rel.bartlett_p if rel is not None else float("nan")
        fa = factor_analysis(ds.data[scale_cols].to_numpy(float), n_factors=n_factors, item_labels=scale_cols)
        loadings = np.asarray(fa.loadings)
        load_df = pd.DataFrame(
            loadings, index=scale_cols, columns=[f"因子{i + 1}" for i in range(fa.n_factors)]
        ).round(3)
        var_df = pd.DataFrame(
            {
                "因子": [f"因子{i + 1}" for i in range(fa.n_factors)],
                "特征值": fa.eigenvalues[: fa.n_factors],
                "方差解释率(%)": [round(v * 100, 2) for v in fa.variance_explained],
                "累计方差解释率(%)": [round(v * 100, 2) for v in fa.cumulative_variance],
            }
        )
        result["validity"] = {
            "kmo": kmo,
            "bartlett_chi2": rel.bartlett_chi2 if rel is not None else float("nan"),
            "bartlett_df": rel.bartlett_df if rel is not None else 0,
            "bartlett_p": bartlett_p,
            "n_factors": fa.n_factors,
            "total_variance": fa.total_variance_explained,
            "loading_table": load_df,
            "variance_table": var_df,
            "interpret": interpret_kmo_bartlett(kmo, bartlett_p) + " " + interpret_factor(fa.total_variance_explained, fa.n_factors),
            "warnings": fa.to_dict("agent").get("warnings", []),
        }
        result["fa"] = fa
    else:
        result["validity"] = None

    # 3) 描述统计（量表题）
    if scale_cols:
        result["descriptives"] = ds.descriptives(scale_cols)
    else:
        result["descriptives"] = None

    # 4) 相关性矩阵（量表题，Pearson，社科惯例标注）
    if len(scale_cols) >= 2:
        labeled, coef, pval = correlation_matrix(ds.data, scale_cols, method="pearson")
        result["correlation"] = {"labeled": labeled, "coef": coef, "p": pval}
    else:
        result["correlation"] = None

    # 5) 频数分析（单选题）
    single_cols = ds.variables_of_type("single")
    freq_tables = {}
    for c in single_cols[:20]:  # 限制数量，避免页面过载
        freq_tables[c] = ds.frequency(c)
    result["frequency"] = {"single_cols": single_cols, "tables": freq_tables}

    return result


def _type_distribution(ds) -> dict:
    from collections import Counter

    dist = Counter(v.q_type for v in ds.variables)
    names = {
        "single": "单选题",
        "multi": "多选题",
        "scale": "量表题",
        "text": "开放题",
        "continuous": "连续变量",
    }
    return {names.get(k, k): c for k, c in dist.items()}


def list_survey_columns(df: pd.DataFrame) -> dict:
    """预览问卷识别结果（供上传后即时展示列识别情况）。"""
    ds = QuestionnaireImporter.from_dataframe(df)
    return {
        "variables": [v.to_dict() for v in ds.variables],
        "scale_cols": ds.scale_columns,
        "n_samples": ds.n_samples,
        "type_dist": _type_distribution(ds),
    }
