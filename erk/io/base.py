"""软件对接层抽象。

借鉴 StatsPAI 的 EngineAdapter 设计，是「专业计算交给专业软件」原则的落点：

  - EngineAdapter.run() 永不抛异常：软件未安装 / 不支持 / 运行错误都归一为
    EngineEstimate(status=...)，绝不让上游崩溃，缺失即降级而非失败。
  - EngineEstimate.to_regression_result() 把三方回读结果归一为统一的
    RegressionResult，供 report 层渲染三线表。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd

# 状态枚举语义
STATUS_OK = "ok"
STATUS_SKIPPED = "skipped"           # 被跳过（如方法不受支持）
STATUS_UNAVAILABLE = "unavailable"   # 软件未安装/未配置
STATUS_ERROR = "error"               # 运行时错误


@dataclass
class EngineEstimate:
    """一次外部引擎回读的标准化结果。

    status 语义见上方常量；coef/se/pvalue 的 key 为自变量名。
    """

    engine: str
    status: str
    dep: str = ""
    coef: dict = field(default_factory=dict)
    se: dict = field(default_factory=dict)
    pvalue: dict = field(default_factory=dict)
    nobs: int | None = None
    r2: float | None = None
    adj_r2: float | None = None
    message: str = ""  # unavailable / error 时的说明

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_regression_result(
        self,
        model: str = "OLS",
        fe: list[str] | None = None,
        cluster: str = "",
        label: str = "",
    ) -> RegressionResult:
        """归一为统一的 RegressionResult，供 report 层渲染。

        注意：外部引擎回读时若未提供置信区间，则用 coef ± 1.96·se 近似
        （仅作展示，正式区间应以引擎输出为准，见 Stata 脚本的全精度输出）。
        """
        # 延迟导入，避免 io.base ↔ stats.regression 的循环依赖
        from erk.stats.regression import RegressionResult

        terms = list(self.coef.keys())
        statistics = {k: (self.coef[k] / self.se[k]) if self.se.get(k) else None for k in terms}
        conf_low = {k: self.coef[k] - 1.96 * self.se[k] for k in terms if self.se.get(k)}
        conf_high = {k: self.coef[k] + 1.96 * self.se[k] for k in terms if self.se.get(k)}

        return RegressionResult(
            dep=self.dep,
            params=self.coef,
            ses=self.se,
            pvalues=self.pvalue,
            nobs=self.nobs or 0,
            r2=self.r2 or 0.0,
            adj_r2=self.adj_r2 or 0.0,
            model=model,
            fe=fe or [],
            cluster=cluster,
            label=label,
            statistics=statistics,
            conf_low=conf_low,
            conf_high=conf_high,
        )


class EngineAdapter(ABC):
    """外部统计软件适配器的统一契约。

    子类实现 available() 与 _run_impl()；run() 统一兜底异常，永不抛出。
    """

    engine_name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """探测目标软件是否可用（已安装且可执行）。"""

    def run(
        self,
        df: pd.DataFrame,
        dep: str,
        indep: list[str],
        fe: list[str] | None = None,
        cluster: str | None = None,
        workdir: str | None = None,
    ) -> EngineEstimate:
        """执行回归并回读结果，永不抛异常。

        软件未安装 → status=unavailable；运行错误 → status=error。
        """
        if not self.available():
            return EngineEstimate(
                engine=self.engine_name,
                status=STATUS_UNAVAILABLE,
                message=f"{self.engine_name} 未安装或未配置，已跳过外部计算。",
            )
        try:
            return self._run_impl(df, dep, indep, fe=fe, cluster=cluster, workdir=workdir)
        except Exception as exc:  # noqa: BLE001 —— 归一为 error，不向上抛
            return EngineEstimate(
                engine=self.engine_name,
                status=STATUS_ERROR,
                message=f"{self.engine_name} 执行失败: {exc}",
            )

    @abstractmethod
    def _run_impl(
        self,
        df: pd.DataFrame,
        dep: str,
        indep: list[str],
        fe: list[str] | None,
        cluster: str | None,
        workdir: str | None,
    ) -> EngineEstimate:
        """子类实现：真正的执行 + 回读逻辑。"""
