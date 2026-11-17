"""学术写作辅助 —— 学术润色 / 论文模板 / 表格公式转 LaTeX。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from core import auth_ui

from core import writing_service as ws
from core import llm_client
from core import ui

st.set_page_config(page_title="学术写作辅助", page_icon="✍️", layout="wide")

auth_ui.render_auth_sidebar()
auth_ui.require_login()

st.title("✍️ 学术写作辅助")
st.caption("学术化润色 · 论文各章节模板 · 表格/公式转 LaTeX")

tab1, tab2, tab3 = st.tabs(["🖋️ 学术润色", "📑 论文模板", "📐 转 LaTeX"])

with tab1:
    st.markdown("### 学术化润色")
    st.caption("输入口语化表述，AI 一键改写为规范学术表达（需自备 API Key）")
    with st.expander("🔑 AI 设置", expanded=True):
        base_url, model, api_key = ui.ai_settings("polish")
    raw = st.text_area("输入原始表述", height=150,
                       placeholder="我觉得这个变量很重要，而且结果也证明了我们的想法……")
    if st.button("✨ AI 学术化改写", type="primary"):
        if not api_key.strip():
            st.warning("请先在上方「AI 设置」中输入你的 API Key。")
        elif not base_url.strip() or not model.strip():
            st.warning("请完整填写 Base URL 和模型名。")
        elif not raw.strip():
            st.warning("请先输入需要润色的文本。")
        else:
            try:
                st.markdown("**润色结果**")
                st.write_stream(llm_client.chat_stream(base_url, api_key, model, llm_client.POLISH_SYSTEM, raw))
            except Exception as exc:  # noqa: BLE001
                st.error(f"调用失败：{exc}")
    st.divider()
    with st.expander("🔧 离线规则润色（无需 AI，效果较基础）"):
        raw_offline = st.text_area("输入原始表述", height=150, key="raw_offline",
                                   placeholder="我觉得这个变量很重要，而且结果也证明了我们的想法……")
        if st.button("✨ 规则润色"):
            if not raw_offline.strip():
                st.warning("请先输入需要润色的文本。")
            else:
                polished, changes = ws.polish_text(raw_offline)
                st.markdown("**润色后**")
                st.write(polished)
                if changes:
                    st.markdown("**替换记录**")
                    for c in changes:
                        st.caption(c)
                else:
                    st.caption("未命中内置替换规则，文本已较为学术化。")

with tab2:
    st.markdown("### 论文写作模板")
    tpl_name = st.selectbox("选择章节模板", list(ws.TEMPLATES.keys()))
    tpl = ws.TEMPLATES[tpl_name]
    st.code(tpl, language=None)
    st.download_button("⬇️ 下载模板", data=tpl.encode("utf-8"), file_name=f"{tpl_name}模板.txt", mime="text/plain")
    st.caption("提示：〔〕内为占位符，请替换为实际内容。")

with tab3:
    st.markdown("### 表格 / 公式转 LaTeX")
    st.caption("粘贴表格数据，生成可直接编译的 booktabs 三线表 LaTeX 代码")
    latex_caption = st.text_input("表格标题（\\caption）", value="")
    latex_label = st.text_input("标签（\\label）", value="tab:1")
    latex_text = st.text_area("粘贴数据（首行为表头，Tab/逗号分隔）", height=150,
                              placeholder="变量\t系数\t标准误\nx1\t0.342***\t(0.081)\nx2\t0.120\t(0.095)")
    if st.button("🔧 生成 LaTeX", type="primary"):
        code = ws.paste_to_latex(latex_text, latex_caption, latex_label)
        if code:
            st.session_state["latex_code"] = code
        else:
            st.warning("请粘贴有效数据。")
    if st.session_state.get("latex_code"):
        st.code(st.session_state["latex_code"], language="latex")
        st.download_button("⬇️ 下载 .tex", data=st.session_state["latex_code"].encode("utf-8"),
                           file_name="table.tex", mime="text/plain")
