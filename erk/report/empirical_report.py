"""经管实证分析报告生成。

从回归结果 + 描述统计生成实证报告：描述统计 → 基准回归（三线表）→ 结论。
"""

from __future__ import annotations

import pandas as pd

from erk.config import Config
from erk.report.builder import ReportBuilder
from erk.report.table import RegressionTable
from erk.stats.regression import RegressionResult


def build_empirical_report(
    results: list[RegressionResult],
    cfg: Config | None = None,
    descriptives: pd.DataFrame | None = None,
    title: str = "经管实证分析报告",
) -> ReportBuilder:
    """生成经管实证报告（Markdown）。"""
    cfg = cfg or Config()
    b = ReportBuilder(title)

    # 一、描述统计
    if descriptives is not None:
        b.heading("一、描述统计", 2)
        b.table(descriptives, "主要变量描述统计")

    # 二、基准回归结果
    b.heading("二、基准回归结果", 2)
    table = RegressionTable(results, cfg, title="表1 基准回归结果")
    b.raw(table.render_markdown())

    # 三、结论与风险提示
    b.heading("三、结论与建议", 2)
    for i, r in enumerate(results):
        label = r.label or f"({i + 1})"
        for w in r.to_dict("agent").get("warnings", []):
            b.note(f"{label}: {w}")
    if not any(r.to_dict("agent").get("warnings") for r in results):
        b.paragraph("回归结果未见明显方法风险，建议补充稳健性检验与机制分析。")

    return b
