"""问卷信度与效度检验（内置引擎）。

这是 ERK 问卷引擎的核心增量：参考项目（wjx-ai-kit 等）均无信效度实现，
本模块用 numpy/scipy 自研，严格遵循经典公式。

阈值判断绑定文献出处（不臆造）：
  - Cronbach's α ≥ 0.70 可接受、≥ 0.80 良好（Nunnally, 1978）
  - KMO ≥ 0.60 可接受、≥ 0.80 良好（Kaiser, 1974）
  - Bartlett 球形检验 p < 0.05（Bartlett, 1954）

注意：所有计算默认 listwise deletion（仅保留完整作答样本）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats

# 阈值（绑定文献）
ALPHA_ACCEPTABLE = 0.70
ALPHA_GOOD = 0.80
KMO_ACCEPTABLE = 0.60
KMO_GOOD = 0.80
BARTLETT_SIG = 0.05


def cronbach_alpha(items: np.ndarray) -> float:
    """Cronbach's α 系数。

    公式：α = (k/(k-1)) * (1 - Σσ²_i / σ²_total)
    其中 k 为题项数，σ²_i 为第 i 题方差，σ²_total 为总分方差。

    items：n_samples × n_items 数值矩阵（应已做 listwise 处理）。
    """
    items = np.asarray(items, dtype=float)
    k = items.shape[1]
    if k < 2:
        return float("nan")
    item_vars = items.var(axis=0, ddof=1)
    total_var = items.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return float("nan")
    return (k / (k - 1)) * (1 - item_vars.sum() / total_var)


def item_total_correlations(items: np.ndarray) -> np.ndarray:
    """修正的项总计相关（corrected item-total correlation）。

    每项与其「其余项之和」的皮尔逊相关。
    """
    items = np.asarray(items, dtype=float)
    k = items.shape[1]
    corrs = np.zeros(k)
    for i in range(k):
        others = items[:, [j for j in range(k) if j != i]].sum(axis=1)
        if np.std(others) == 0 or np.std(items[:, i]) == 0:
            corrs[i] = float("nan")
        else:
            corrs[i] = np.corrcoef(items[:, i], others)[0, 1]
    return corrs


def alpha_if_deleted(items: np.ndarray) -> np.ndarray:
    """删除某项后的 Cronbach's α（用于识别拖累信度的题项）。"""
    items = np.asarray(items, dtype=float)
    k = items.shape[1]
    result = np.zeros(k)
    for i in range(k):
        result[i] = cronbach_alpha(np.delete(items, i, axis=1))
    return result


def kmo_from_corr(corr: np.ndarray) -> tuple[float, np.ndarray]:
    """KMO 抽样充分性度量。

    公式：KMO = ΣΣ r²_ij / (ΣΣ r²_ij + ΣΣ p²_ij)
    其中 r 为相关系数，p 为偏相关系数（由相关矩阵的逆推得）。

    返回 (总体 KMO, 每个变量的 KMO)。
    """
    corr = np.asarray(corr, dtype=float)
    p = corr.shape[0]
    try:
        inv = np.linalg.inv(corr)
    except np.linalg.LinAlgError:
        return float("nan"), np.full(p, float("nan"))

    # 偏相关矩阵（对角线置 0）
    d = np.diag(inv)
    partial = -inv / np.sqrt(np.outer(d, d))
    np.fill_diagonal(partial, 0.0)

    # 每个变量的 KMO
    kmo_per = np.zeros(p)
    for j in range(p):
        num = float((corr[j, :] ** 2).sum() - corr[j, j] ** 2)
        den = num + float((partial[j, :] ** 2).sum())
        kmo_per[j] = num / den if den > 0 else float("nan")

    # 总体 KMO（排除对角线）
    r2_sum = float((corr ** 2).sum() - np.trace(corr ** 2))
    p2_sum = float((partial ** 2).sum())
    overall = r2_sum / (r2_sum + p2_sum) if (r2_sum + p2_sum) > 0 else float("nan")
    return overall, kmo_per


def bartlett_sphericity(corr: np.ndarray, n: int) -> tuple[float, int, float]:
    """Bartlett 球形检验。

    公式：χ² = -(n - 1 - (2p+5)/6) · ln(det(R))，df = p(p-1)/2。

    返回 (χ², df, p 值)。
    """
    corr = np.asarray(corr, dtype=float)
    p = corr.shape[0]
    df = p * (p - 1) // 2
    det = np.linalg.det(corr)
    if det <= 0:
        return float("nan"), df, float("nan")
    chi2 = -(n - 1 - (2 * p + 5) / 6) * np.log(det)
    pval = float(1 - stats.chi2.cdf(chi2, df))
    return float(chi2), df, pval


