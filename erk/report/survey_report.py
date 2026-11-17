"""问卷分析报告生成。

从 QuestionnaireDataset 生成完整问卷报告：
数据概览 → 描述统计 → 信度 → 效度（KMO/Bartlett/EFA）→ 结论与建议。
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from erk.report.builder import ReportBuilder
from erk.survey.dataset import QuestionnaireDataset


def build_survey_report(
    ds: QuestionnaireDataset,
    scale_cols: list[str] | None = None,
    title: str = "问卷分析报告",
) -> ReportBuilder:
    """生成问卷分析报告（Markdown）。"""
    b = ReportBuilder(title)
    scale_cols = scale_cols or ds.scale_columns

    # 一、数据概览
    b.heading("一、数据概览", 2)
    b.paragraph(f"有效样本量：{ds.n_samples} 份；变量总数：{len(ds.columns)} 个。")
    if ds.variables:
        dist = Counter(v.q_type for v in ds.variables)
        type_names = {
            "single": "单选题", "multi": "多选题", "scale": "量表题",
            "text": "开放题", "continuous": "连续变量",
        }
        b.paragraph(
            "题型分布：" + "；".join(f"{type_names.get(k, k)} {c} 个" for k, c in dist.items()) + "。"
        )

    # 二、描述统计
    b.heading("二、描述统计", 2)
    if scale_cols:
        b.table(ds.descriptives(scale_cols), "量表题项描述统计")

    rel = None
    fa = None

    # 三、信度检验
    if len(scale_cols) >= 2:
        rel = ds.reliability(scale_cols)
        b.heading("三、信度检验", 2)
        judge = "良好" if rel.alpha_good else ("可接受" if rel.alpha_ok else "偏低")
        b.paragraph(f"Cronbach's α = {rel.alpha:.3f}（{judge}）。")
        item_df = pd.DataFrame(
            {
                "题项": scale_cols,
                "项总计相关": rel.item_total,
                "删除后 α": rel.alpha_if_deleted,
            }
        )
        b.table(item_df, "项总计统计量")

    # 四、效度检验
    if len(scale_cols) >= 3:
        b.heading("四、效度检验", 2)
        b.paragraph(
            f"KMO = {rel.kmo:.3f}（{'可接受' if rel.kmo_ok else '偏低'}）；"
            f"Bartlett 球形检验 χ² = {rel.bartlett_chi2:.2f}（df={rel.bartlett_df}），"
            f"p = {rel.bartlett_p:.4f}。"
        )
        from erk.survey.factor_analysis import factor_analysis

        fa = factor_analysis(ds.data[scale_cols].to_numpy(float), item_labels=scale_cols)
        b.paragraph(
            f"探索性因子分析提取 {fa.n_factors} 个因子，"
            f"累积方差解释率 {fa.total_variance_explained:.1%}。"
        )
        L = np.asarray(fa.loadings)
        load_df = pd.DataFrame(
            L, index=scale_cols, columns=[f"因子{i + 1}" for i in range(fa.n_factors)]
        )
        b.table(load_df.round(3), "旋转后因子载荷矩阵")

    # 五、结论与建议
    b.heading("五、结论与建议", 2)
    all_warnings = []
    if rel is not None:
        all_warnings.extend(rel.to_dict("agent").get("warnings", []))
    if fa is not None:
        all_warnings.extend(fa.to_dict("agent").get("warnings", []))
    if all_warnings:
        for w in all_warnings:
            b.note(w)
    else:
        b.paragraph("量表信效度良好，各项指标均达到可接受标准。")

    return b
