"""StudyHack 科研效率平台 · 首页。

本科经管社科一站式科研效率平台 —— 零代码、全中文、上传即出结果、输出直接复用。
"""

import streamlit as st

st.set_page_config(
    page_title="StudyHack · 科研效率平台",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 隐私承诺说明（sidebar 顶部）
with st.sidebar:
    st.markdown("### 🎓 StudyHack")
    st.caption("本科经管社科一站式科研效率平台")
    st.divider()
    st.markdown("##### 🔒 隐私承诺")
    st.caption("数据仅临时处理，10 分钟内自动清除，不上传、不存储。")

# ---- 首屏 ----
st.markdown(
    """
    <div style="padding: 0.5rem 0 0.5rem 0;">
      <h1 style="font-size: 2.4rem; margin-bottom: 0.2rem;">🎓 StudyHack 科研效率平台</h1>
      <p style="font-size: 1.15rem; color: #4b5563; margin-top: 0;">
        面向本科经管社科学生的一站式科研助手 —— 零代码、全中文、上传即出结果、输出直接复用。
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ---- 核心工具入口（3 大核心） ----
st.markdown("### 🚀 核心工具 · 一键开始")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        """
        <div style="background:#F0F7F4; border-radius:12px; padding:1.1rem; border:1px solid #D7E7E1;">
          <h4 style="margin:0 0 0.4rem 0;">📊 问卷智能分析</h4>
          <p style="color:#4b5563; font-size:0.92rem; margin:0 0 0.8rem 0;">问卷星/腾讯问卷原生 Excel 直传，信效度 + 描述 + 相关一键出报告。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_📊_问卷智能分析.py", label="进入问卷分析 →", icon="📊")
with c2:
    st.markdown(
        """
        <div style="background:#EFF4FA; border-radius:12px; padding:1.1rem; border:1px solid #D7E2F0;">
          <h4 style="margin:0 0 0.4rem 0;">📈 经管实证分析</h4>
          <p style="color:#4b5563; font-size:0.92rem; margin:0 0 0.8rem 0;">面板/截面数据，预处理 + 描述 + OLS 基准回归，对标 Stata 17。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_📈_经管实证分析.py", label="进入实证分析 →", icon="📈")
with c3:
    st.markdown(
        """
        <div style="background:#F5F3EE; border-radius:12px; padding:1.1rem; border:1px solid #E8E2D5;">
          <h4 style="margin:0 0 0.4rem 0;">🧹 数据预处理</h4>
          <p style="color:#4b5563; font-size:0.92rem; margin:0 0 0.8rem 0;">去重、缺失值、长宽表、标准化，处理完直接跳转分析。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_🧹_数据预处理.py", label="进入预处理 →", icon="🧹")

st.markdown("---")

# ---- 四大板块总览 ----
st.markdown("### 🧭 全链路工具箱")
col1, col2 = st.columns(2)

with col1:
    st.markdown("##### 📊 板块一 · 数据实证工具箱")
    st.markdown("- 问卷智能分析：信度 / 效度 / 描述 / 相关 / 频数")
    st.markdown("- 经管实证分析：预处理 / 描述 / 相关 / OLS 回归 / 分组回归")
    st.markdown("- 数据预处理：去重 / 缺失值 / 长宽表 / 标准化")

with col2:
    st.markdown("##### 📝 板块二 · 学术写作辅助")
    st.markdown("- 三线表生成器（Word/PNG）")
    st.markdown("- 参考文献转换（GB/T 7714 / APA 7th / MLA 9th）")
    st.markdown("- 学术润色 + 论文模板 + 转 LaTeX")

col3, col4 = st.columns(2)
with col3:
    st.markdown("##### 📖 板块三 · 文献学习辅助")
    st.markdown("- 文献摘要拆解（问题/方法/结论/创新点）")
    st.markdown("- 科研笔记模板库")
    st.markdown("- 期刊分区查询")

with col4:
    st.markdown("##### 🗂️ 板块四 · 科研资源导航")
    st.markdown("- 数据库 / 工具 / 教程分类聚合")
    st.markdown("- 标签筛选 + 关键词搜索")

st.markdown("---")

# ---- 全部工具直达 ----
st.markdown("### 🧰 全部工具直达")
link_rows = [
    ["📊 问卷智能分析", "pages/1_📊_问卷智能分析.py", "信度/效度/描述/相关/频数"],
    ["📈 经管实证分析", "pages/2_📈_经管实证分析.py", "预处理/描述/OLS回归/分组回归"],
    ["🧹 数据预处理", "pages/3_🧹_数据预处理.py", "去重/缺失值/长宽表/标准化"],
    ["📝 三线表生成", "pages/4_📝_三线表生成.py", "GB/T 7714 标准三线表"],
    ["📚 参考文献转换", "pages/5_📚_参考文献转换.py", "GB/T 7714/APA/MLA"],
    ["✍️ 学术润色与模板", "pages/6_✍️_学术润色.py", "润色/模板/转LaTeX"],
    ["📖 文献学习辅助", "pages/7_📖_文献学习辅助.py", "摘要拆解/笔记/期刊分区"],
    ["🗂️ 资源导航", "pages/8_🗂️_资源导航.py", "数据库/工具/教程聚合"],
]
for i in range(0, len(link_rows), 4):
    cols = st.columns(4)
    for j, (label, path, desc) in enumerate(link_rows[i : i + 4]):
        with cols[j]:
            st.page_link(path, label=label, icon=label.split()[0])
            st.caption(desc)

st.markdown("---")

# ---- 三步用法 ----
st.markdown("### ⚡ 三步上手")
step1, step2, step3 = st.columns(3)
step1.markdown("**① 上传数据**\n\n拖拽 Excel，自动识别变量与题型")
step2.markdown("**② 选择分析**\n\n勾选功能与参数，默认学术常用标准")
step3.markdown("**③ 下载报告**\n\n三线表 + 学术解读，复制进论文即用")

st.markdown("---")
st.caption(
    "核心计算对标 SPSS 26 / Stata 17 ｜ 数据仅临时处理，10 分钟内自动清除"
)
