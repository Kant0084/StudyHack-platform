"""学术三线表生成器 —— 粘贴/上传数据 → 标准三线表（Word / PNG）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from core.ui import upload_excel, download_bytes, download_docx
from core import three_line_table, report_service

st.set_page_config(page_title="学术三线表生成", page_icon="📝", layout="wide")

st.title("📝 学术三线表生成器")
st.caption("粘贴 Excel 数据或上传表格文件，一键生成符合 GB/T 7714 规范的标准学术三线表")

tab_in, tab_preview = st.tabs(["① 输入数据", "② 生成与导出"])

df = None

with tab_in:
    mode = st.radio("数据来源", ["粘贴数据", "上传 Excel / CSV"], horizontal=True)
    if mode == "粘贴数据":
        st.markdown("**粘贴表格数据**（首行为表头，用 Tab / 逗号 / 空格分隔）")
        pasted = st.text_area("在此粘贴", height=180, placeholder="变量\t均值\t标准差\n营业收入\t1.234\t0.567\n净利润\t0.890\t0.321")
        if pasted.strip():
            df = three_line_table.parse_pasted(pasted)
    else:
        df, _ = upload_excel(key="tlt_upload")

    table_title = st.text_input("表格标题（可选）", value="")

with tab_preview:
    if df is not None and not df.empty:
        st.markdown("### 数据预览")
        st.dataframe(df, width="stretch")

        st.markdown("### 导出")
        c1, c2, c3 = st.columns(3)
        with c1:
            png_bytes = three_line_table.table_to_png_bytes(df, table_title)
            download_bytes(png_bytes, "三线表.png", "image/png", "⬇️ 下载 PNG")
        with c2:
            if st.button("📄 生成 Word（三线表）", type="primary"):
                out_path = Path("assets") / "三线表.docx"
                report_service.build_docx_from_tables([(df, table_title)], table_title, "", str(out_path))
                st.session_state["tlt_docx"] = str(out_path)
            if st.session_state.get("tlt_docx"):
                download_docx(Path(st.session_state["tlt_docx"]), "⬇️ 下载 Word")
        with c3:
            download_bytes(df.to_csv(index=False).encode("utf-8-sig"), "三线表数据.csv", "text/csv", "⬇️ 下载数据 CSV")

        st.divider()
        st.image(png_bytes, caption="三线表预览（顶线/表头底线/底线，无竖线）", width="stretch")
    else:
        st.info("👈 请先在「输入数据」标签页粘贴或上传数据。")
        st.markdown(
            """
            **三线表规范（GB/T 7714）：**
            - 仅保留顶线（粗）、表头底线（细）、底线（粗）三条横线
            - 无竖线、无斜线
            - 表格内文字居中，适配本科论文通用格式
            """
        )
