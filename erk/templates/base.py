"""分析模板基础：AnalysisTemplate 数据结构 + 模板注册表。

借鉴 AERS（Auto-Empirical-Research-Skills）的模板组织：
  - 8 步实证闭环作为经管实证的标准流程骨架；
  - 每个模板声明「数据要求 + 分析方法 + 步骤 + 文献出处」；
  - 注册表提供 catalog 式检索（list/get/describe）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 经管实证研究 8 步闭环（AERS 旗舰 skill 共享的流程骨架）
EMPIRICAL_STEPS = [
    "数据导入与清洗",
    "变量构造（缩尾/虚拟变量/衍生变量）",
    "描述统计 Table 1",
    "诊断检验（VIF/Hausman/弱工具等）",
    "基准回归",
    "稳健性检验",
    "机制与异质性分析",
    "结果表图输出",
]


@dataclass
class AnalysisTemplate:
    """一个分析模板：声明某类研究的完整流程与数据要求。"""

    name: str
    title: str
    description: str
    methods: list[str]              # 方法标签：ols/fe/cluster/did/iv/rdd/psm
    required_vars: list[str]        # 必需变量角色（如 dep/treat/post/instrument）
    steps: list[str] = field(default_factory=lambda: list(EMPIRICAL_STEPS))
    checks: list[str] = field(default_factory=list)   # 必查诊断
    references: list[str] = field(default_factory=list)  # 方法出处
    tags: list[str] = field(default_factory=list)

    def validate(self, columns: list[str]) -> list[str]:
        """校验数据列是否满足模板要求，返回缺失的变量角色。"""
        cols = set(columns)
        return [v for v in self.required_vars if v not in cols]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "methods": self.methods,
            "required_vars": self.required_vars,
            "steps": self.steps,
            "checks": self.checks,
            "references": self.references,
            "tags": self.tags,
        }

    def describe(self) -> str:
        """模板说明文本。"""
        lines = [
            f"[{self.name}] {self.title}",
            f"  描述: {self.description}",
            f"  方法: {', '.join(self.methods)}",
            f"  必需变量: {', '.join(self.required_vars) if self.required_vars else '(无特殊要求)'}",
        ]
        if self.checks:
            lines.append(f"  必查诊断: {'; '.join(self.checks)}")
        if self.references:
            lines.append(f"  方法出处: {'; '.join(self.references)}")
        return "\n".join(lines)


class TemplateRegistry:
    """模板注册表（catalog）。"""

    def __init__(self):
        self._templates: dict[str, AnalysisTemplate] = {}

    def register(self, template: AnalysisTemplate) -> None:
        self._templates[template.name] = template

    def get(self, name: str) -> AnalysisTemplate | None:
        return self._templates.get(name)

    def list(self) -> list[str]:
        return list(self._templates.keys())

    def all(self) -> list[AnalysisTemplate]:
        return list(self._templates.values())

    def describe(self, name: str) -> str:
        t = self.get(name)
        return t.describe() if t else f"未找到模板: {name}"

    def search(self, method: str | None = None, tag: str | None = None) -> list[str]:
        """按方法或标签检索模板。"""
        result = []
        for t in self._templates.values():
            if method and method not in t.methods:
                continue
            if tag and tag not in t.tags:
                continue
            result.append(t.name)
        return result
