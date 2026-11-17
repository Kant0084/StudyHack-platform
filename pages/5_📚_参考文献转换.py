"""参考文献格式转换 —— GB/T 7714-2015 / APA 7th / MLA 9th。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from core import auth_ui
from core import audit_service

from core import reference_service as ref

st.set_page_config(page_title="参考文献转换", page_icon="📚", layout="wide")

auth_ui.render_auth_sidebar()
auth_ui.require_login()

st.title("📚 参考文献格式转换器")
st.caption("填写文献题录，一键切换 GB/T 7714-2015（国标）/ APA 7th / MLA 9th，支持中英文文献")

ref_type = st.selectbox("① 文献类型", list(ref.TYPE_OPTIONS.keys()))
rt = ref.TYPE_OPTIONS[ref_type]

st.markdown("### ② 填写题录信息")
c1, c2 = st.columns(2)
with c1:
    authors = st.text_input("作者（逗号/分号分隔，如：张三, 李四 或 Zhang San, Li Si）", value="")
    title = st.text_input("题名 / 标题", value="")
    source = st.text_input("期刊名 / 出版社 / 学校（按类型）", value="")
with c2:
    year = st.text_input("年份", value="")
    volume = st.text_input("卷（期刊）", value="")
    issue = st.text_input("期（期刊）", value="")
    pages = st.text_input("页码", value="")

c3, c4 = st.columns(2)
with c3:
    doi = st.text_input("DOI（可选）", value="")
with c4:
    location = st.text_input("出版地 / 会议地点（书籍/学位论文/会议）", value="")
    degree = st.text_input("学位（学位论文，如「博士学位论文」）", value="")

st.markdown("### ③ 生成结果")
if st.button("🔄 生成三种格式", type="primary", width="stretch"):
    if not title.strip():
        st.warning("请至少填写「题名 / 标题」。")
    else:
        audit_service.log(
            audit_service.current_user(st.session_state), "参考文献转换", "题录信息",
            f"标题={title}; 作者={authors}; 年份={year}; 来源={source}; 卷={volume}; 期={issue}; 页码={pages}; DOI={doi}",
        )
        r = ref.format_reference(
            ref_type=rt, authors=authors, year=year, title=title, source=source,
            volume=volume, issue=issue, pages=pages, doi=doi, location=location, degree=degree,
        )
        st.session_state["ref_result"] = r

r = st.session_state.get("ref_result")
if r:
    styles = {
        "GB/T 7714-2015（国标）": "gbt",
        "APA 7th": "apa",
        "MLA 9th": "mla",
    }
    for label, key in styles.items():
        with st.container():
            st.markdown(f"**{label}**")
            st.code(r[key], language=None)
            st.download_button(
                f"📋 复制 {label}",
                data=r[key].encode("utf-8"),
                file_name=f"参考文献_{key}.txt",
                mime="text/plain",
                key=f"dl_{key}",
            )

    st.divider()
    st.caption("说明：作者不超过 3 人时全部列出，超过 3 人按各标准规则缩写（GB/T 7714 用「等」/「et al」）。")
