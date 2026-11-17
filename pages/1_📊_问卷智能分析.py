"""问卷智能分析 —— 信度 / 效度 / 描述统计 / 相关 / 频数，一键生成 Word 报告。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from core import auth_ui

from core.ui import upload_excel, download_docx, pie_chart, bar_chart
from core import survey_service, report_service

st.set_page_config(page_title="问卷智能分析", page_icon="📊", layout="wide")

auth_ui.require_login()

st.title("📊 问卷智能分析")
st.caption("支持问卷星 / 腾讯问卷原生导出 Excel，自动识别量表题项，对标 SPSS 26（误差 ≤0.001）")

# 作者与标题信息（供报告）
with st.expander("📄 报告信息（可选，写入 Word 报告）"):
    report_title = st.text_input("论文/报告标题", value="问卷分析报告")
    report_author = st.text_input("作者姓名", value="")

df, fname = upload_excel(key="survey_upload")

# 支持从「数据预处理」模块跳转带入数据
if df is None and "incoming_df" in st.session_state:
    df = st.session_state["incoming_df"]
    fname = "预处理后数据"
    st.info("📥 已载入「数据预处理」模块处理后的数据")

if df is not None:
    # 列识别预览
    preview = survey_service.list_survey_columns(df)
    scale_cols = preview["scale_cols"]
    all_vars = [v["name"] for v in preview["variables"]]

    st.markdown("### ① 题型自动识别结果")
    with st.expander("查看识别详情（可手动调整量表列）", expanded=True):
        if preview["type_dist"]:
            st.write("题型分布：", "、".join(f"{k} {v} 个" for k, v in preview["type_dist"].items()))
        selected_scale = st.multiselect(
            "选择用于信效度/相关分析的量表题列",
            options=all_vars,
            default=scale_cols,
        )
        st.caption(f"样本量：{preview['n_samples']} 份")

    st.markdown("### ② 分析参数")
    c1, c2 = st.columns([1, 2])
    with c1:
        n_factors = st.selectbox("因子数", options=["自动（特征值>1）", "1", "2", "3", "4", "5"], index=0)

    n_factors_arg = None if n_factors.startswith("自动") else int(n_factors)

    st.markdown("### ③ 开始分析")
    if st.button("🚀 开始分析", type="primary", width="stretch"):
        if not selected_scale:
            st.warning("请至少选择 1 个量表题列进行分析。")
        else:
            with st.spinner("正在计算（信度 / 效度 / 描述 / 相关 / 频数）……"):
                try:
                    result = survey_service.analyze_survey(df, scale_cols=selected_scale, n_factors=n_factors_arg)
                    st.session_state["survey_result"] = result
                    st.session_state["survey_report_path"] = None
                except Exception as exc:  # noqa: BLE001
                    st.error(f"分析失败：{exc}")
                    st.info("请检查：① 量表列为数值（1-5 等 Likert 分值）；② 无全空列；③ 数据无损坏。")

    # ---- 结果展示 ----
    result = st.session_state.get("survey_result")
    if result:
        st.markdown("---")
        st.markdown("### 📋 分析结果")

        tabs = st.tabs(["🔍 信度分析", "🎯 效度分析", "📈 描述统计", "🔗 相关性", "📊 频数分析"])

        with tabs[0]:
            rel = result.get("reliability")
            if rel:
                m1, m2, m3 = st.columns(3)
                m1.metric("Cronbach's α", f"{rel['alpha']:.3f}")
                m2.metric("题项数", rel["n_items"])
                m3.metric("有效样本", rel["n_samples"])
                st.info(rel["interpret"])
                st.dataframe(rel["item_table"], width="stretch")
                if rel.get("warnings"):
                    for w in rel["warnings"]:
                        st.warning(w)
            else:
                st.warning("量表题少于 2 个，无法计算信度。")

        with tabs[1]:
            val = result.get("validity")
            if val:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("KMO", f"{val['kmo']:.3f}")
                c2.metric("Bartlett χ²", f"{val['bartlett_chi2']:.2f}")
                c3.metric("Bartlett p", f"{val['bartlett_p']:.4f}")
                c4.metric("累计方差解释率", f"{val['total_variance']:.1%}")
                st.info(val["interpret"])
                st.markdown("**因子载荷矩阵**")
                st.dataframe(val["loading_table"], width="stretch")
                st.markdown("**方差解释率**")
                st.dataframe(val["variance_table"], width="stretch")
            else:
                st.warning("量表题少于 3 个，无法进行效度/因子分析。")

        with tabs[2]:
            desc = result.get("descriptives")
            if desc is not None:
                st.dataframe(desc, width="stretch")
            else:
                st.warning("无可分析的量表题。")

        with tabs[3]:
            corr = result.get("correlation")
            if corr is not None:
                st.dataframe(corr["labeled"], width="stretch")
                st.caption("* p<0.05, ** p<0.01, *** p<0.001")
            else:
                st.warning("量表题少于 2 个，无法计算相关矩阵。")

        with tabs[4]:
            freq = result.get("frequency")
            if freq and freq["single_cols"]:
                freq_col = st.selectbox("选择单选题查看频数", freq["single_cols"])
                t = freq["tables"].get(freq_col)
                if t is not None:
                    st.dataframe(t, width="stretch")
                    chart_type = st.radio("图表类型", ["柱状图", "饼图"], horizontal=True)
                    counts = t["count"]
                    if chart_type == "饼图":
                        st.pyplot(pie_chart(counts, title=freq_col))
                    else:
                        st.pyplot(bar_chart(counts, title=freq_col))
            else:
                st.warning("未识别到单选题（或单选题不足）。")

        # ---- 生成报告 ----
        st.markdown("---")
        st.markdown("### 📄 生成 Word 报告")
        if st.button("📝 生成并下载 Word 报告", type="primary"):
            with st.spinner("正在生成符合学术规范的 Word 报告……"):
                out_path = Path("assets") / f"问卷分析报告_{fname or 'result'}.docx".replace(" ", "_")
                p = report_service.build_survey_report(result, report_title, report_author, str(out_path))
                st.session_state["survey_report_path"] = str(p)
        rp = st.session_state.get("survey_report_path")
        if rp:
            download_docx(Path(rp))
            st.success("报告已生成：三线表 + 标准化学术解读，可直接复制进论文。")
else:
    st.info("👆 请先上传问卷星 / 腾讯问卷导出的 Excel 文件（题目作为表头）。")
    st.markdown(
        """
        **支持的分析功能：**
        - 信度分析：克朗巴赫 α、CITC、删除后 α
        - 效度分析：KMO、Bartlett 球形检验、因子载荷、累计方差解释率
        - 描述性统计：均值 / 标准差 / 最小 / 最大
        - 相关性分析：Pearson 相关系数矩阵（*p<0.05）
        - 频数分析：单选题频数 + 柱状图 / 饼图
        """
    )
