"""学术解读文本生成。

为每个统计结果附带 1 句标准化学术解读，直接可写入论文。
判断阈值绑定文献出处（与 ERK 内核一致，不臆造）：
  - Cronbach's α ≥ 0.70 可接受、≥ 0.80 良好（Nunnally, 1978）
  - KMO ≥ 0.60 可接受、≥ 0.80 良好（Kaiser, 1974）
  - Bartlett 球形检验 p < 0.05（Bartlett, 1954）
  - 因子载荷 |loading| ≥ 0.40 可接受（Hair et al., 2010）
"""

from __future__ import annotations


def interpret_alpha(alpha: float) -> str:
    if alpha >= 0.90:
        level = "极好"
    elif alpha >= 0.80:
        level = "良好"
    elif alpha >= 0.70:
        level = "可接受"
    else:
        level = "偏低"
    return (
        f"总量表克朗巴赫α系数为 {alpha:.3f}，"
        f"{'大于' if alpha >= 0.70 else '低于'} 0.7 的临界标准，"
        f"说明该量表信度{level}，内部一致性{'较高' if alpha >= 0.70 else '不足，建议检查反向题或删除拖累项'}。"
    )


def interpret_kmo_bartlett(kmo: float, bartlett_p: float) -> str:
    kmo_level = "良好" if kmo >= 0.80 else ("可接受" if kmo >= 0.60 else "偏低")
    kmo_ok = kmo >= 0.60
    bartlett_ok = bartlett_p < 0.05
    if kmo_ok and bartlett_ok:
        return (
            f"KMO 值为 {kmo:.3f}（{kmo_level}），且 Bartlett 球形检验显著"
            f"（p = {bartlett_p:.4f} < 0.05），表明变量间存在较强相关，适合进行因子分析。"
        )
    if not kmo_ok and not bartlett_ok:
        return (
            f"KMO 值为 {kmo:.3f}（{kmo_level}），且 Bartlett 球形检验不显著"
            f"（p = {bartlett_p:.4f}），表明样本可能不适合进行因子分析。"
        )
    if not kmo_ok:
        return (
            f"KMO 值为 {kmo:.3f}（{kmo_level}），低于 0.6 的可接受标准，"
            f"样本适合度欠佳，因子分析结果需谨慎解读。"
        )
    return (
        f"KMO 值为 {kmo:.3f}（{kmo_level}），但 Bartlett 球形检验不显著"
        f"（p = {bartlett_p:.4f}），相关矩阵可能接近单位阵，因子分析意义有限。"
    )


def interpret_factor(variance_total: float, n_factors: int) -> str:
    ok = variance_total >= 0.60
    return (
        f"探索性因子分析共提取 {n_factors} 个因子，累计方差解释率为 {variance_total:.1%}，"
        f"{'达到' if ok else '未达到'} 60% 的常用经验标准，"
        f"提取的因子对原始题项{'具有较好的解释力' if ok else '解释力有限，可考虑增减题项或调整因子数'}。"
    )


def interpret_coef(name: str, coef: float, p: float, direction_hint: str = "") -> str:
    """回归系数解读。direction_hint 为方向性描述（如"为正"），留空时自动判断。"""
    if p < 0.01:
        sig = "1%"
    elif p < 0.05:
        sig = "5%"
    elif p < 0.1:
        sig = "10%"
    else:
        sig = ""
    sign = "为正" if coef > 0 else "为负" if coef < 0 else "接近于零"
    if sig:
        core = f"{name}的回归系数为 {coef:.3f}，在 {sig} 统计水平上显著{sign}"
    else:
        core = f"{name}的回归系数为 {coef:.3f}，未通过显著性检验"
    hint = direction_hint or ""
    return f"核心解释变量{core}，{hint}" if not hint else f"{core}，{hint}"


def interpret_correlation(r: float, x: str, y: str) -> str:
    abs_r = abs(r)
    if abs_r >= 0.8:
        strength = "高度"
    elif abs_r >= 0.5:
        strength = "中等程度"
    elif abs_r >= 0.3:
        strength = "较弱"
    else:
        strength = "微弱"
    direction = "正" if r > 0 else "负" if r < 0 else "无"
    return f"{x}与{y}呈{strength}{direction}相关（r = {r:.3f}）。"
