"""问卷数据结构（QuestionnaireDataset）。

统一的问卷数据入口：承载原始数据 + 变量元数据，提供信效度、
描述统计、差异检验的高层方法。后续可扩展问卷星/问卷网的原生解析
（见 Roadmap，参考 wjx-ai-kit 的题型映射与 submitdata 解码）。
"""

from __future__ import annotations

import pandas as pd

from erk.survey.descriptives import describe_continuous, frequency_table
from erk.survey.reliability import ReliabilityResult, run_reliability


class QuestionnaireDataset:
    """问卷数据集：宽表形式，每列一个变量/题项。"""

    def __init__(self, data: pd.DataFrame, variables: list | None = None):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data 必须是 pandas.DataFrame")
        self.data = data
        self.variables = list(variables) if variables else []

    # ---- 基础属性 ----

    @property
    def n_samples(self) -> int:
        return len(self.data)

    @property
    def columns(self) -> list[str]:
        return list(self.data.columns)

    # ---- 变量元数据（来自问卷星导入器） ----

    @property
    def scale_columns(self) -> list[str]:
        """量表题列名（供信效度分析）。"""
        if self.variables:
            return [v.name for v in self.variables if v.q_type == "scale"]
        # 无元数据时，退化为数值列（启发式）
        return [c for c in self.data.columns if pd.api.types.is_numeric_dtype(self.data[c])]

    def variables_of_type(self, q_type: str) -> list[str]:
        """按题型筛选变量列名。"""
        return [v.name for v in self.variables if v.q_type == q_type]

    # ---- 量表与信效度 ----

    def scale_items(self, cols: list[str]) -> "pd.DataFrame":
        """提取量表题项并数值化（缺失值保留为 NaN，交由信度计算 listwise 处理）。"""
        return self.data[cols].apply(pd.to_numeric, errors="coerce")

    def reliability(self, cols: list[str]) -> ReliabilityResult:
        """对指定量表题项做信效度检验（Cronbach's α / KMO / Bartlett）。"""
        items = self.scale_items(cols).to_numpy(dtype=float)
        return run_reliability(items, item_labels=list(cols))

    # ---- 描述统计 ----

    def frequency(self, col: str) -> pd.DataFrame:
        """单变量频数表。"""
        return frequency_table(self.data[col])

    def descriptives(self, cols: list[str] | None = None) -> pd.DataFrame:
        """连续变量描述统计。"""
        return describe_continuous(self.data, cols)

    # ---- 差异与相关 ----

    def t_test(self, col: str, group_col: str, group_a, group_b):
        """独立样本 t 检验（按分组变量拆两组）。"""
        from erk.survey.inferential import independent_t_test

        a = self.data.loc[self.data[group_col] == group_a, col]
        b = self.data.loc[self.data[group_col] == group_b, col]
        return independent_t_test(a, b)

    def anova(self, col: str, group_col: str):
        """单因素方差分析（按分组变量拆多组）。"""
        from erk.survey.inferential import one_way_anova

        groups = [g[col] for _, g in self.data.groupby(group_col)]
        return one_way_anova(*groups)

    def correlate(self, x: str, y: str):
        """皮尔逊相关。"""
        from erk.survey.inferential import pearson_correlation

        return pearson_correlation(self.data[x], self.data[y])
