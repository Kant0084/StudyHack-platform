"""探索性因子分析（EFA）。

实现主成分法因子提取 + varimax 正交旋转（经典 Kaiser 算法），
补全效度检验中「因子提取」这一环（KMO/Bartlett 是前置检验，见 reliability.py）。

阈值绑定文献（不臆造）：
  - 因子数：Kaiser 准则（特征值 > 1）
  - 载荷显著：|loading| ≥ 0.40 可接受、≥ 0.50 良好（Hair et al., 2010）
  - 累积方差解释率 ≥ 60% 常见经验标准

风险说明：
  - 主成分法（PCA-based EFA）是最基础的提取法；主因子法、最大似然法更严谨，
    但需要迭代，后续可扩展（或接入 R psych/lavaan 复核）。
  - 因子数自动判定（Kaiser 准则）可能高估，正式研究建议结合平行分析/碎石图。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from erk.survey.reliability import bartlett_sphericity, kmo_from_corr

LOADING_ACCEPTABLE = 0.40
LOADING_GOOD = 0.50
CUMULATIVE_TARGET = 0.60


def eigenvalues(corr: np.ndarray) -> np.ndarray:
    """相关矩阵的特征值（降序）。"""
    vals = np.linalg.eigvalsh(corr)
    return np.sort(vals)[::-1]


def varimax_rotation(loadings: np.ndarray, max_iter: int = 1000, tol: float = 1e-9) -> np.ndarray:
    """Varimax 正交旋转（Kaiser 归一化 + pairwise 平面旋转，Kaiser 1958）。"""
    A = loadings.copy()
    p, k = A.shape
    if k < 2:
        return A

    # Kaiser 归一化：每行除以共同度平方根，旋转后再还原（避免量纲导致的数值问题）
    h = np.sqrt((A**2).sum(axis=1))
    h[h < 1e-12] = 1.0
    U = A / h[:, None]

    for _ in range(max_iter):
        max_change = 0.0
        for i in range(k):
            for j in range(i + 1, k):
                x = U[:, i].copy()
                y = U[:, j].copy()
                u = x**2 - y**2
                v = 2 * x * y
                a = u.sum()
                b = v.sum()
                c = (u**2 - v**2).sum()
                d = 2 * (u * v).sum()
                num = d - 2 * a * b / p
                den = c - (a**2 - b**2) / p
                phi = 0.25 * np.arctan2(num, den)
                cos_p, sin_p = np.cos(phi), np.sin(phi)
                U[:, i] = cos_p * x + sin_p * y
                U[:, j] = -sin_p * x + cos_p * y
                max_change = max(max_change, abs(phi))
        if max_change < tol:
            break

    # 反归一化
    return U * h[:, None]


def _kaiser_n_factors(eigvals: np.ndarray) -> int:
    """Kaiser 准则：特征值 > 1 的因子数（至少 1）。"""
    n = int((eigvals > 1.0).sum())
    return max(n, 1)


@dataclass
class FactorResult:
    """EFA 标准化结果。"""

    method: str = "efa"
    n_items: int = 0
    n_samples: int = 0
    n_factors: int = 0
    eigenvalues: list = field(default_factory=list)       # 全部特征值
    loadings: list = field(default_factory=list)          # n_items × n_factors
    variance_explained: list = field(default_factory=list)  # 每因子方差解释率
    cumulative_variance: list = field(default_factory=list)  # 累积解释率
    communalities: list = field(default_factory=list)     # 共同度
    item_labels: list = field(default_factory=list)
    kmo: float = float("nan")
    bartlett_p: float = float("nan")

    @property
    def total_variance_explained(self) -> float:
        return float(self.cumulative_variance[-1]) if self.cumulative_variance else float("nan")

    @property
    def variance_ok(self) -> bool:
        return not np.isnan(self.total_variance_explained) and self.total_variance_explained >= CUMULATIVE_TARGET

    def loading_matrix(self) -> "np.ndarray":
        return np.asarray(self.loadings)

    def to_dict(self, detail: str = "standard") -> dict:
        payload = {
            "method": self.method,
            "n_items": self.n_items,
            "n_samples": self.n_samples,
            "n_factors": self.n_factors,
            "eigenvalues": self.eigenvalues,
            "loadings": self.loadings,
            "variance_explained": self.variance_explained,
            "cumulative_variance": self.cumulative_variance,
            "total_variance_explained": self.total_variance_explained,
            "communalities": self.communalities,
            "kmo": self.kmo,
            "bartlett_p": self.bartlett_p,
        }
        if detail == "agent":
            payload["warnings"] = self._warnings()
            payload["thresholds"] = {
                "loading": f">={LOADING_ACCEPTABLE} (Hair et al., 2010)",
                "cumulative_variance": f">={CUMULATIVE_TARGET}",
            }
        return payload

    def _warnings(self) -> list[str]:
        warnings = []
        if not self.variance_ok:
            warnings.append(
                f"累积方差解释率 = {self.total_variance_explained:.1%}，低于 {CUMULATIVE_TARGET:.0%}，"
                "提取的因子解释力有限。"
            )
        # 低共同度提示
        for i, h in enumerate(self.communalities):
            if h < 0.30:
                label = self.item_labels[i] if i < len(self.item_labels) else f"item_{i}"
                warnings.append(f"题项「{label}」共同度 = {h:.3f}（< 0.30），可能需删除。")
        # 载荷不清晰提示（某题项在所有因子上载荷都低）
        L = np.asarray(self.loadings)
        for i in range(self.n_items):
            if L[i, :].size and np.abs(L[i, :]).max() < LOADING_ACCEPTABLE:
                label = self.item_labels[i] if i < len(self.item_labels) else f"item_{i}"
                warnings.append(
                    f"题项「{label}」在所有因子上的载荷均 < {LOADING_ACCEPTABLE}，归属不清晰。"
                )
        return warnings


def factor_analysis(
    items: np.ndarray,
    n_factors: int | None = None,
    rotation: str = "varimax",
    item_labels: list[str] | None = None,
) -> FactorResult:
    """主成分法探索性因子分析。

    items：n_samples × n_items 数值矩阵（listwise 处理缺失）。
    n_factors：因子数；None 时用 Kaiser 准则（特征值 > 1）。
    rotation：目前支持 "varimax" 或 "none"。
    """
    items = np.asarray(items, dtype=float)
    items = items[~np.isnan(items).any(axis=1)]
    n_samples, n_items = items.shape

    if n_items < 2 or n_samples < 5:
        return FactorResult(
            n_items=n_items, n_samples=n_samples,
            item_labels=item_labels or [f"item_{i}" for i in range(n_items)],
        )

    corr = np.corrcoef(items, rowvar=False)
    # 注意：np.linalg.eigh 返回升序特征值，须与特征向量一并降序对齐
    eigvals_raw, eigvecs = np.linalg.eigh(corr)
    order = np.argsort(eigvals_raw)[::-1]
    eigvals = eigvals_raw[order]
    eigvecs = eigvecs[:, order]

    if n_factors is None:
        n_factors = _kaiser_n_factors(eigvals)
    n_factors = min(n_factors, n_items)

    # 未旋转载荷 = 特征向量 × sqrt(特征值)
    loadings = eigvecs[:, :n_factors] * np.sqrt(eigvals[:n_factors])

    if rotation == "varimax":
        loadings = varimax_rotation(loadings)

    variance_explained = eigvals[:n_factors] / eigvals.sum()
    cumulative = np.cumsum(variance_explained)
    communalities = (loadings**2).sum(axis=1)

    overall_kmo, _ = kmo_from_corr(corr)
    _, _, bartlett_p = bartlett_sphericity(corr, n_samples)

    return FactorResult(
        n_items=n_items,
        n_samples=n_samples,
        n_factors=int(n_factors),
        eigenvalues=[round(float(x), 4) for x in eigvals],
        loadings=[[round(float(x), 4) for x in row] for row in loadings],
        variance_explained=[round(float(x), 4) for x in variance_explained],
        cumulative_variance=[round(float(x), 4) for x in cumulative],
        communalities=[round(float(x), 4) for x in communalities],
        item_labels=item_labels or [f"item_{i}" for i in range(n_items)],
        kmo=float(overall_kmo),
        bartlett_p=float(bartlett_p),
    )
