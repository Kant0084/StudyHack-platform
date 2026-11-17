"""三线表渲染（中文期刊规范）。

三线表：只有顶线、表头分隔线、底线三条横线，无竖线。
本模块将多个 RegressionResult 归并渲染为一张回归表，支持：
  - 控制台输出（纯文本对齐，便于快速查看）
  - Markdown 输出（便于写入文档）
  - Excel 输出（openpyxl 精确控制边框，产出真正的三线表）

显著性标注规则（可经 Config.table 调整）：
  *** p<0.01, ** p<0.05, * p<0.1
"""

from __future__ import annotations

from pathlib import Path

from erk.config import Config
from erk.stats.regression import RegressionResult


def _stars(p: float, cfg: Config) -> str:
    """按配置的显著性阈值返回星号。

    按阈值从小到大（即从最严格到最宽松）判断，先命中最小阈值才返回
    对应星号，避免"先命中宽松阈值"导致高显著系数只标一个星。
    排序后与 sig_levels/sig_symbols 的声明顺序无关。
    """
    pairs = sorted(zip(cfg.table.sig_levels, cfg.table.sig_symbols))
    for lv, sym in pairs:
        if p < lv:
            return sym
    return ""


def _fmt_coef(val: float, p: float, cfg: Config) -> str:
    d = cfg.table.decimals
    return f"{val:.{d}f}{_stars(p, cfg)}"


def _fmt_se(val: float, cfg: Config) -> str:
    d = cfg.table.decimals
    return f"({val:.{d}f})"


def _union_vars(results: list[RegressionResult]) -> list[str]:
    """所有模型自变量的并集，保持出现顺序，确保行对齐。"""
    seen: list[str] = []
    for r in results:
        for k in r.params:
            if k not in seen:
                seen.append(k)
    return seen


class RegressionTable:
    """一张回归表，包含一列或多列模型。"""

    def __init__(self, results: list[RegressionResult], cfg: Config, title: str = ""):
        self.results = results
        self.cfg = cfg
        self.title = title
        self.vars = _union_vars(results)

    # ---- 内部行构造（三个渲染器共用，保证输出一致） ----

    def _header(self) -> list[str]:
        return ["变量"] + [r.label or f"({i + 1})" for i, r in enumerate(self.results)]

    def _body_rows(self) -> list[list[str]]:
        rows: list[list[str]] = []
        for var in self.vars:
            coefs, ses = self._var_rows(var)
            rows.append([var] + coefs)     # 系数行
            rows.append([""] + ses)        # 标准误行（变量列留空）
        return rows

    def _var_rows(self, var: str) -> tuple[list[str], list[str]]:
        coefs, ses = [], []
        for r in self.results:
            if var in r.params:
                coefs.append(_fmt_coef(r.params[var], r.pvalues[var], self.cfg))
                ses.append(_fmt_se(r.ses[var], self.cfg))
            else:
                coefs.append("")
                ses.append("")
        return coefs, ses

    def _footer_notes(self) -> list[str]:
        notes = []
        for i, r in enumerate(self.results):
            label = r.label or f"({i + 1})"
            fe_txt = "Yes" if r.fe else "No"
            cluster_txt = r.cluster or "—"
            notes.append(f"{label}: 固定效应={fe_txt}, 聚类={cluster_txt}, N={r.nobs}, R²={r.r2:.3f}")
        notes.append("注: 括号内为标准误; * p<0.1, ** p<0.05, *** p<0.01")
        return notes

    # ---- 渲染输出 ----

    def render_console(self) -> str:
        """纯文本对齐输出，便于终端快速查看。"""
        header = self._header()
        body = self._body_rows()
        all_rows = [header] + body
        widths = [
            max(len(str(row[c])) for row in all_rows) for c in range(len(header))
        ]
        sep = "-" * (sum(widths) + 2 * (len(widths) - 1))

        lines = []
        if self.title:
            lines.append(self.title)
        lines.append(self._pad(header, widths))
        lines.append(sep)
        for row in body:
            lines.append(self._pad(row, widths))
        lines.append(sep)
        lines.extend(self._footer_notes())
        return "\n".join(lines)

    def render_markdown(self) -> str:
        """Markdown 表格输出（含底部注记）。"""
        header = self._header()
        body = self._body_rows()
        lines = []
        if self.title:
            lines.append(f"### {self.title}\n")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for row in body:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines.extend(f"- {n}" for n in self._footer_notes())
        return "\n".join(lines)

    def to_excel(self, path: str | Path) -> None:
        """用 openpyxl 精确控制边框，产出真正的三线表（顶线粗、表头下线细、底线粗）。"""
        from openpyxl import Workbook
        from openpyxl.styles import Border, Font, Side
        from openpyxl.utils import get_column_letter

        header = self._header()
        body = self._body_rows()
        ncols = len(header)

        wb = Workbook()
        ws = wb.active
        ws.title = "回归结果表"

        top = Side(style="medium")
        mid = Side(style="thin")
        bottom = Side(style="medium")

        # 表头（第 1 行）：顶线 + 表头下线
        for c, text in enumerate(header, start=1):
            cell = ws.cell(row=1, column=c, value=text)
            cell.font = Font(bold=True)
            cell.border = Border(top=top, bottom=mid)

        # 表体
        r = 2
        for row in body:
            for c, text in enumerate(row, start=1):
                ws.cell(row=r, column=c, value=text)
            r += 1
        last_row = r - 1

        # 底线
        for c in range(1, ncols + 1):
            ws.cell(row=last_row, column=c).border = Border(bottom=bottom)

        # 底部注记（写在表体下方两行起）
        note_row = last_row + 2
        for note in self._footer_notes():
            ws.cell(row=note_row, column=1, value=note)
            note_row += 1

        # 列宽
        for c in range(1, ncols + 1):
            ws.column_dimensions[get_column_letter(c)].width = 16

        wb.save(path)

    @staticmethod
    def _pad(row: list[str], widths: list[int]) -> str:
        return "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
