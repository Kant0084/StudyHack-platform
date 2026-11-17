"""学术三线表生成器。

输入：粘贴数据（Tab/逗号分隔）或 DataFrame。
输出：三线表 PNG（matplotlib 精确绘制三条横线）+ Word（复用 ERK 三线表渲染）。

三线表规范（GB/T 7714）：仅顶线（粗）、表头底线（细）、底线（粗）三条横线，无竖线。
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

# 中文字体（保证 PNG 中文不乱码）
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

import pandas as pd


def parse_pasted(text: str) -> pd.DataFrame:
    """解析粘贴的表格数据。

    支持：制表符(Tab)、逗号、空格（多空格）分隔；首行作为表头。
    """
    text = text.strip()
    if not text:
        return pd.DataFrame()

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return pd.DataFrame()

    def _split(line: str) -> list[str]:
        if "\t" in line:
            return line.split("\t")
        if "," in line:
            return [c.strip() for c in line.split(",")]
        parts = [p for p in line.replace("，", ",").split() if p]
        return parts if parts else [line]

    rows = [_split(ln) for ln in lines]
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]

    header = [str(h).strip() or f"列{i + 1}" for i, h in enumerate(rows[0])]
    df = pd.DataFrame(rows[1:], columns=header)
    return df


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.3f}" if v == v else "—"
    return str(v)


def _build_fig(df: pd.DataFrame, title: str):
    """手动布局绘制三线表：直接计算列宽/行高，画三条横线 + 文本（完全可控）。"""
    import matplotlib.pyplot as plt

    n_rows, n_cols = df.shape
    headers = [str(c) for c in df.columns]
    cells = [[_fmt(v) for v in row] for _, row in df.iterrows()]

    def text_w(s: str) -> int:
        return sum(2 if "\u4e00" <= ch <= "\u9fff" else 1 for ch in str(s))

    # 列宽（按文本长度，中文计 2）
    col_w = []
    for j in range(n_cols):
        w = text_w(headers[j])
        for i in range(n_rows):
            w = max(w, text_w(cells[i][j]))
        col_w.append(max(w, 4))
    unit = 0.30
    widths = [w * unit + 0.9 for w in col_w]
    total_w = sum(widths) + 0.4

    header_h = 0.55
    row_h = 0.48
    top_margin = 0.9  # 标题空间
    total_h = top_margin + header_h + n_rows * row_h + 0.6

    fig, ax = plt.subplots(figsize=(max(total_w, 5.0), max(total_h, 2.0)))
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    ax.axis("off")

    # 三条横线的 y 坐标（从上往下）
    y_top = total_h - top_margin
    y_header_bottom = y_top - header_h
    y_bottom = y_header_bottom - n_rows * row_h

    left, right = 0.2, total_w - 0.2
    for y, lw in ((y_top, 2.0), (y_header_bottom, 1.0), (y_bottom, 2.0)):
        ax.plot([left, right], [y, y], color="black", linewidth=lw, solid_capstyle="butt", clip_on=False)

    # 表头文本
    x = left + 0.05
    for j in range(n_cols):
        cx = x + widths[j] / 2
        ax.text(cx, (y_top + y_header_bottom) / 2, headers[j], ha="center", va="center",
                fontsize=10.5, fontweight="bold")
        x += widths[j]

    # 数据行文本
    for i in range(n_rows):
        yc = y_header_bottom - (i + 0.5) * row_h
        x = left + 0.05
        for j in range(n_cols):
            cx = x + widths[j] / 2
            ax.text(cx, yc, cells[i][j], ha="center", va="center", fontsize=10.5)
            x += widths[j]

    if title:
        ax.text(total_w / 2, total_h - 0.15, title, ha="center", va="top", fontsize=12)

    return fig, ax


def table_to_png(df: pd.DataFrame, title: str, output_path: str | Path) -> Path:
    """绘制三线表并保存为 PNG。"""
    fig, _ = _build_fig(df, title)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200, bbox_inches="tight", pad_inches=0.3, facecolor="white")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return p


def table_to_png_bytes(df: pd.DataFrame, title: str) -> bytes:
    """绘制三线表，返回 PNG 字节流。"""
    fig, _ = _build_fig(df, title)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=200, bbox_inches="tight", pad_inches=0.3, facecolor="white")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return buf.getvalue()
