"""PSM 倾向得分匹配（内置引擎预览）。

核心流程（Rosenbaum & Rubin, 1983）：
  1. 倾向得分：logistic 回归估计 P(treat=1 | X)
  2. 最近邻匹配：基于倾向得分做最近邻匹配（默认有放回，见 _nearest_neighbor_match）
  3. 平衡性检验：匹配前后协变量标准化偏差（|SMD| < 10% 为平衡）
  4. ATT：匹配后处理组与对照组的均值差

风险说明（诚实标注，不悄悄掩盖）：
  - 本实现用于「开箱即用」的快速预览；ATT 标准误采用简单合并方差估计，
    未使用 Abadie-Imbens 稳健标准误，正式结果建议用 Stata `teffects psmatch`
    或 R `MatchIt` 复核。
  - 最近邻匹配对倾向得分重叠（共同支撑域）敏感，倾向得分极端值会影响匹配质量。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

# 平衡性阈值（Rosenbaum & Rubin 建议标准化偏差 < 10%）
SMD_THRESHOLD = 0.10


def _logit_ps(df: pd.DataFrame, treat: str, covariates: list[str]) -> tuple[np.ndarray, float]:
    """估计倾向得分，返回 (pscore, pseudo_r2)。"""
    X = sm.add_constant(df[covariates].astype(float))
    y = df[treat].astype(int)
    model = sm.Logit(y, X).fit(disp=0)
    pscore = model.predict(X)
    return pscore.to_numpy(), float(model.prsquared)


def _nearest_neighbor_match(
    ps_treated: np.ndarray,
    ps_control: np.ndarray,
    caliper: float | None = None,
    with_replacement: bool = True,
):
    """最近邻匹配，返回 (匹配到的对照组索引, 距离)。

    with_replacement=True（默认）：允许对照个体重复使用，样本不平衡时更稳健；
    with_replacement=False：1:1 无放回匹配。
    caliper：卡尺（倾向得分最大距离），超出的不匹配（索引记为 -1）。
    """
    matched: list[int] = []
    dists: list[float] = []
    available = list(range(len(ps_control)))

    for t in ps_treated:
        if with_replacement:
            if len(ps_control) == 0:
                matched.append(-1)
                dists.append(float("nan"))
                continue
            best = int(np.argmin(np.abs(ps_control - t)))
        else:
            if not available:
                matched.append(-1)
                dists.append(float("nan"))
                continue
            best = min(available, key=lambda ci: abs(ps_control[ci] - t))

        d = abs(t - ps_control[best])
        if caliper is not None and d > caliper:
            matched.append(-1)
            dists.append(float("nan"))
            continue
        matched.append(best)
        dists.append(d)
        if not with_replacement:
            available.remove(best)

    return matched, dists


def _smd(a: np.ndarray, b: np.ndarray) -> float:
    """标准化均值差（standardized mean difference）。"""
    var_a, var_b = a.var(ddof=1), b.var(ddof=1)
    pooled = np.sqrt((var_a + var_b) / 2)
    if pooled == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled)


@dataclass
class PsmResult:
    """PSM 匹配结果。"""

    method: str = "psm"
    att: float = float("nan")
    att_se: float = float("nan")
    t_stat: float = float("nan")
    p_value: float = float("nan")
    n_treated: int = 0
    n_control: int = 0
    n_matched: int = 0
    ps_pseudo_r2: float = float("nan")
    balance_before: dict = field(default_factory=dict)
    balance_after: dict = field(default_factory=dict)

    @property
    def balanced(self) -> bool:
        """匹配后所有协变量 |SMD| < 阈值。"""
        if not self.balance_after:
            return False
        return all(abs(v) < SMD_THRESHOLD for v in self.balance_after.values())

    @property
    def significant(self) -> bool:
        return not np.isnan(self.p_value) and self.p_value < 0.05

    def to_dict(self, detail: str = "standard") -> dict:
        payload = {
            "method": self.method,
            "att": self.att,
            "att_se": self.att_se,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
            "n_treated": self.n_treated,
            "n_control": self.n_control,
            "n_matched": self.n_matched,
            "ps_pseudo_r2": self.ps_pseudo_r2,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "balanced": self.balanced,
        }
        if detail == "agent":
            payload["warnings"] = self._warnings()
            payload["thresholds"] = {"smd": f"< {SMD_THRESHOLD} (Rosenbaum & Rubin, 1983)"}
        return payload

    def _warnings(self) -> list[str]:
        warnings = []
        if not self.balanced:
            worst = max(self.balance_after.items(), key=lambda kv: abs(kv[1]))
            warnings.append(
                f"匹配后协变量「{worst[0]}」标准化偏差 = {worst[1]:.3f}（≥ {SMD_THRESHOLD}），"
                "平衡性不足，建议调整匹配算法或协变量。"
            )
        if self.n_matched < self.n_treated:
            warnings.append(
                f"仅匹配 {self.n_matched}/{self.n_treated} 个处理个体，"
                "存在共同支撑域问题（部分处理个体无相近对照）。"
            )
        warnings.append(
            "ATT 标准误为简单合并方差估计，未用 Abadie-Imbens 稳健标准误；"
            "正式结果建议用 Stata teffects psmatch 或 R MatchIt 复核。"
        )
        return warnings


def run_psm(
    df: pd.DataFrame,
    dep: str,
    treat: str,
    covariates: list[str],
    caliper: float | None = None,
) -> PsmResult:
    """PSM 倾向得分匹配 + ATT 估计。

    返回 PsmResult；ATT = 匹配后处理组与对照组因变量均值差。
    """
    df = df.copy()
    # 编码 treat 为 0/1：确定性字典序编码（较小类别为对照组 0），
    # 消除「首次出现顺序」导致处理组误判的风险；非二值则明确报错。
    if not pd.api.types.is_numeric_dtype(df[treat]):
        cats = sorted({str(x) for x in df[treat].dropna()})
        if len(cats) != 2:
            raise ValueError(
                f"变量 {treat} 有 {len(cats)} 个类别 {cats}，倾向得分匹配仅支持二值处理变量；"
                "请先把处理组显式编码为 0/1。"
            )
        mapping = {cats[0]: 0, cats[1]: 1}
        df[treat] = df[treat].astype(str).map(mapping).astype(int)

    # 1. 倾向得分
    pscore, pseudo_r2 = _logit_ps(df, treat, covariates)

    # 2. 分组
    treated_mask = df[treat] == 1
    ps_treated = pscore[treated_mask.to_numpy()]
    ps_control = pscore[~treated_mask.to_numpy()]
    y_treated = df.loc[treated_mask, dep].to_numpy(float)
    y_control_all = df.loc[~treated_mask, dep].to_numpy(float)
    X_treated = df.loc[treated_mask, covariates].astype(float)
    X_control_all = df.loc[~treated_mask, covariates].astype(float)

    # 3. 匹配（成功配对：matched_idx[i] >= 0 的处理个体 i 与对应对照组）
    matched_idx, _ = _nearest_neighbor_match(ps_treated, ps_control, caliper=caliper)
    treated_matched = [i for i, m in enumerate(matched_idx) if m >= 0]
    control_matched = [m for m in matched_idx if m >= 0]
    n_matched = len(treated_matched)

    if n_matched == 0:
        return PsmResult(
            att=float("nan"), n_treated=len(y_treated), n_control=len(y_control_all), n_matched=0,
            ps_pseudo_r2=pseudo_r2,
        )

    y_treated_m = y_treated[treated_matched]
    y_control_m = y_control_all[control_matched]
    X_treated_m = X_treated.iloc[treated_matched]
    X_control_m = X_control_all.iloc[control_matched]

    # 4. ATT（仅用匹配成功的配对）
    att = float(y_treated_m.mean() - y_control_m.mean())
    var_t, var_c = y_treated_m.var(ddof=1), y_control_m.var(ddof=1)
    se = float(np.sqrt(var_t / len(y_treated_m) + var_c / len(y_control_m)))
    t_stat = att / se if se > 0 else float("nan")
    p_value = float(2 * stats.norm.sf(abs(t_stat))) if not np.isnan(t_stat) else float("nan")

    # 5. 平衡性检验（匹配前后均用成功配对的处理组）
    balance_before = {c: _smd(X_treated[c].to_numpy(), X_control_all[c].to_numpy()) for c in covariates}
    balance_after = {c: _smd(X_treated_m[c].to_numpy(), X_control_m[c].to_numpy()) for c in covariates}

    return PsmResult(
        att=att,
        att_se=se,
        t_stat=t_stat,
        p_value=p_value,
        n_treated=len(y_treated),
        n_control=len(y_control_all),
        n_matched=n_matched,
        ps_pseudo_r2=pseudo_r2,
        balance_before={k: round(v, 4) for k, v in balance_before.items()},
        balance_after={k: round(v, 4) for k, v in balance_after.items()},
    )
