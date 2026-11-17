"""Word 分析报告生成（基于 ERK ReportBuilder + 学术规范后处理）。

报告结构（对齐参赛要求 3.1.4）：
  数据概览 → 描述统计 → 信度/效度/相关 → 学术解读 → 核心指标释义 →
  分析方法说明 → 参考文献格式示例。

格式规范：
  - 统计表为标准学术三线表（GB/T 7714，顶线/表头底线/底线，无竖线）；
  - 字体宋体五号(10.5pt)，1.5 倍行距，表格内文字居中；
  - 导出 .docx，兼容 Office 2019+ / WPS。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from erk.report.builder import ReportBuilder
from erk.report.table import RegressionTable
from erk.config import Config


# ---- 固定附录模板（核心指标释义 / 方法说明 / 参考文献） ----

_CORE_INDICATORS = [
    ("Cronbach's α 系数", "衡量量表内部一致性的信度指标，取值 0~1；一般认为 α≥0.70 可接受、α≥0.80 良好（Nunnally, 1978）。"),
    ("KMO 值", "取样充分性检验统计量，反映变量间相关程度，用于判断是否适合因子分析；KMO≥0.60 可接受、≥0.80 良好（Kaiser, 1974）。"),
    ("Bartlett 球形检验", "检验相关矩阵是否为单位阵，p<0.05 表明变量间存在显著相关，适合因子分析（Bartlett, 1954）。"),
    ("因子载荷", "反映题项与提取因子之间的关联强度，|载荷|≥0.40 可接受、≥0.50 良好（Hair et al., 2010）。"),
    ("累计方差解释率", "提取因子解释原始变量总方差的比例，常用经验标准为 ≥60%。"),
    ("回归系数", "在其他变量不变的条件下，解释变量每变动 1 单位引起的因变量平均变动量。"),
    ("R² / 调整 R²", "模型拟合优度，反映解释变量对因变量变异的解释比例；调整 R² 对变量个数做了惩罚，更适用于多变量比较。"),
    ("标准误 / t 值 / P 值", "标准误衡量系数估计精度；t 值为系数与标准误之比；P 值为显著性检验概率，P<0.05 通常认为显著。"),
]

_METHOD_NOTES = [
    "信度分析采用 Cronbach's α 系数法，并报告校正的项总计相关（CITC）与删除该项后的 α 系数。",
    "效度分析采用 KMO 与 Bartlett 球形检验作为前置检验，探索性因子分析采用主成分法提取、最大方差法（varimax）正交旋转，因子数按特征值大于 1（Kaiser 准则）确定。",
    "描述性统计报告均值、标准差、最小值、中位数、最大值等指标。",
    "相关性分析采用 Pearson 积矩相关（双侧检验），显著性标注 * p<0.05, ** p<0.01, *** p<0.001。",
    "基准回归采用普通最小二乘法（OLS）估计，报告回归系数、标准误、t 值、P 值、R²、调整 R²。",
]

_REFERENCES = [
    "Nunnally J C. Psychometric theory[M]. 2nd ed. New York: McGraw-Hill, 1978.",
    "Kaiser H F. An index of factorial simplicity[J]. Psychometrika, 1974, 39(1): 31-36.",
    "Bartlett M S. A note on the multiplying factors for various χ² approximations[J]. Journal of the Royal Statistical Society, 1954, 16(2): 296-298.",
    "Hair J F, Black W C, Babin B J, et al. Multivariate data analysis[M]. 7th ed. Upper Saddle River: Prentice Hall, 2010.",
]


def _report_header(b: ReportBuilder, title: str, author: str) -> None:
    """报告标题与作者信息。"""
    if title:
        b.heading(title, 1)
    if author:
        b.paragraph(f"作者：{author}")
    b.blank()


def _append_interpret(b: ReportBuilder, text: str | None) -> None:
    """附加学术解读（加粗标注「解读」）。"""
    if text:
        b.paragraph(f"解读：{text}")


# ---- 问卷报告 ----

def build_survey_report(result: dict, title: str, author: str, output_path: str) -> Path:
    b = ReportBuilder("")
    _report_header(b, title or "问卷分析报告", author)

    # 一、数据概览
    b.heading("一、数据概览", 2)
    b.paragraph(f"有效样本量：{result.get('n_samples', 0)} 份。")
    type_dist = result.get("type_dist") or {}
    if type_dist:
        b.paragraph("题型分布：" + "；".join(f"{k} {v} 个" for k, v in type_dist.items()) + "。")

    # 二、描述统计
    desc = result.get("descriptives")
    if desc is not None and not desc.empty:
        b.heading("二、描述统计", 2)
        b.table(desc, "表1 量表题项描述统计")

    # 三、信度分析
    rel = result.get("reliability")
    if rel:
        b.heading("三、信度分析", 2)
        b.paragraph(f"Cronbach's α = {rel['alpha']:.3f}（题项数 {rel['n_items']}，样本量 {rel['n_samples']}）。")
        _append_interpret(b, rel.get("interpret"))
        b.table(rel["item_table"], "表2 项总计统计量")

    # 四、效度分析
    val = result.get("validity")
    if val:
        b.heading("四、效度分析", 2)
        b.paragraph(
            f"KMO = {val['kmo']:.3f}；Bartlett 球形检验 χ² = {val['bartlett_chi2']:.2f}（df={val['bartlett_df']}），"
            f"p = {val['bartlett_p']:.4f}。"
        )
        _append_interpret(b, val.get("interpret"))
        b.table(val["loading_table"], "表3 旋转后因子载荷矩阵")
        b.table(val["variance_table"], "表4 方差解释率")

    # 五、相关性分析
    corr = result.get("correlation")
    if corr is not None:
        b.heading("五、相关性分析", 2)
        b.table(corr["labeled"], "表5 相关系数矩阵")
        b.note("注：* p<0.05, ** p<0.01, *** p<0.001")

    # 六、核心指标释义
    b.heading("六、核心指标释义", 2)
    for name, desc in _CORE_INDICATORS:
        b.paragraph(f"{name}：{desc}")

    # 七、分析方法说明
    b.heading("七、分析方法说明", 2)
    for m in _METHOD_NOTES:
        b.paragraph(m)

    # 八、参考文献
    b.heading("八、参考文献格式示例", 2)
    for i, ref in enumerate(_REFERENCES, 1):
        b.paragraph(f"[{i}] {ref}")

    return _save_and_postprocess(b, output_path)


# ---- 经管实证报告 ----

def build_regression_report(result: dict, title: str, author: str, output_path: str) -> Path:
    b = ReportBuilder("")
    _report_header(b, title or "经管实证分析报告", author)

    b.heading("一、数据与变量", 2)
    b.paragraph(
        f"预处理后样本量：{result.get('n_after', 0)}（原始 {result.get('n_before', 0)}）。"
    )

    desc = result.get("descriptives")
    if desc is not None and not desc.empty:
        b.heading("二、描述性统计", 2)
        b.table(desc, "表1 主要变量描述统计")

    corr = result.get("correlation")
    if corr is not None:
        b.heading("三、相关性分析", 2)
        b.table(corr["labeled"], "表2 相关系数矩阵")
        b.note("注：* p<0.05, ** p<0.01, *** p<0.001")

    base = result.get("baseline")
    if base:
        b.heading("四、基准回归结果", 2)
        tidy = base["tidy"]
        reg_df = pd.DataFrame(
            {
                "变量": tidy["term"],
                "回归系数": [f"{v:.3f}" for v in tidy["estimate"]],
                "标准误": [f"({v:.3f})" for v in tidy["std_error"]],
                "t值": [f"{v:.3f}" if pd.notna(v) else "—" for v in tidy["statistic"]],
                "P值": [f"{v:.3f}" if pd.notna(v) else "—" for v in tidy["p_value"]],
            }
        )
        b.table(reg_df, "表3 基准回归结果")
        f_txt = f"{base['f_stat']:.2f}" if base.get("f_stat") is not None else "—"
        b.paragraph(
            f"样本量 N = {base['nobs']}；R² = {base['r2']:.3f}；调整 R² = {base['adj_r2']:.3f}；F = {f_txt}。"
        )
        _append_interpret(b, base.get("interpret"))

    grouped = result.get("grouped")
    if grouped:
        b.heading("五、分组回归（异质性分析）", 2)
        for gr in grouped["results"]:
            if "error" in gr:
                b.note(f"分组「{gr['group']}」：{gr['error']}")
                continue
            g_tidy = gr["tidy"]
            g_df = pd.DataFrame(
                {
                    "变量": g_tidy["term"],
                    "回归系数": [f"{v:.3f}" for v in g_tidy["estimate"]],
                    "标准误": [f"({v:.3f})" for v in g_tidy["std_error"]],
                }
            )
            b.table(g_df, f"表 分组 {gr['group']}（N={gr['nobs']}）")

    # 六、核心指标释义
    b.heading("六、核心指标释义", 2)
    for name, desc in _CORE_INDICATORS:
        b.paragraph(f"{name}：{desc}")

    # 七、分析方法说明
    b.heading("七、分析方法说明", 2)
    for m in _METHOD_NOTES:
        b.paragraph(m)

    b.heading("八、参考文献格式示例", 2)
    for i, ref in enumerate(_REFERENCES, 1):
        b.paragraph(f"[{i}] {ref}")

    return _save_and_postprocess(b, output_path)


# ---- 保存 + 学术排版后处理 ----

def _save_and_postprocess(b: ReportBuilder, output_path: str) -> Path:
    """保存 docx 并做排版后处理（1.5 倍行距 + 表格居中 + 字体）。"""
    p = b.render_word(output_path)
    _postprocess_docx(p)
    return p


def _postprocess_docx(path: Path) -> None:
    """排版增强：全局 1.5 倍行距、表格内文字居中、宋体五号。"""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = Document(str(path))

    # 段落：1.5 倍行距 + 宋体五号
    for p in doc.paragraphs:
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        for run in p.runs:
            run.font.name = "宋体"
            run.font.size = Pt(10.5)
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    # 表格：单元格文字居中 + 宋体五号
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    for run in para.runs:
                        run.font.name = "宋体"
                        run.font.size = Pt(10.5)
                        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    doc.save(str(path))


def build_docx_from_tables(tables: list[tuple[pd.DataFrame, str]], title: str, author: str, output_path: str) -> Path:
    """通用：把多张表格 + 标题组装成三线表 Word 文档（供三线表生成器复用）。"""
    b = ReportBuilder("")
    _report_header(b, title or "三线表", author)
    for i, (df, t) in enumerate(tables, 1):
        b.table(df, t or f"表{i}")
    return _save_and_postprocess(b, output_path)
