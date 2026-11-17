"""R 语言对接。

技术方案（借鉴 StatsPAI 的 RscriptAdapter）：
  - subprocess `Rscript` + 临时 CSV 出数据 + 生成 R 脚本拟合 + 行式结果回传，
    刻意避免 rpy2 硬依赖。
  - 引擎选择（R 脚本内部按包可用性自动降级）：
      * fixest：feols 高维固定效应 + 聚类标准误（最接近 Stata reghdfe）
      * base lm：无依赖兜底，固定效应用 factor() 虚拟变量
  - 聚类标准误：fixest 可用时用 feols(cluster=...)；否则降级为普通标准误，
    并在结果 message 中显式标注（不悄悄掩盖）。

风险说明：
  - 固定效应以 factor() 虚拟变量实现，与 reghdfe/fixest 在自由度口径上可能
    有差异（fixest 的 feols 使用去均值法，更高效且标准误口径更严谨）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from erk.io.base import EngineAdapter, EngineEstimate, STATUS_OK

DATA_FILENAME = "_erk_data.csv"
SCRIPT_FILENAME = "_erk_script.R"


def find_r() -> str | None:
    """定位 Rscript 可执行文件，返回路径或 None。"""
    found = shutil.which("Rscript")
    if found:
        return found
    # Windows 常见安装路径：C:/Program Files/R/R-<ver>/bin/Rscript.exe
    for base in (
        os.environ.get("PROGRAMFILES", "C:/Program Files"),
        os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"),
    ):
        rdir = Path(base) / "R"
        if rdir.exists():
            for ver in sorted(rdir.iterdir(), reverse=True):
                if ver.name.startswith("R-"):
                    exe = ver / "bin" / "Rscript.exe"
                    if exe.exists():
                        return str(exe)
    return None


class RAdapter(EngineAdapter):
    """R 适配器：把回归任务翻译为 R 脚本并批处理执行。"""

    engine_name = "r"

    def __init__(self, rscript_path: str = ""):
        self.rscript_path = rscript_path or find_r() or "Rscript"

    def available(self) -> bool:
        return shutil.which(self.rscript_path) is not None or Path(self.rscript_path).exists()

    # ---- 脚本生成（纯函数，可独立测试） ----

    def generate_script(
        self,
        dep: str,
        indep: list[str],
        fe: list[str] | None = None,
        cluster: str | None = None,
        data_filename: str = DATA_FILENAME,
    ) -> str:
        """生成 R 脚本。

        注意：变量名须为 R 合法标识符（英文、不以数字开头、无空格）。
        中文/特殊变量名需先在 Python 端重命名（Roadmap）。
        """
        fe = fe or []
        use_cluster = bool(cluster)
        L: list[str] = []

        L.append("# ============================================================")
        L.append("# ERK 自动生成 · 基准回归 (OLS)")
        L.append(f"# 因变量: {dep}")
        L.append(f"# 自变量: {' '.join(indep)}")
        L.append(f"# 固定效应: {' '.join(fe) if fe else '(无)'}")
        L.append(f"# 聚类: {cluster or '(无)'}")
        L.append("# ============================================================")
        L.append("")
        L.append(f'df <- read.csv("{data_filename}", stringsAsFactors = FALSE)')
        L.append("")
        for c in set(fe + ([cluster] if cluster else [])):
            L.append(f'df${c} <- as.factor(df${c})')
        L.append("")
        quoted = ", ".join(f'"{v}"' for v in indep)
        L.append(f"vars <- c({quoted})")
        L.append("")

        # 回归块：fixest（聚类时优先）→ base lm 兜底
        rhs = " + ".join(indep)
        fe_terms = " + ".join(f"factor({c})" for c in fe)
        lm_formula = f"{dep} ~ {rhs}" + (f" + {fe_terms}" if fe_terms else "")

        L.append('has_fixest <- requireNamespace("fixest", quietly = TRUE)')
        L.append("use_cluster <- " + ("TRUE" if use_cluster else "FALSE"))
        L.append("cluster_ok <- FALSE")
        L.append("if (use_cluster && has_fixest) {")
        fe_part = (" | " + " + ".join(fe)) if fe else ""
        # ssc(fixef.K="full")：对齐 Stata reghdfe / statsmodels 的自由度口径
        # （fixest 默认 fixef.K="nested" 会导致聚类标准误偏小，实测 0.0764 vs 0.0855）
        L.append(
            f'    m <- fixest::feols({dep} ~ {rhs}{fe_part}, data = df, '
            f'cluster = ~{cluster}, ssc = fixest::ssc(fixef.K = "full"))'
        )
        L.append("    s <- summary(m)")
        L.append("    cf <- s$coeftable")
        L.append('    r2 <- fixest::r2(m, "r2")')
        L.append('    adj_r2 <- fixest::r2(m, "ar2")')
        L.append("    nobs <- m$nobs")
        L.append("    cluster_ok <- TRUE")
        L.append("} else {")
        L.append(f"    m <- lm({lm_formula}, data = df)")
        L.append("    s <- summary(m)")
        L.append("    cf <- s$coefficients")
        L.append("    r2 <- s$r.squared")
        L.append("    adj_r2 <- s$adj.r.squared")
        L.append("    nobs <- nobs(m)")
        L.append("}")
        L.append("")

        # 行式 key=value 输出，供 Python 端解析（避免 JSON 转义）
        L.append('cat(sprintf("r2=%.10f\\n", r2))')
        L.append('cat(sprintf("adj_r2=%.10f\\n", adj_r2))')
        L.append('cat(sprintf("nobs=%d\\n", as.integer(nobs)))')
        L.append('cat(sprintf("cluster_ok=%d\\n", as.integer(cluster_ok)))')
        L.append("n <- length(vars)")
        L.append("for (i in seq_len(n)) {")
        L.append("    v <- vars[i]")
        L.append('    cat(sprintf("%s=%.10f,%.10f,%.10f\\n", v, cf[v, 1], cf[v, 2], cf[v, 4]))')
        L.append("}")
        return "\n".join(L) + "\n"

    # ---- 解析 ----

    @staticmethod
    def parse_result(text: str) -> tuple[EngineEstimate, bool]:
        """解析 R 输出，返回 (EngineEstimate, cluster_ok)。"""
        r2 = adj_r2 = None
        nobs = None
        cluster_ok = False
        coef: dict = {}
        se: dict = {}
        pvalue: dict = {}
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
            elif key == "nobs":
                nobs = int(float(val))
            elif key == "cluster_ok":
                cluster_ok = val == "1"
            elif "," in val:
                parts = val.split(",")
                if len(parts) >= 3:
                    coef[key] = float(parts[0])
                    se[key] = float(parts[1])
                    pvalue[key] = float(parts[2])
        est = EngineEstimate(
            engine="r",
            status=STATUS_OK,
            coef=coef,
            se=se,
            pvalue=pvalue,
            nobs=nobs,
            r2=r2,
            adj_r2=adj_r2,
        )
        return est, cluster_ok

    # ---- 执行 ----

    def _run_impl(
        self,
        df: pd.DataFrame,
        dep: str,
        indep: list[str],
        fe: list[str] | None,
        cluster: str | None,
        workdir: str | None,
    ) -> EngineEstimate:
        work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="erk_r_"))
        work.mkdir(parents=True, exist_ok=True)

        # 1. 导出数据（R 端 as.factor 处理字符串因子，无需 Python 端编码）
        data_path = work / DATA_FILENAME
        df.to_csv(data_path, index=False)

        # 2. 生成脚本
        script_path = work / SCRIPT_FILENAME
        script_path.write_text(self.generate_script(dep, indep, fe=fe, cluster=cluster), encoding="utf-8")

        # 3. 运行 Rscript
        proc = subprocess.run(
            [self.rscript_path, SCRIPT_FILENAME],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            return EngineEstimate(
                engine="r",
                status="error",
                message=f"R 执行失败（返回码 {proc.returncode}）：{proc.stderr.strip()[-400:]}",
            )

        # 4. 解析
        est, cluster_ok = self.parse_result(proc.stdout)
        est.dep = dep
        if cluster and not cluster_ok:
            est.message = "R 环境缺少 fixest 包，聚类标准误已降级为普通标准误；建议安装 fixest 后重跑。"
        return est
