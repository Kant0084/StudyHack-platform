"""内置分析模板目录。"""

from __future__ import annotations

from erk.templates.base import AnalysisTemplate, TemplateRegistry
from erk.templates.decision import METHOD_CHECKS, METHOD_REFERENCES

FINANCE = AnalysisTemplate(
    name="finance",
    title="公司金融基准回归",
    description="上市公司面板数据基准回归示例（OLS + 双向固定效应 + 公司层面聚类）。",
    methods=["ols", "fe", "cluster"],
    required_vars=["roa", "lev", "size", "firm_id", "year"],
    checks=["聚类标准误层级（公司层面）", "固定效应选择（个体/时间）"],
    references=["Wooldridge (2010)"],
    tags=["经管", "面板", "公司金融"],
)

DID = AnalysisTemplate(
    name="did",
    title="双重差分（政策评估）",
    description="政策/冲击的因果效应评估，支持交错处理（多期 DID）。",
    methods=["did"],
    required_vars=["dep", "treat", "post", "id", "time"],
    checks=METHOD_CHECKS["did"],
    references=METHOD_REFERENCES["did"],
    tags=["政策评估", "因果推断", "面板"],
)

IV = AnalysisTemplate(
    name="iv",
    title="工具变量法（2SLS）",
    description="用工具变量处理遗漏变量/双向因果导致的内生性。",
    methods=["iv", "ols"],
    required_vars=["dep", "x", "instrument"],
    checks=METHOD_CHECKS["iv"],
    references=METHOD_REFERENCES["iv"],
    tags=["因果推断", "内生性"],
)

RDD = AnalysisTemplate(
    name="rdd",
    title="断点回归",
    description="处理由断点/阈值规则决定时的局部处理效应识别。",
    methods=["rdd"],
    required_vars=["dep", "running_var", "treat"],
    checks=METHOD_CHECKS["rdd"],
    references=METHOD_REFERENCES["rdd"],
    tags=["因果推断", "断点"],
)

PSM = AnalysisTemplate(
    name="psm",
    title="倾向得分匹配",
    description="基于可观测变量的选择偏差校正（匹配后估计处理效应）。",
    methods=["psm"],
    required_vars=["dep", "treat", "covariates"],
    checks=METHOD_CHECKS["psm"],
    references=METHOD_REFERENCES["psm"],
    tags=["因果推断", "匹配"],
)


def build_registry() -> TemplateRegistry:
    """构建内置模板注册表。"""
    reg = TemplateRegistry()
    for t in (FINANCE, DID, IV, RDD, PSM):
        reg.register(t)
    return reg
