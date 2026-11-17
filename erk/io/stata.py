"""Stata 对接：生成 .do 脚本 → 批处理运行 → 回读结果。

技术方案（融合 stata-mcp 与 StatsPAI 的工程实践）：
  - 批处理运行：Windows `stata /e do script.do`、Unix `stata -b do script.do`
    （subprocess），而非 PyStata 进程内嵌，与 ERK「生成脚本 → 静默运行 → 回读」
    链最契合，且不引入 pystata 硬依赖。
  - 结果回读：.do 脚本用 `file write` 把系数/标准误/拟合统计写为纯文本
    `_erk_result.txt`，Python 端解析 —— 这是本项目（stata-mcp）缺失、ERK 自研
    的核心增量。
  - 全精度输出：系数/标准误用 %12.10f，避免浮点误差破坏与内置引擎的交叉验证。

风险说明：
  - 固定效应以 i.varname 虚拟变量实现，与 reghdfe 在自由度/口径上可能有差异；
  - p 值与置信区间在回读时用正态近似计算（见 EngineEstimate.to_regression_result），
    精确口径以 Stata 输出为准，正式报告建议核对原始 .log。
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from erk.io.base import EngineAdapter, EngineEstimate, STATUS_OK, STATUS_UNAVAILABLE

RESULT_FILENAME = "_erk_result.txt"
DATA_FILENAME = "_erk_data.csv"
SCRIPT_FILENAME = "_erk_script.do"

# 版本(edition) → Windows 可执行文件名候选
_WIN_EXE = {
    "mp": ["StataMP-64.exe", "StataMP.exe"],
    "se": ["StataSE-64.exe", "StataSE.exe"],
    "be": ["Stata-64.exe", "Stata.exe"],
}


def find_stata(exe_dir: str = "", edition: str = "mp") -> str | None:
    """跨平台定位 Stata 可执行文件，返回路径或 None。

    借鉴 stata-mcp 的 find_stata_executable：按 edition 映射可执行名，
    覆盖 Windows / macOS(.app) / Linux 三种布局；exe_dir 留空时自动探测常见路径。
    """
    if exe_dir:
        return _find_in_dir(Path(exe_dir), edition)

    # 自动探测常见安装路径（Windows）
    import os

    candidates = [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")),
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")),
    ]
    for base in candidates:
        for ver in ("StataNow19", "StataNow18", "Stata19", "Stata18", "Stata17", "Stata16"):
            p = _find_in_dir(base / ver, edition)
            if p:
                return p
    # macOS / Linux 兜底：直接找可执行名
    for name in _WIN_EXE.get(edition, []) + ["stata-mp", "stata-se", "stata"]:
        found = shutil.which(name)
        if found:
            return found
    return None


def _find_in_dir(stata_dir: Path, edition: str) -> str | None:
    """在给定安装目录内按 edition 查找可执行文件。"""
    if not stata_dir.exists():
        return None
    for name in _WIN_EXE.get(edition, []):
        p = stata_dir / name
        if p.exists():
            return str(p)
    # macOS: Stata 是 .app 包
    app = stata_dir / "Stata.app" / "Contents" / "MacOS"
    for name in ("stata-mp", "stata-se", "stata"):
        p = app / name
        if p.exists():
            return str(p)
    return None


class StataAdapter(EngineAdapter):
    """Stata 适配器：把回归任务翻译为 .do 脚本并批处理执行。"""

    engine_name = "stata"

    def __init__(self, exe_path: str = "", edition: str = "mp"):
        self.exe_path = exe_path or find_stata(edition=edition) or ""
        self.edition = edition

    def available(self) -> bool:
        return bool(self.exe_path) and Path(self.exe_path).exists()

    # ---- 脚本生成（纯函数，可独立测试） ----

    def generate_script(
        self,
        dep: str,
        indep: list[str],
        fe: list[str] | None = None,
        cluster: str | None = None,
        data_filename: str = DATA_FILENAME,
        result_filename: str = RESULT_FILENAME,
    ) -> str:
        """生成 .do 脚本。

        注意：变量名须为 Stata 合法标识符（英文、不以数字开头、无空格）。
        中文/特殊变量名需先在 Python 端重命名为合法名称并建立映射（Roadmap）。
        """
        fe = fe or []
        lines = [
            "* ============================================================",
            "* ERK 自动生成 · 基准回归 (OLS)",
            f"* 因变量: {dep}",
            f"* 自变量: {' '.join(indep)}",
            f"* 固定效应: {' '.join(fe) if fe else '(无)'}",
            f"* 聚类: {cluster or '(无)'}",
            "* 生成方式: ERK io/stata.py (可复现)",
            "* ============================================================",
            "",
            f'import delimited "{data_filename}", clear varnames(1)',
            "",
        ]

        rhs = " ".join(indep)
        if fe:
            rhs += " " + " ".join(f"i.{c}" for c in fe)
        cmd = f"regress {dep} {rhs}"
        if cluster:
            cmd += f", vce(cluster {cluster})"
        lines.append(cmd)
        lines.append("")

        # 用 file write 输出纯文本结果，供 Python 端解析
        lines.append(f'file open fh using "{result_filename}", write replace')
        lines.append('file write fh "r2=" %12.10f (e(r2)) _n')
        lines.append('file write fh "adj_r2=" %12.10f (e(r2_a)) _n')
        lines.append('file write fh "N=" %10.0f (e(N)) _n')
        for v in indep:
            lines.append(f'file write fh "{v}=" %12.10f (_b[{v}]) "," %12.10f (_se[{v}]) _n')
        lines.append("file close fh")
        lines.append("")
        return "\n".join(lines)

    # ---- 解析 ----

    @staticmethod
    def parse_result(text: str) -> EngineEstimate:
        """解析 _erk_result.txt，返回 EngineEstimate（仅含 coef/se/nobs/r2）。

        p 值/置信区间在 to_regression_result 中做正态近似补充。
        """
        r2 = adj_r2 = None
        nobs = None
        coef: dict = {}
        se: dict = {}
        for raw in text.splitlines():
            line = raw.strip()
            if not line or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key == "r2":
                r2 = float(val)
            elif key == "adj_r2":
                adj_r2 = float(val)
            elif key == "N":
                nobs = int(float(val))
            elif "," in val:
                parts = val.split(",")
                if len(parts) >= 2:
                    coef[key] = float(parts[0])
                    se[key] = float(parts[1])
        return EngineEstimate(
            engine="stata",
            status=STATUS_OK,
            coef=coef,
            se=se,
            nobs=nobs,
            r2=r2,
            adj_r2=adj_r2,
        )

    # ---- 执行 ----

    def execute_script(
        self,
        script: str,
        df: pd.DataFrame,
        fe: list[str] | None = None,
        cluster: str | None = None,
        workdir: str | None = None,
    ) -> EngineEstimate:
        """执行自定义 .do 脚本（脚本负责 file write 结果到 _erk_result.txt），回读并归一。

        供 OLS 与内生性方法（DID/IV 等）复用同一套「导出数据 → 批处理 → 解析」流程。
        """
        work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="erk_stata_"))
        work.mkdir(parents=True, exist_ok=True)

        # 导出数据（固定效应/聚类变量若非数值，先编码为数值；
        # 注意 pandas 2.x 字符串列为 StringDtype 而非 object）
        df_export = df.copy()
        for c in set((fe or []) + ([cluster] if cluster else [])):
            if c in df_export.columns and not pd.api.types.is_numeric_dtype(df_export[c]):
                df_export[c] = pd.factorize(df_export[c])[0]
        df_export.to_csv(work / DATA_FILENAME, index=False)

        (work / SCRIPT_FILENAME).write_text(script, encoding="utf-8")

        # 批处理运行：Windows 用 /e，Unix 用 -b（工作目录=脚本目录，产出 .log）
        batch_flag = "/e" if platform.system() == "Windows" else "-b"
        proc = subprocess.run(
            [self.exe_path, batch_flag, "do", SCRIPT_FILENAME],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=300,
        )

        result_path = work / RESULT_FILENAME
        if not result_path.exists():
            return EngineEstimate(
                engine="stata",
                status="error",
                message=(
                    f"Stata 未产出结果文件，返回码 {proc.returncode}。"
                    f"日志见 {work / Path(SCRIPT_FILENAME).with_suffix('.log')}"
                ),
            )
        return self.parse_result(result_path.read_text(encoding="utf-8", errors="replace"))

    def _run_impl(
        self,
        df: pd.DataFrame,
        dep: str,
        indep: list[str],
        fe: list[str] | None,
        cluster: str | None,
        workdir: str | None,
    ) -> EngineEstimate:
        script = self.generate_script(dep, indep, fe=fe, cluster=cluster)
        est = self.execute_script(script, df, fe=fe, cluster=cluster, workdir=workdir)
        est.dep = dep
        return est
