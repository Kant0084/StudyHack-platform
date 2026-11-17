"""报告组装器（ReportBuilder）。

把各模块的分析结果组装成结构化报告，支持 Markdown 与 Word(.docx) 双渲染。
Word 渲染输出符合中文期刊规范的三线表与中文字体（宋体/黑体）。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def df_to_markdown(df: pd.DataFrame, float_fmt: str = "{:.3f}") -> str:
    """DataFrame → Markdown 表格（避免额外依赖）。"""
    n_cols = len(df.columns)
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join(["---"] * n_cols) + "|"
    rows = []
    for _, row in df.iterrows():
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append(float_fmt.format(v))
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep] + rows)


class ReportBuilder:
    """报告组装器：收集 section，统一渲染为 Markdown 或 Word。"""

    def __init__(self, title: str = ""):
        self.title = title
        self._sections: list[tuple] = []  # (kind, payload)
        if title:
            self._sections.append(("heading", (title, 1)))

    # ---- 组装方法 ----

    def heading(self, text: str, level: int = 1) -> "ReportBuilder":
        self._sections.append(("heading", (text, level)))
        return self

    def paragraph(self, text: str) -> "ReportBuilder":
        self._sections.append(("paragraph", text))
        return self

    def table(self, df: pd.DataFrame, title: str = "") -> "ReportBuilder":
        self._sections.append(("table", (df, title)))
        return self

    def raw(self, markdown: str) -> "ReportBuilder":
        """直接插入 Markdown 片段（如三线表）。Word 渲染时尝试解析表格。"""
        self._sections.append(("raw", markdown))
        return self

    def note(self, text: str) -> "ReportBuilder":
        self._sections.append(("note", text))
        return self

    def bullet(self, text: str) -> "ReportBuilder":
        self._sections.append(("bullet", text))
        return self

    def blank(self) -> "ReportBuilder":
        self._sections.append(("blank", None))
        return self

    # ---- Markdown 渲染 ----

    def render_markdown(self) -> str:
        lines: list[str] = []
        for kind, payload in self._sections:
            if kind == "heading":
                text, level = payload
                lines.append("#" * level + " " + text)
                lines.append("")
            elif kind == "paragraph":
                lines.append(payload)
                lines.append("")
            elif kind == "table":
                df, title = payload
                if title:
                    lines.append(f"**{title}**")
                lines.append(df_to_markdown(df))
                lines.append("")
            elif kind == "raw":
                lines.append(payload)
                lines.append("")
            elif kind == "note":
                lines.append(f"> ⚠ {payload}")
                lines.append("")
            elif kind == "bullet":
                lines.append(f"- {payload}")
            elif kind == "blank":
                lines.append("")
        return "\n".join(lines).strip() + "\n"

    # ---- Word 渲染 ----

    def render_word(self, path: str | Path) -> Path:
        """渲染为 .docx（中文字体 + 三线表）。"""
        from docx import Document
        from docx.shared import RGBColor

        doc = Document()
        for kind, payload in self._sections:
            if kind == "heading":
                text, level = payload
                p = doc.add_heading(level=min(level, 4))
                run = p.add_run(text)
                _set_run_font(run, name="黑体", size=_heading_size(level), bold=True)
            elif kind == "paragraph":
                run = doc.add_paragraph().add_run(payload)
                _set_run_font(run, name="宋体", size=10.5)
            elif kind == "table":
                df, title = payload
                if title:
                    p = doc.add_paragraph()
                    r = p.add_run(title)
                    _set_run_font(r, name="黑体", size=10.5, bold=True)
                _add_dataframe_table(doc, df)
            elif kind == "raw":
                _add_raw(doc, payload)
            elif kind == "note":
                run = doc.add_paragraph().add_run("⚠ " + payload)
                _set_run_font(run, name="宋体", size=9, italic=True, color=RGBColor(0x80, 0x80, 0x80))
            elif kind == "bullet":
                run = doc.add_paragraph(style="List Bullet").add_run(payload)
                _set_run_font(run, name="宋体", size=10.5)

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.save(p)
        return p

    def save(self, path: str | Path) -> Path:
        """按扩展名保存（.md → Markdown，.docx → Word）。"""
        p = Path(path)
        if p.suffix.lower() == ".docx":
            return self.render_word(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.render_markdown(), encoding="utf-8")
        return p


# ---- Word 渲染辅助 ----

def _heading_size(level: int) -> int:
    return {1: 16, 2: 14, 3: 12, 4: 11}.get(level, 10)


def _set_run_font(run, name="宋体", size=10.5, bold=False, italic=False, color=None):
    """设置中文字体（含 eastAsia）。"""
    from docx.oxml.ns import qn
    from docx.shared import Pt

    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def _add_dataframe_table(doc, df: pd.DataFrame):
    """把 DataFrame 渲染为 Word 三线表。"""
    table = doc.add_table(rows=len(df) + 1, cols=len(df.columns))
    for j, col in enumerate(df.columns):
        cell = table.rows[0].cells[j]
        cell.text = str(col)
        _style_cell(cell, bold=True)
    for i, (_, row) in enumerate(df.iterrows()):
        for j, v in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = f"{v:.3f}" if isinstance(v, float) else str(v)
            _style_cell(cell)
    _set_three_line_borders(table)


def _style_cell(cell, bold=False):
    """设置单元格字体（宋体）。"""
    from docx.oxml.ns import qn

    for p in cell.paragraphs:
        for run in p.runs:
            run.font.name = "宋体"
            run.font.bold = bold
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def _set_three_line_borders(table):
    """设置三线表边框（顶线粗、表头下线细、底线粗，无竖线）。"""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def _cell_border(cell, top=None, bottom=None):
        tcPr = cell._tc.get_or_add_tcPr()
        borders = OxmlElement("w:tcBorders")
        for edge, spec in (("top", top), ("bottom", bottom)):
            if spec:
                val, sz = spec
                el = OxmlElement(f"w:{edge}")
                el.set(qn("w:val"), val)
                el.set(qn("w:sz"), str(sz))
                el.set(qn("w:color"), "000000")
                borders.append(el)
        tcPr.append(borders)

    rows = table.rows
    for cell in rows[0].cells:
        _cell_border(cell, top=("single", 12), bottom=("single", 6))
    for cell in rows[-1].cells:
        _cell_border(cell, bottom=("single", 12))


def _add_raw(doc, markdown: str):
    """处理 raw（markdown 片段）：表格则转 Word 表格，否则作为段落。"""
    lines = [l.strip() for l in markdown.strip().splitlines() if l.strip()]
    if len(lines) >= 2 and lines[0].startswith("|") and set(lines[1].replace("|", "").replace("-", "").strip()) == set():
        header = [c.strip() for c in lines[0].strip("|").split("|")]
        data_rows = [l for l in lines[2:] if l.startswith("|")]
        table = doc.add_table(rows=1 + len(data_rows), cols=len(header))
        for j, h in enumerate(header):
            table.rows[0].cells[j].text = h
            _style_cell(table.rows[0].cells[j], bold=True)
        for i, line in enumerate(data_rows):
            cells = [c.strip() for c in line.strip("|").split("|")]
            for j, v in enumerate(cells):
                table.rows[i + 1].cells[j].text = v
                _style_cell(table.rows[i + 1].cells[j])
        _set_three_line_borders(table)
        return
    for line in lines:
        clean = line.lstrip("#").strip()
        if clean:
            run = doc.add_paragraph().add_run(clean)
            _set_run_font(run, name="宋体", size=10.5)
