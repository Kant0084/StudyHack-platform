"""经管实证分析 —— 预处理 / 描述统计 / 相关 / OLS 基准回归 / 分组回归。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from core.ui import upload_excel, download_docx
from core import regression_service, report_service

st.set_page_config(page_title="经管实证分析", page_icon="📈", layout="wide")

st.title("📈 经管实证分析")
st.caption("面板 / 截面数据，预处理 → 描述 → 相关 → OLS 基准回归，对标 Stata 17 reg（误差 ≤0.001）")

with st.expander("📄 报告信息（可选）"):
    report_title = st.text_input("报告标题", value="经管实证分析报告")
    report_author = st.text_input("作者姓名", value="")

df, fname = upload_excel(key="reg_upload")

# 支持从「数据预处理」模块跳转带入数据
if df is None and "incoming_df" in st.session_state:
    df = st.session_state["incoming_df"]
    fname = "预处理后数据"
    st.info("📥 已载入「数据预处理」模块处理后的数据")

if df is not None:
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    all_cols = df.columns.tolist()

    if len(num_cols) < 2:
        st.error("数值列不足 2 个，无法进行回归分析。请确认数据已正确读取。")
    else:
        st.markdown("### ① 选择变量")
        c1, c2 = st.columns(2)
        with c1:
            dep = st.selectbox("因变量（被解释变量）", options=num_cols)
        with c2:
            indep = st.multiselect("自变量（解释变量，可多选）", options=[c for c in num_cols if c != dep])

        st.markdown("### ② 进阶设置（可选，折叠）")
        with st.expander("固定效应 / 聚类 / 预处理 / 异质性", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                fe = st.multiselect("固定效应变量（个体/年份等）", options=[c for c in all_cols if c not in indep and c != dep])
                cluster = st.selectbox("聚类变量（可选）", options=["（不聚类）"] + [c for c in all_cols if c != dep])
            with c2:
                missing = st.selectbox("缺失值处理", options=["删除缺失样本", "均值填充", "中位数填充", "不处理"], index=0)
                winsor = st.selectbox("连续变量缩尾", options=["不缩尾", "1%/99% 缩尾", "5%/95% 缩尾"], index=1)
                standardize = st.checkbox("变量标准化（z-score）", value=False)
            group_col = st.selectbox("分组回归变量（异质性分析，可选）", options=["（不做分组回归）"] + [c for c in all_cols if c != dep])

        missing_map = {"删除缺失样本": "drop", "均值填充": "mean", "中位数填充": "median", "不处理": "none"}
        winsor_map = {"不缩尾": None, "1%/99% 缩尾": 0.01, "5%/95% 缩尾": 0.05}
        cluster_arg = None if cluster == "（不聚类）" else cluster
        group_arg = None if group_col == "（不做分组回归）" else group_col

        st.markdown("### ③ 开始分析")
        if st.button("🚀 开始回归分析", type="primary", width="stretch"):
            if not indep:
                st.warning("请至少选择 1 个自变量。")
            else:
                with st.spinner("正在运行 OLS 回归……"):
                    try:
                        result = regression_service.analyze_regression(
                            df, dep, indep,
                            fe=fe or None, cluster=cluster_arg,
                            missing=missing_map[missing],
                            winsor_lower=winsor_map[winsor],
                            standardize=standardize,
                            group_col=group_arg,
                        )
                        st.session_state["reg_result"] = result
                        st.session_state["reg_report_path"] = None
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"回归失败：{exc}")
                        st.info("请检查：① 因变量/自变量是否为数值；② 是否存在全空或常量列；③ 分类变量请勿选入自变量（需先转虚拟变量）。")

        result = st.session_state.get("reg_result")
        if result:
            st.markdown("---")
            st.markdown("### 📋 回归结果")

            tabs = st.tabs(["📈 描述统计", "🔗 相关性", "🎯 基准回归", "🧩 分组回归"])

            with tabs[0]:
                st.dataframe(result["descriptives"], width="stretch")
                st.caption(f"样本量：{result['n_after']}（原始 {result['n_before']}）")

            with tabs[1]:
                corr = result.get("correlation")
                if corr is not None:
                    st.dataframe(corr["labeled"], width="stretch")
                    st.caption("* p<0.05, ** p<0.01, *** p<0.001")

            with tabs[2]:
                base = result["baseline"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("样本量 N", base["nobs"])
                c2.metric("R²", f"{base['r2']:.3f}")
                c3.metric("调整 R²", f"{base['adj_r2']:.3f}")
                c4.metric("F 值", f"{base['f_stat']:.2f}" if base.get("f_stat") is not None else "—")
                st.dataframe(base["tidy"], width="stretch")
                if base.get("interpret"):
                    st.success(base["interpret"])
                if base.get("warnings"):
                    for w in base["warnings"]:
                        st.warning(w)
                st.caption("注：回归结果对标 Stata 17 reg；固定效应以虚拟变量实现。")

            with tabs[3]:
                grouped = result.get("grouped")
                if grouped:
                    st.write(f"分组变量：{grouped['group_col']}")
                    for gr in grouped["results"]:
                        if "error" in gr:
                            st.warning(f"分组「{gr['group']}」：{gr['error']}")
                        else:
                            st.markdown(f"**分组：{gr['group']}**（N={gr['nobs']}，R²={gr['r2']:.3f}）")
                            st.dataframe(gr["tidy"], width="stretch")
                else:
                    st.info("未选择分组变量，如需异质性分析请在「进阶设置」中选择。")

            # ---- 生成报告 ----
            st.markdown("---")
            st.markdown("### 📄 生成 Word 报告")
            if st.button("📝 生成并下载 Word 报告", type="primary"):
                with st.spinner("正在生成实证分析 Word 报告……"):
                    out_path = Path("assets") / f"实证分析报告_{fname or 'result'}.docx".replace(" ", "_")
                    p = report_service.build_regression_report(result, report_title, report_author, str(out_path))
                    st.session_state["reg_report_path"] = str(p)
            rp = st.session_state.get("reg_report_path")
            if rp:
                download_docx(Path(rp))
                st.success("报告已生成：三线表 + 标准化学术解读，可直接复制进论文。")
else:
    st.info("👆 请先上传面板 / 截面数据 Excel（首行为变量名，数值型变量）。")
    st.markdown(
        """
        **支持的分析功能：**
        - 数据预处理：缺失值处理、1%/5% 缩尾、标准化（自动执行）
        - 描述性统计：观测值 / 均值 / 标准差 / 最小 / 中位数 / 最大
        - 相关性分析：Pearson 相关系数矩阵
        - 基准回归：OLS 多元线性回归（系数 / 标准误 / t / P / R² / 调整 R² / F）
        - 进阶：固定效应、聚类标准误、分组回归（异质性分析）
        """
    )
