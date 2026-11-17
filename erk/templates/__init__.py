"""分析模板中心。

提供：
  - AnalysisTemplate / TemplateRegistry：模板数据结构与检索
  - 识别策略决策树：recommend_method（识别优先）
  - 内置模板：finance / did / iv / rdd / psm
  - 8 步实证闭环常量 EMPIRICAL_STEPS
"""

from erk.templates.base import EMPIRICAL_STEPS, AnalysisTemplate, TemplateRegistry
from erk.templates.catalog import build_registry
from erk.templates.decision import (
    METHOD_CHECKS,
    METHOD_REFERENCES,
    MethodRecommendation,
    method_checks,
    recommend_method,
)

_REGISTRY = build_registry()

# ---- 兼容旧接口（cli 依赖） ----

def list_templates() -> list[str]:
    return _REGISTRY.list()


def describe_template(name: str) -> str:
    return _REGISTRY.describe(name)


def get_template(name: str) -> AnalysisTemplate | None:
    return _REGISTRY.get(name)


def search_templates(method: str | None = None, tag: str | None = None) -> list[str]:
    return _REGISTRY.search(method=method, tag=tag)


__all__ = [
    "EMPIRICAL_STEPS",
    "AnalysisTemplate",
    "TemplateRegistry",
    "MethodRecommendation",
    "recommend_method",
    "method_checks",
    "METHOD_CHECKS",
    "METHOD_REFERENCES",
    "list_templates",
    "describe_template",
    "get_template",
    "search_templates",
]
