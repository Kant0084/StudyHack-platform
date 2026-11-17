"""学术写作辅助：学术化润色、论文模板、表格/公式转 LaTeX。"""

from __future__ import annotations

# ---- 学术化润色：口语 → 学术替换表 ----

_POLISH_RULES = [
    ("我觉得", "本文认为"),
    ("我认为", "笔者认为"),
    ("我们觉得", "本文认为"),
    ("大概", "约"),
    ("差不多", "接近"),
    ("很多", "大量"),
    ("非常多", "数量众多"),
    ("特别多", "显著"),
    ("很少", "较少"),
    ("越来越大", "呈上升趋势"),
    ("越来越小", "呈下降趋势"),
    ("越来越好", "持续改善"),
    ("变多", "增加"),
    ("变少", "减少"),
    ("变大", "增大"),
    ("变小", "减小"),
    ("证明了", "验证了"),
    ("说明了", "表明"),
    ("证明了这一点", "为此提供了实证支持"),
    ("很重要", "具有重要意义"),
    ("非常重要", "具有重要理论与实践意义"),
    ("人们", "现有研究"),
    ("大家", "学界"),
    ("弄明白", "厘清"),
    ("搞清楚", "厘清"),
    ("查一下", "检验"),
    ("看了看", "考察"),
    ("做了个调查", "开展了一项问卷调查"),
    ("结果发现", "实证结果表明"),
    ("总的来说", "综上"),
    ("也就是说", "换言之"),
    ("换句话说", "即"),
    ("这样的话", "由此"),
    ("因为", "由于"),
    ("所以", "因此"),
    ("但是", "然而"),
    ("而且", "此外"),
    ("还有", "同时"),
    ("东西", "因素"),
    ("事情", "问题"),
    ("有点", "一定程度上"),
    ("挺", "较为"),
    ("很", "较为"),
]


def polish_text(text: str) -> tuple[str, list[str]]:
    """学术化润色。返回 (润色后文本, 替换记录列表)。"""
    out = text
    changes = []
    for k, v in _POLISH_RULES:
        if k in out:
            out = out.replace(k, v)
            changes.append(f"「{k}」→「{v}」")
    return out, changes


# ---- 论文写作模板 ----

TEMPLATES = {
    "摘要": (
        "【摘要】\n"
        "本文以〔研究对象/问题〕为切入点，基于〔理论/方法〕，利用〔数据来源与样本〕，"
        "系统考察了〔核心变量之间的关系〕。研究发现：〔结论1〕；〔结论2〕。"
        "据此，本文提出〔对策建议〕。研究结论对〔理论/实践意义〕具有一定参考价值。\n"
        "【关键词】〔关键词1〕；〔关键词2〕；〔关键词3〕；〔关键词4〕"
    ),
    "研究设计": (
        "【研究设计】\n"
        "一、数据来源与样本\n本文数据来源于〔数据来源〕，样本期间为〔起始年份〕—〔结束年份〕，"
        "剔除〔筛选标准〕后，最终得到〔样本量〕个有效样本。\n"
        "二、变量定义\n（1）被解释变量：〔变量名〕，采用〔度量方式〕；\n"
        "（2）解释变量：〔变量名〕，采用〔度量方式〕；\n"
        "（3）控制变量：参照既有文献，控制〔变量1〕、〔变量2〕等。\n"
        "三、模型设定\n本文构建如下回归模型：\n"
        "Yᵢₜ = β₀ + β₁Xᵢₜ + ΣγControls + μᵢ + λₜ + εᵢₜ\n"
        "其中 Y 为被解释变量，X 为核心解释变量，μᵢ 与 λₜ 分别为个体与时间固定效应。"
    ),
    "实证结果": (
        "【实证结果】\n"
        "一、描述性统计\n〔简述主要变量的均值、标准差与极值，说明分布特征〕。\n"
        "二、基准回归\n表 X 报告了基准回归结果。第（1）列〔模型设定〕中，"
        "核心解释变量〔变量名〕的系数为〔数值〕，在〔显著性水平〕水平上显著，"
        "表明〔经济含义解读〕。\n"
        "三、稳健性检验\n为验证结论的稳健性，本文〔替换变量/更换方法/子样本回归〕，"
        "结果保持一致（见附表）。"
    ),
    "结论与建议": (
        "【结论与建议】\n"
        "本文基于〔样本〕，考察了〔核心问题〕。研究发现：〔结论1〕；〔结论2〕。"
        "基于上述结论，本文提出如下建议：\n"
        "第一，〔建议1〕；\n第二，〔建议2〕；\n第三，〔建议3〕。"
        "本文的局限在于〔研究局限〕，未来研究可〔改进方向〕。"
    ),
}


# ---- 表格转 LaTeX（booktabs 三线表） ----

def df_to_latex(headers: list[str], rows: list[list[str]], caption: str = "", label: str = "") -> str:
    """生成 booktabs 三线表 LaTeX 代码。"""
    ncol = len(headers)
    colspec = "l" + "c" * (ncol - 1) if ncol > 1 else "l"
    lines = []
    lines.append("\\begin{table}[htbp]")
    lines.append("  \\centering")
    if caption:
        lines.append(f"  \\caption{{{caption}}}")
    if label:
        lines.append(f"  \\label{{{label}}}")
    lines.append("  \\begin{tabular}{%s}" % colspec)
    lines.append("    \\toprule")
    lines.append("    " + " & ".join(headers) + " \\\\")
    lines.append("    \\midrule")
    for row in rows:
        lines.append("    " + " & ".join(row) + " \\\\")
    lines.append("    \\bottomrule")
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def paste_to_latex(text: str, caption: str = "", label: str = "tab:1") -> str:
    """粘贴数据 → LaTeX 三线表。"""
    from core.three_line_table import parse_pasted

    df = parse_pasted(text)
    if df.empty:
        return ""
    headers = [str(c) for c in df.columns]
    rows = [[str(v) for v in row] for _, row in df.iterrows()]
    return df_to_latex(headers, rows, caption, label)
