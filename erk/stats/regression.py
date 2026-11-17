"""回归分析封装（内置引擎） + 统一结果契约。

设计边界（务必遵守，是全项目的原则落点）：
  - 内置引擎仅用于「开箱即用」的快速预览，以及无专业软件环境下的基础分析。
  - 进阶计量（DID/PSM/IV/RDD、以及严格的固定效应 + 聚类标准误）应由
    Stata/R 等专业软件计算，走 io/ 模块「生成脚本 → 静默运行 → 回读结果」。
  - 本模块不重复实现统计轮子。

RegressionResult 是「结果标准化」的统一中间结构：无论结果来自内置引擎
还是三大软件回读（io/EngineEstimate.to_regression_result），都归一为同一
结构，供 report/ 层统一渲染三线表。

契约设计（借鉴 StatsPAI）：统一提供 tidy() / glance() / to_dict(detail)，
让回归、t 检验、信效度等异构结果共享同一套输出口径。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import statsmodels.formula.api as smf

from erk.stats.results import to_jsonable

# tidy 长表的标准列（broom 风格）
TIDY_COLUMNS = [
    "term", "estimate", "std_error", "statistic", "p_value", "conf_low", "conf_high",
]


@dataclass
class RegressionResult:
    """一次回归的标准化结果。

    params / ses / pvalues / statistics / conf_low / conf_high 的 key 为自变量名；
    fe / cluster 用于在表格底部标注固定效应与聚类层级，保证可追溯、可复现。
    """

    dep: str
    params: dict
    ses: dict
    pvalues: dict
    nobs: int
    r2: float
    adj_r2: float
    model: str = "OLS"
    fe: list = field(default_factory=list)
    cluster: str = ""
    label: str = ""  # 表格列标题，如 "(1)" "(2)"
    statistics: dict = field(default_factory=dict)  # {var: t 统计量}
    conf_low: dict = field(default_factory=dict)    # {var: 95% 置信下限}
    conf_high: dict = field(default_factory=dict)   # {var: 95% 置信上限}

    # ---- 契约：terms / tidy / glance ----

    @property
    def terms(self) -> list[str]:
        """自变量的展示顺序。"""
        return list(self.params.keys())

    def tidy(self) -> pd.DataFrame:
        """broom 风格长表，供表格渲染统一消费。

        列：term / estimate / std_error / statistic / p_value / conf_low / conf_high。
        """
        rows = []
        for k in self.terms:
            rows.append(
                {
                    "term": k,
                    "estimate": self.params[k],
                    "std_error": self.ses[k],
                    "statistic": self.statistics.get(k),
                    "p_value": self.pvalues[k],
                    "conf_low": self.conf_low.get(k),
                    "conf_high": self.conf_high.get(k),
                }
            )
        return pd.DataFrame(rows, columns=TIDY_COLUMNS)

    def glance(self) -> pd.DataFrame:
        """模型级单行统计（nobs / r2 / adj_r2），供表格底部注记消费。"""
        return pd.DataFrame(
            [{"nobs": self.nobs, "r2": self.r2, "adj_r2": self.adj_r2}]
        )

    # ---- 契约：三档信封 ----

    def to_dict(self, detail: str = "standard") -> dict:
        """三档信封输出（minimal / standard / agent），JSON 安全。

        - minimal : 核心估计量与样本量，供 Agent 低 token 消费；
        - standard: 完整系数 + 拟合统计；
        - agent   : standard + 学术风险提示与后续动作建议。
        """
        coefs = {
            k: {
                "estimate": self.params[k],
                "se": self.ses[k],
                "p_value": self.pvalues[k],
                "conf_low": self.conf_low.get(k),
                "conf_high": self.conf_high.get(k),
            }
            for k in self.terms
        }
        if detail == "minimal":
            payload = {
                "method": self.model,
                "estimand": self.dep,
                "n_obs": self.nobs,
                "coefficients": coefs,
            }
        else:
            payload = {
                "method": self.model,
                "estimand": self.dep,
                "n_obs": self.nobs,
                "r2": self.r2,
                "adj_r2": self.adj_r2,
                "coefficients": coefs,
                "fixed_effects": self.fe,
                "cluster": self.cluster or None,
            }
            if detail == "agent":
                payload["warnings"] = self._warnings()
                payload["next_steps"] = self._next_steps()
        return to_jsonable(payload)

    # ---- agent 层：风险提示与后续建议 ----

    def _warnings(self) -> list[str]:
        """学术风险提示：把口径差异显式暴露给用户/Agent，不悄悄掩盖。"""
        warnings = []
        if self.fe:
            warnings.append(
                "固定效应以虚拟变量(dummy)实现，样本量大时效率低，"
                "自由度/标准误口径与 Stata reghdfe 可能不一致，建议用 Stata 复核。"
            )
        if self.cluster:
            warnings.append(
                "聚类标准误采用 statsmodels cluster 估计，与 Stata `vce(cluster)` "
                "在小样本校正口径上可能存在差异，正式结果建议用 Stata/R 复核。"
            )
        return warnings

    def _next_steps(self) -> list[str]:
        """后续动作建议（稳健性 / 异质性 / 机制）。"""
        return [
            "建议补充稳健性检验（替换变量、子样本、更换估计方法）。",
            "建议做异质性分析（分组回归）与机制检验（中介/调节）。",
            "正式论文请用 io/ 模块生成 Stata/R 脚本复核核心结果。",
        ]


def run_ols(
    df: pd.DataFrame,
    dep: str,
    indep: list[str],
    fe: list[str] | None = None,
    cluster: str | None = None,
    label: str = "",
) -> RegressionResult:
    """运行 OLS 回归（内置引擎），返回标准化结果。

    参数：
      df      : 样本数据
      dep     : 因变量
      indep   : 自变量列表
      fe      : 固定效应变量列表（以虚拟变量形式加入，见下方风险说明）
      cluster : 聚类变量（公司/个体 ID）
      label   : 表格列标题，如 "(1)"

    风险说明：
      - 固定效应以虚拟变量(dummy)实现，样本量大、虚拟变量多时效率较低，
        自由度/标准误口径与 Stata `reghdfe` 可能不完全一致；
      - 聚类标准误使用 statsmodels 的 cluster 协方差估计，与 Stata
        `vce(cluster)` 在小样本校正口径上可能存在差异。
      正式论文建议用 io/ 模块生成 Stata/R 脚本复核。
    """
    fe = fe or []
    rhs = list(indep) + [f"C({c})" for c in fe]
    formula = f"{dep} ~ {' + '.join(rhs)}"

    model = smf.ols(formula, data=df)
    if cluster:
        res = model.fit(cov_type="cluster", cov_kwds={"groups": df[cluster]})
    else:
        res = model.fit()

    # 三线表仅展示核心自变量系数；固定效应以 Yes/No 标注，不逐项列出 dummy 系数
    params = {k: float(res.params[k]) for k in indep}
    ses = {k: float(res.bse[k]) for k in indep}
    pvalues = {k: float(res.pvalues[k]) for k in indep}
    statistics = {k: float(res.tvalues[k]) for k in indep}

    conf = res.conf_int()
    conf_low = {k: float(conf.loc[k].iloc[0]) for k in indep}
    conf_high = {k: float(conf.loc[k].iloc[1]) for k in indep}

    return RegressionResult(
        dep=dep,
        params=params,
        ses=ses,
        pvalues=pvalues,
        nobs=int(res.nobs),
        r2=float(res.rsquared),
        adj_r2=float(res.rsquared_adj),
        model="OLS",
        fe=list(fe),
        cluster=cluster or "",
        label=label,
        statistics=statistics,
        conf_low=conf_low,
        conf_high=conf_high,
    )
