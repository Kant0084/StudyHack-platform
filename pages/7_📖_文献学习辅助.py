"""文献学习辅助 —— 摘要拆解 / 科研笔记模板 / 期刊分区查询。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from core import auth_ui

from core import literature_service as lit
from core import llm_client
from core import ui

st.set_page_config(page_title="文献学习辅助", page_icon="📖", layout="wide")

auth_ui.require_login()

st.title("📖 文献学习辅助")
st.caption("文献摘要拆解 · 科研笔记模板 · 期刊分区查询")

tab1, tab2, tab3 = st.tabs(["🔬 摘要拆解", "📓 笔记模板", "🏆 期刊分区"])

with tab1:
    st.markdown("### 文献摘要拆解")
    st.caption("粘贴摘要，AI 自动提取「研究问题 / 核心方法 / 主要结论 / 研究创新」四大要素（需自备 API Key）")
    with st.expander("🔑 AI 设置", expanded=True):
        base_url, model, api_key = ui.ai_settings("abstract")
    abstract = st.text_area("粘贴文献摘要", height=160,
                            placeholder="本文基于……，采用……方法，利用……数据，考察了……。结果表明……。本研究的边际贡献在于……")
    if st.button("🤖 AI 拆解四大要素", type="primary"):
        if not api_key.strip():
            st.warning("请先在上方「AI 设置」中输入你的 API Key。")
        elif not base_url.strip() or not model.strip():
            st.warning("请完整填写 Base URL 和模型名。")
        elif not abstract.strip():
            st.warning("请先粘贴文献摘要。")
        else:
            try:
                st.write_stream(llm_client.chat_stream(base_url, api_key, model, llm_client.ABSTRACT_SYSTEM, abstract))
            except Exception as exc:  # noqa: BLE001
                st.error(f"调用失败：{exc}")
    st.divider()
    with st.expander("🔧 离线规则拆解（无需 AI，效果较基础）"):
        abstract_offline = st.text_area("粘贴文献摘要", height=150, key="abstract_offline",
                                        placeholder="本文基于……，采用……方法，利用……数据，考察了……。结果表明……。本研究的边际贡献在于……")
        if st.button("🔬 规则拆解"):
            if not abstract_offline.strip():
                st.warning("请先粘贴文献摘要。")
            else:
                r = lit.extract_abstract(abstract_offline)
                for aspect in ["研究问题", "核心方法", "主要结论", "研究创新"]:
                    sents = r.get(aspect, [])
                    st.markdown(f"**{aspect}**")
                    if sents:
                        for s in sents:
                            st.markdown(f"- {s}")
                    else:
                        st.caption("（未识别到相关内容）")
                    st.write("")

with tab2:
    st.markdown("### 科研笔记模板库")
    tpl_name = st.selectbox("选择笔记模板", list(lit.NOTE_TEMPLATES.keys()))
    content = lit.NOTE_TEMPLATES[tpl_name]
    st.code(content, language="markdown")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ 下载 Markdown", data=content.encode("utf-8"),
                           file_name=f"{tpl_name}.md", mime="text/markdown")
    with c2:
        st.caption("支持在线编辑后导出，可直接复制到 Typora / Obsidian 使用。")

with tab3:
    st.markdown("### 期刊分区查询")
    st.caption("内置常见经管社科期刊参考数据（中科院分区/影响因子，请以官方最新发布为准）")
    kw = st.text_input("输入期刊名关键词", placeholder="如：经济研究 / Journal of Finance")
    field_filter = st.multiselect("领域筛选", lit.journal_fields())
    results = lit.search_journal(kw)
    if field_filter:
        results = [r for r in results if r["field"] in field_filter]
    if results:
        st.dataframe(
            [{"期刊": r["name"], "领域": r["field"], "中科院分区": r["zone"],
              "影响因子(参考)": r["if"], "备注": r["note"]} for r in results],
            width="stretch",
        )
        st.caption("数据为公开常识性参考，分区与影响因子每年更新，投稿前请以中科院文献情报中心 / Clarivate 官方为准。")
    else:
        st.info("未找到匹配期刊，可尝试更宽泛的关键词。")
