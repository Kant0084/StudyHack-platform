"""内生性工具箱执行层。

把 DID / IV 等内生性方法翻译为 Stata 脚本并执行，结果归一为
EngineEstimate（可 to_regression_result 转为统一契约，与 OLS 共享三线表渲染）。

原则（核心边界）：进阶计量计算交给专业软件（Stata），工具只做
「脚本生成 → 批处理 → 回读 → 标准化」，不重复造统计轮子。

风险说明：
  - DID 仅实现 2×2 基础设定；交错处理/多期 DID 需 Callaway-Sant'Anna 等
    现代估计量（见 templates/decision.py 的必查诊断，Roadmap 接入 reghdfe/csdid）。
  - IV 的弱工具检验（Olea-Pflueger 有效 F）需 ivreg2/weakiv 等包，当前
    只回读 2SLS 系数，正式报告须补充弱工具诊断。
"""

from __future__ import annotations

import pandas as pd

from erk.io.base import STATUS_UNAVAILABLE, EngineEstimate
from erk.io.stata import RESULT_FILENAME, StataAdapter


def _encode_binary(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """把二值变量编码为 0/1。

    编码规则：对非数值列，取去重类别并按字典序排序，字典序较小者为 0、
    较大者为 1。确定性排序消除了「首次出现顺序」导致处理组被误判为对照组的
    风险；若类别数不是 2，则抛出明确错误，绝不静默反转。

    注意：工具无法自动判断哪个类别是「处理组」。若处理组的字典序反而较小，
    会被编为 0。因此正式分析强烈建议用户先把处理组显式编码为 0/1 数值列
    （数值列原样返回，不做映射）。
    """
    if pd.api.types.is_numeric_dtype(df[col]):
        return df
    df = df.copy()
    cats = sorted({str(x) for x in df[col].dropna()})
    if len(cats) != 2:
        raise ValueError(
            f"变量 {col} 有 {len(cats)} 个类别 {cats}，二值编码仅支持恰好 2 个类别；"
            "请先把处理组显式编码为 0/1。"
        )
    mapping = {cats[0]: 0, cats[1]: 1}
    df[col] = df[col].astype(str).map(mapping).astype(int)
    return df


def _header(dep: str, method: str) -> list[str]:
    return [
        "* ============================================================",
        f"* ERK 自动生成 · {method}",
        f"* 因变量: {dep}",
        "* 生成方式: ERK stats/endogeneity.py (可复现)",
        "* ============================================================",
        "",
    ]


def _did_script(dep: str, treat: str, post: str, controls: list[str], cluster: str | None) -> str:
    """生成 2×2 DID 的 .do 脚本（核心估计量 = treat×post 交互项）。"""
    L = _header(dep, "双重差分 (DID 2x2)")
    L.append('import delimited "_erk_data.csv", clear varnames(1)')
    L.append("")
    L.append(f"gen treat_post = {treat} * {post}")
    L.append("")
    rhs = " ".join([treat, post, "treat_post"] + controls)
    cmd = f"regress {dep} {rhs}"
    if cluster:
        cmd += f", vce(cluster {cluster})"
    L.append(cmd)
    L.append("")
    L.append(f'file open fh using "{RESULT_FILENAME}", write replace')
    L.append('file write fh "r2=" %12.10f (e(r2)) _n')
    L.append('file write fh "N=" %10.0f (e(N)) _n')
    L.append('file write fh "treat_post=" %12.10f (_b[treat_post]) "," %12.10f (_se[treat_post]) _n')
    L.append("file close fh")
    L.append("")
    return "\n".join(L)


def _iv_script(dep: str, endog: str, instrument: str, controls: list[str]) -> str:
    """生成 2SLS 的 .do 脚本（核心估计量 = 内生变量系数）。"""
    L = _header(dep, "工具变量法 (2SLS)")
    L.append('import delimited "_erk_data.csv", clear varnames(1)')
    L.append("")
    rhs = " ".join(controls)
    cmd = f"ivregress 2sls {dep} ({endog} = {instrument}) {rhs}".rstrip()
    L.append(cmd)
    L.append("")
    L.append(f'file open fh using "{RESULT_FILENAME}", write replace')
    L.append('file write fh "r2=" %12.10f (e(r2)) _n')
    L.append('file write fh "N=" %10.0f (e(N)) _n')
    L.append(f'file write fh "{endog}=" %12.10f (_b[{endog}]) "," %12.10f (_se[{endog}]) _n')
    L.append("file close fh")
    L.append("")
    return "\n".join(L)


def run_did(
    df: pd.DataFrame,
    dep: str,
    treat: str,
    post: str,
    controls: list[str] | None = None,
    cluster: str | None = None,
    exe_path: str = "",
    workdir: str | None = None,
) -> EngineEstimate:
    """DID（2×2）估计，返回核心估计量 treat×post 的系数/标准误。

    返回的 EngineEstimate 中 coef 的 key 为 "treat_post"。
    """
    controls = controls or []

    # 列名校验：漏列时给出可读的错误，而不是让 Stata 报费解的 r(111)
    missing = _missing_columns(df, [dep, treat, post] + controls + ([cluster] if cluster else []))
    if missing:
        return _column_error("run_did", missing, list(df.columns))

    adapter = StataAdapter(exe_path=exe_path)
    if not adapter.available():
        return EngineEstimate(engine="stata", status=STATUS_UNAVAILABLE, message="Stata 未安装或未配置。")

    df = _encode_binary(_encode_binary(df.copy(), treat), post)
    script = _did_script(dep, treat, post, controls, cluster)
    est = adapter.execute_script(script, df, cluster=cluster, workdir=workdir)
    est.dep = dep
    return est


def run_iv(
    df: pd.DataFrame,
    dep: str,
    endog: str,
    instrument: str,
    controls: list[str] | None = None,
    exe_path: str = "",
    workdir: str | None = None,
) -> EngineEstimate:
    """IV（2SLS）估计，返回内生变量的系数/标准误。

    返回的 EngineEstimate 中 coef 的 key 为 endog。
    """
    controls = controls or []

    # 列名校验：漏列（尤其是 instrument 忘了放进 df）时给出可读错误
    missing = _missing_columns(df, [dep, endog, instrument] + controls)
    if missing:
        return _column_error("run_iv", missing, list(df.columns))

    adapter = StataAdapter(exe_path=exe_path)
    if not adapter.available():
        return EngineEstimate(engine="stata", status=STATUS_UNAVAILABLE, message="Stata 未安装或未配置。")

    script = _iv_script(dep, endog, instrument, controls)
    est = adapter.execute_script(script, df, workdir=workdir)
    est.dep = dep
    return est


def _missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c and c not in df.columns]


def _column_error(func: str, missing: list[str], available: list[str]) -> EngineEstimate:
    return EngineEstimate(
        engine="stata",
        status="error",
        message=(
            f"{func}: 数据中缺少列 {missing}。"
            f"现有列: {available}。请检查列名拼写，或把缺失的变量加进 DataFrame。"
        ),
    )
