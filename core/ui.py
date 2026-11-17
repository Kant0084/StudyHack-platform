"""公共 Streamlit UI 组件（页面逻辑，与计算逻辑分离）。"""

from __future__ import annotations

import matplotlib

# 图表中文字体（Windows 常见中文字体）
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

import streamlit as st  # noqa: E402

from core import io_utils  # noqa: E402


def upload_excel(key: str = "upload", label: str = "上传 Excel / CSV 文件"):
    """统一上传组件。返回 (df, filename)；未上传返回 (None, None)。"""
    uploaded = st.file_uploader(label, type=["xlsx", "xls", "csv"], key=key)
    if uploaded is None:
        return None, None
    try:
        fid, path = io_utils.save_upload(uploaded)
        df = io_utils.read_upload(path)
        st.success(f"已读取「{uploaded.name}」：{df.shape[0]} 行 × {df.shape[1]} 列")
        return df, uploaded.name
    except Exception as exc:  # noqa: BLE001
        st.error(f"文件读取失败：{exc}。请确认文件格式（.xlsx / .xls / .csv）未损坏。")
        return None, None


def download_docx(path, label: str = "⬇️ 下载 Word 报告") -> None:
    """Word 报告下载按钮。"""
    try:
        with open(path, "rb") as f:
            st.download_button(label, data=f.read(), file_name=path.name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except OSError as exc:
        st.error(f"报告文件生成失败：{exc}")


def download_bytes(data: bytes, filename: str, mime: str, label: str = "⬇️ 下载") -> None:
    st.download_button(label, data=data, file_name=filename, mime=mime)


def pie_chart(counts, title: str = ""):
    """饼图（matplotlib），counts 为 pandas Series（index=类别，value=频数）。"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(counts.values, labels=counts.index.astype(str), autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    if title:
        ax.set_title(title, fontsize=12)
    return fig


def bar_chart(counts, title: str = ""):
    """柱状图（matplotlib）。"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(counts.index.astype(str), counts.values, color="#2E7D6B")
    ax.set_ylabel("频数")
    if title:
        ax.set_title(title, fontsize=12)
    plt.xticks(rotation=30, ha="right")
    return fig