@dataclass
class ReliabilityResult:
    """量表信效度标准化结果（实现 to_dict 契约，供报告层消费）。"""

    method: str = "reliability"
    n_items: int = 0
    n_samples: int = 0
    alpha: float = float("nan")
    item_total: list = field(default_factory=list)
    alpha_if_deleted: list = field(default_factory=list)
    kmo: float = float("nan")
    kmo_per_item: list = field(default_factory=list)
    bartlett_chi2: float = float("nan")
    bartlett_df: int = 0
    bartlett_p: float = float("nan")
    item_labels: list = field(default_factory=list)

    @property
    def alpha_ok(self) -> bool:
        return not np.isnan(self.alpha) and self.alpha >= ALPHA_ACCEPTABLE

    @property
    def alpha_good(self) -> bool:
        return not np.isnan(self.alpha) and self.alpha >= ALPHA_GOOD

    @property
    def kmo_ok(self) -> bool:
        return not np.isnan(self.kmo) and self.kmo >= KMO_ACCEPTABLE

    @property
    def bartlett_ok(self) -> bool:
        return not np.isnan(self.bartlett_p) and self.bartlett_p < BARTLETT_SIG

    def to_dict(self, detail: str = "standard") -> dict:
        """标准化输出（standard / agent）。"""
        payload = {
            "method": self.method,
            "n_items": self.n_items,
            "n_samples": self.n_samples,
            "alpha": self.alpha,
            "alpha_acceptable": self.alpha_ok,
            "alpha_good": self.alpha_good,
            "item_total": self.item_total,
            "alpha_if_deleted": self.alpha_if_deleted,
            "kmo": self.kmo,
            "kmo_acceptable": self.kmo_ok,
            "bartlett_chi2": self.bartlett_chi2,
            "bartlett_df": self.bartlett_df,
            "bartlett_p": self.bartlett_p,
            "bartlett_sig": self.bartlett_ok,
        }
        if detail == "agent":
            payload["warnings"] = self._warnings()
            payload["thresholds"] = {
                "alpha": f">={ALPHA_ACCEPTABLE} (Nunnally, 1978)",
                "kmo": f">={KMO_ACCEPTABLE} (Kaiser, 1974)",
                "bartlett": f"p<{BARTLETT_SIG} (Bartlett, 1954)",
            }
        return payload

    def _warnings(self) -> list[str]:
        warnings = []
        if not self.alpha_ok:
            warnings.append(
                f"Cronbach's α = {self.alpha:.3f}，低于可接受阈值 {ALPHA_ACCEPTABLE}，"
                "量表内部一致性不足，建议检查反向题或删除拖累项（见 alpha_if_deleted）。"
            )
        if not self.kmo_ok:
            warnings.append(
                f"KMO = {self.kmo:.3f}，低于 {KMO_ACCEPTABLE}，样本可能不适合因子分析。"
            )
        if not self.bartlett_ok:
            warnings.append("Bartlett 检验不显著，相关矩阵可能接近单位阵，因子分析意义有限。")
        # 项总计相关过低提示
        for i, r in enumerate(self.item_total):
            if not np.isnan(r) and abs(r) < 0.30:
                label = self.item_labels[i] if i < len(self.item_labels) else f"item_{i}"
                warnings.append(f"题项「{label}」项总计相关 = {r:.3f}（< 0.30），可能需删除。")
        return warnings


def run_reliability(items: np.ndarray, item_labels: list[str] | None = None) -> ReliabilityResult:
    """一键计算量表信效度（listwise 处理缺失）。

    items：n_samples × n_items 数值矩阵（Likert 得分）。
    """
    items = np.asarray(items, dtype=float)
    # listwise deletion
    items = items[~np.isnan(items).any(axis=1)]
    n_samples, n_items = items.shape

    if n_items < 2 or n_samples < 3:
        return ReliabilityResult(n_items=n_items, n_samples=n_samples, item_labels=item_labels or [])

    corr = np.corrcoef(items, rowvar=False)
    overall_kmo, kmo_per = kmo_from_corr(corr)
    chi2, df, pval = bartlett_sphericity(corr, n_samples)

    return ReliabilityResult(
        n_items=n_items,
        n_samples=n_samples,
        alpha=cronbach_alpha(items),
        item_total=[round(float(x), 4) for x in item_total_correlations(items)],
        alpha_if_deleted=[round(float(x), 4) for x in alpha_if_deleted(items)],
        kmo=float(overall_kmo),
        kmo_per_item=[round(float(x), 4) for x in kmo_per],
        bartlett_chi2=float(chi2),
        bartlett_df=df,
        bartlett_p=float(pval),
        item_labels=item_labels or [f"item_{i}" for i in range(n_items)],
    )
