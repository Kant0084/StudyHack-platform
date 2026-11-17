"""数据预处理工具 —— 去重 / 缺失值 / 长宽表 / 标准化 / 归一化，导出 Excel。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from core import auth_ui
from core import audit_service

from core.ui import upload_excel, download_bytes
from core import preprocessing_service, io_utils

st.set_page_config(page_title="数据预处理", page_icon="🧹", layout="wide")

auth_ui.render_auth_sidebar()
auth_ui.require_login()

st.title("🧹 数据预处理工具")
st.caption("Excel 去重、缺失值、长宽表转换、标准化 / 归一化，处理后可导出或跳转分析")

df, fname = upload_excel(key="preprocess_upload")

if df is not None:
    audit_service.log(
        audit_service.current_user(st.session_state), "数据预处理", "上传文件",
        f"文件名={fname}; 行数={df.shape[0]}; 列数={df.shape[1]}",
    )
    st.markdown("### 选择预处理操作")
    op = st.radio(
        "操作类型",
        ["去重", "缺失值处理", "宽表转长表", "长表转宽表", "标准化 / 归一化", "格式统一"],
        horizontal=True,
    )

    result_df = None

    if op == "去重":
        subset = st.multiselect("去重依据列（留空=整行完全重复才去重）", df.columns.tolist())
        keep = st.radio("保留策略", ["保留第一条", "保留最后一条"], horizontal=True)
        if st.button("执行去重", type="primary"):
            result_df = preprocessing_service.deduplicate(df, subset=subset or None, keep="first" if keep.startswith("保留第一") else "last")

    elif op == "缺失值处理":
        strategy = st.radio("处理策略", ["删除含缺失行", "均值填充", "中位数填充", "众数填充"], horizontal=True)
        cols = st.multiselect("作用列（留空=全部列）", df.columns.tolist())
        if st.button("执行缺失值处理", type="primary"):
            s_map = {"删除含缺失行": "drop", "均值填充": "mean", "中位数填充": "median", "众数填充": "mode"}
            result_df = preprocessing_service.handle_missing(df, strategy=s_map[strategy], cols=cols or None)

    elif op == "宽表转长表":
        id_vars = st.multiselect("保留的标识列（ID 变量）", df.columns.tolist())
        value_vars = st.multiselect("转换的数值列", [c for c in df.columns if c not in id_vars])
        var_name = st.text_input("新「变量名」列名", value="变量")
        value_name = st.text_input("新「取值」列名", value="取值")
        if st.button("执行宽转长", type="primary"):
            if not id_vars or not value_vars:
                st.warning("请同时选择标识列与数值列。")
            else:
                result_df = preprocessing_service.wide_to_long(df, id_vars, value_vars, var_name, value_name)

    elif op == "长表转宽表":
        index = st.multiselect("行标识列（index）", df.columns.tolist())
        columns = st.selectbox("转为列名的变量", [c for c in df.columns if c not in index])
        values = st.selectbox("取值列", [c for c in df.columns if c not in index and c != columns])
        aggfunc = st.selectbox("聚合方式", ["均值", "求和", "中位数", "计数"])
        if st.button("执行长转宽", type="primary"):
            if not index or not columns or not values:
                st.warning("请完整选择行标识、列名变量、取值列。")
            else:
                agg_map = {"均值": "mean", "求和": "sum", "中位数": "median", "计数": "count"}
                result_df = preprocessing_service.long_to_wide(df, index, columns, values, aggfunc=agg_map[aggfunc])

    elif op == "标准化 / 归一化":
        method = st.radio("方法", ["z-score 标准化", "min-max 归一化"], horizontal=True)
        cols = st.multiselect("作用列（留空=全部数值列）", df.select_dtypes(include=["number"]).columns.tolist())
        if st.button("执行标准化/归一化", type="primary"):
            if method == "z-score 标准化":
                result_df = preprocessing_service.standardize(df, cols=cols or None)
            else:
                result_df = preprocessing_service.normalize(df, cols=cols or None)

    elif op == "格式统一":
        st.write("将统一：列名去首尾空白、数值列强制转为数值类型。")
        if st.button("执行格式统一", type="primary"):
            result_df = preprocessing_service.unify_format(df)

    # ---- 结果展示与导出 ----
    if result_df is not None:
        st.success(f"处理完成：{result_df.shape[0]} 行 × {result_df.shape[1]} 列")
        st.dataframe(result_df.head(200), width="stretch")
        st.markdown("### 导出 / 继续分析")
        base = Path(fname or "数据").stem
        c1, c2 = st.columns(2)
        with c1:
            download_bytes(io_utils.to_excel_bytes(result_df), f"{base}_处理后.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "⬇️ 下载 Excel")
        with c2:
            download_bytes(io_utils.to_csv_bytes(result_df), f"{base}_处理后.csv", "text/csv", "⬇️ 下载 CSV")

        st.divider()
        st.markdown("**一键跳转分析模块（数据将带入目标页）**")
        j1, j2 = st.columns(2)
        with j1:
            if st.button("→ 跳转到经管实证分析", width="stretch"):
                st.session_state["incoming_df"] = result_df
                st.switch_page("pages/2_📈_经管实证分析.py")
        with j2:
            if st.button("→ 跳转到问卷智能分析", width="stretch"):
                st.session_state["incoming_df"] = result_df
                st.switch_page("pages/1_📊_问卷智能分析.py")
else:
    st.info("👆 请先上传 Excel / CSV 文件。")
    st.markdown(
        """
        **支持的操作：**
        - Excel 批量去重（指定列 / 整行）
        - 缺失值批量处理（删除 / 均值 / 中位数 / 众数填充）
        - 长宽表转换（宽转长 / 长转宽）
        - 变量一键标准化（z-score）/ 归一化（min-max）
        - 数据格式批量统一
        """
    )
