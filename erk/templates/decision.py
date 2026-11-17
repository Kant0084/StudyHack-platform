"""识别策略决策树（识别优先）。

借鉴 AERS 的 aer-identification：在估计之前先确定识别策略，
并为每类方法提供「现代默认值 + 必查诊断」清单。

原则：识别优先于估计——先回答「因果效应如何被识别」，
再选择估计方法（Angrist & Pischke, 2009, MHE）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 各方法的必查诊断清单（现代默认值，绑定出处）
METHOD_CHECKS: dict[str, list[str]] = {
    "did": [
        "平行趋势检验：事件研究图 + 联合 pre-trend 检验",
        "交错处理用 Callaway-Sant'Anna / Sun-Abraham（避免 TWFE 偏误）",
        "Goodman-Bacon 分解检验",
        "安慰剂检验（随机化处理时点/组别）",
    ],
    "iv": [
        "一阶段 F 统计量（弱工具检验，Olea-Pflueger 有效 F）",
        "排除性限制论证 + 安慰剂检验",
        "过度识别检验（Sargan/Hansen J）",
        "工具变量外生性论证",
    ],
    "rdd": [
        "McCrary 密度检验（断点处操纵检验）",
        "局部线性回归 + 三角核，MSE 最优带宽",
        "安慰剂断点检验",
        "带宽敏感性分析",
    ],
    "psm": [
        "平衡性检验（匹配后标准化偏差 < 10%）",
        "共同支撑域检验",
        "匹配质量与稳健性（不同匹配算法）",
        "倾向得分重叠检验",
    ],
    "fe": [
        "Hausman 检验（FE vs RE）",
        "聚类标准误层级（个体/时间）",
        "序列相关检验",
        "组内变异是否充分",
    ],
}

# 方法出处
METHOD_REFERENCES: dict[str, list[str]] = {
    "did": ["Callaway & Sant'Anna (2021)", "Sun & Abraham (2021)", "Goodman-Bacon (2021)"],
    "iv": ["Angrist & Pischke (2009)", "Olea & Pflueger (2013)", "Stock & Yogo (2005)"],
    "rdd": ["Cattaneo, Idrobo & Titiunik (2019)", "McCrary (2008)"],
    "psm": ["Rosenbaum & Rubin (1983)", "Caliendo & Kopeinig (2008)"],
    "fe": ["Wooldridge (2010)", "Angrist & Pischke (2009)"],
}


@dataclass
class MethodRecommendation:
    """方法推荐结果。"""

    name: str
    reason: str
    checks: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "reason": self.reason,
            "checks": self.checks,
            "references": self.references,
        }


def recommend_method(
    has_panel: bool = False,
    has_time: bool = False,
    has_treatment: bool = False,
    has_instrument: bool = False,
    has_cutoff: bool = False,
) -> list[MethodRecommendation]:
    """根据研究场景特征推荐识别策略（按优先级排序）。

    参数（研究场景的关键特征）：
      has_panel      是否有面板数据（个体 × 时间）
      has_time       是否有政策/冲击前后时间维度
      has_treatment  是否有处理组与对照组
      has_instrument 是否有工具变量
      has_cutoff     处理是否由断点/阈值规则决定

    返回推荐方法列表（首项为最优先）。
    """
    results: list[MethodRecommendation] = []

    if has_cutoff:
        results.append(
            MethodRecommendation(
                "rdd",
                "处理由断点/阈值规则决定，可做断点回归识别局部处理效应。",
                METHOD_CHECKS["rdd"],
                METHOD_REFERENCES["rdd"],
            )
        )

    if has_instrument:
        results.append(
            MethodRecommendation(
                "iv",
                "存在工具变量，可用 2SLS 处理遗漏变量/双向因果导致的内生性。",
                METHOD_CHECKS["iv"],
                METHOD_REFERENCES["iv"],
            )
        )

    if has_treatment and has_time:
        results.append(
            MethodRecommendation(
                "did",
                "有处理组/对照组且存在政策前后，可用 DID 识别政策处理效应。",
                METHOD_CHECKS["did"],
                METHOD_REFERENCES["did"],
            )
        )

    if has_panel:
        results.append(
            MethodRecommendation(
                "fe",
                "有面板数据，可用固定效应吸收不随时间变化的个体异质性。",
                METHOD_CHECKS["fe"],
                METHOD_REFERENCES["fe"],
            )
        )

    if not results:
        results.append(
            MethodRecommendation(
                "psm",
                "无断点/工具/时间维，若可观测变量能解释选择，可用 PSM 匹配。",
                METHOD_CHECKS["psm"],
                METHOD_REFERENCES["psm"],
            )
        )

    return results


def method_checks(method: str) -> list[str]:
    """返回某方法的必查诊断清单。"""
    return METHOD_CHECKS.get(method, [])
