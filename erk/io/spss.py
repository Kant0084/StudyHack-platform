"""SPSS 对接。

技术方案（SPSS 批处理 = Production Job）：
  - 生成 .sps 语法文件（GET DATA + OMS 输出 XML + REGRESSION）
  - 生成 .spj 生产作业文件（XML，指定语法文件 + 输出）
  - `stats.exe job.spj -production silent` 静默运行
  - 回读 OMS 输出的 OXML，解析回归系数

SPSS 局限（明确标注，不悄悄掩盖）：
  - REGRESSION 命令不支持 factor 变量固定效应（需手动 dummy 或 UNIANOVA），
    也不支持聚类稳健标准误。
  - 因此 SpssAdapter 仅支持「无固定效应、无聚类」的基础 OLS 与描述统计；
    进阶计量（固定效应/聚类/DID/PSM/IV）应使用 Stata/R 对接。

风险说明：
  - SPSS 结果回读依赖 OMS 输出 XML，OXML 结构复杂，解析器需随版本校准。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from erk.io.base import EngineAdapter, EngineEstimate, STATUS_OK, STATUS_SKIPPED

DATA_FILENAME = "_erk_data.csv"
SCRIPT_FILENAME = "_erk_script.sps"
JOB_FILENAME = "_erk_job.spj"
RESULT_FILENAME = "_erk_result.xml"


def find_spss() -> str | None:
    """定位 SPSS 主程序 stats.exe，返回路径或 None。"""
    for base in (
        os.environ.get("PROGRAMFILES", "C:/Program Files"),
        os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"),
    ):
        spss_dir = Path(base) / "IBM" / "SPSS" / "Statistics"
        if spss_dir.exists():
            for ver in sorted(spss_dir.iterdir(), reverse=True):
                exe = ver / "stats.exe"
                if exe.exists():
                    return str(exe)
    return None


def _spss_var_decl(df: pd.DataFrame) -> list[str]:
    """从 DataFrame 推断 SPSS 变量声明（A=字符串，F=数值）。"""
    decls = []
    for name in df.columns:
        if pd.api.types.is_numeric_dtype(df[name]):
            if pd.api.types.is_integer_dtype(df[name]):
                decls.append(f"    {name} F8.0")
            else:
                decls.append(f"    {name} F8.6")
        else:
            width = min(50, max(8, int(df[name].astype(str).str.len().max())))
            decls.append(f"    {name} A{width}")
    return decls


class SpssAdapter(EngineAdapter):
    """SPSS 适配器：把基础 OLS 翻译为 .sps + .spj 并生产作业运行。"""

    engine_name = "spss"

    def __init__(self, stats_exe: str = ""):
        self.stats_exe = stats_exe or find_spss() or ""

    def available(self) -> bool:
        return bool(self.stats_exe) and Path(self.stats_exe).exists()

    # ---- 语法生成（纯函数，可独立测试） ----

    def generate_sps(
        self,
        df: pd.DataFrame,
        dep: str,
        indep: list[str],
        data_filename: str,
        result_filename: str,
    ) -> str:
        """生成 .sps 语法（GET DATA + OMS + REGRESSION）。"""
        var_decls = _spss_var_decl(df)
        vars_block = "\n".join(var_decls)
        indep_str = " ".join(indep)

        lines = [
            "* ERK auto-generated: OLS regression (no FE, no cluster).",
            "GET DATA /TYPE=TXT",
            f'  /FILE="{data_filename}"',
            "  /ENCODING='UTF8'",
            '  /DELIMITERS=","',
            '  /QUALIFIER=\'"\'',
            "  /ARRANGEMENT=DELIMITED",
            "  /FIRSTCASE=2",
            "  /VARIABLES=",
            vars_block + ".",
            "DATASET NAME ds1.",
            "",
            "OMS /DESTINATION VIEWER=NO FORMAT=OXML",
            f'  OUTFILE="{result_filename}"',
            "  /SELECT TABLES.",
            "",
            "REGRESSION /MISSING LISTWISE /STATISTICS COEFF OUTS R ANOVA",
            "  /CRITERIA=PIN(.05) POUT(.10) /NOORIGIN",
            f"  /DEPENDENT {dep}",
            f"  /METHOD=ENTER {indep_str}.",
            "",
            "OMSEND.",
        ]
        return "\n".join(lines) + "\n"

    def generate_spj(self, sps_path: str, output_path: str) -> str:
        """生成 .spj 生产作业文件（XML）。"""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            '<job xmlns="http://www.ibm.com/software/analytics/spss/xml/production" '
            'codepageSyntaxFiles="false" print="false" syntaxErrorHandling="continue" '
            'syntaxFormat="interactive" unicode="true" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.ibm.com/software/analytics/spss/xml/production '
            'http://www.ibm.com/software/analytics/spss/xml/production/production-1.4.xsd">\n'
            '<locale charset="UTF-8" country="US" language="en"/>\n'
            '<output imageFormat="jpg" imageSize="100" outputFormat="text-codepage" '
            f'outputPath="{output_path}" tableColumnAutofit="true" tableColumnBorder="|" '
            'tableColumnSeparator="space" tableRowBorder="-"/>\n'
            f'<syntax syntaxPath="{sps_path}"/>\n'
            "</job>\n"
        )

    # ---- 解析 ----

    @staticmethod
    def parse_result(xml_text: str) -> EngineEstimate:
        """解析 OMS OXML，提取回归系数/标准误/p 值/R²/N。

        结构定位（不依赖显示语言，中英文候选都覆盖）：
          - Model Summary 表 → R 方 / 调整后 R 方
          - Coefficients 表 → 每个 variable="true" 的 category 的
            B（系数）/ 标准误差 / 显著性
          - Notes 表 → 工作数据文件中的行数（N）
        """
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
        NS = "{http://www.ibm.com/software/analytics/spss/xml/oms}"

        coef: dict = {}
        se: dict = {}
        pvalue: dict = {}
        r2 = adj_r2 = None
        nobs = None

        # 中英文候选（SPSS 界面语言可能不同）
        _R2 = ("R 方", "R Square", "R方")
        _ADJ_R2 = ("调整后 R 方", "Adjusted R Square", "调整后R方")
        _B = ("B",)
        _SE = ("标准误差", "Std. Error", "标准误")
        _P = ("显著性", "Sig.")
        _N = ("工作数据文件中的行数", "Number of rows in working data file")

        def cell_number(cat) -> float | None:
            for cell in cat.iter(NS + "cell"):
                if cell.get("number"):
                    try:
                        return float(cell.get("number"))
                    except ValueError:
                        return None
            return None

        for pt in root.iter(NS + "pivotTable"):
            subtype = pt.get("subType")
            if subtype == "Model Summary":
                for cat in pt.iter(NS + "category"):
                    t = cat.get("text")
                    if t in _R2:
                        r2 = cell_number(cat)
                    elif t in _ADJ_R2:
                        adj_r2 = cell_number(cat)
            elif subtype == "Coefficients":
                for cat in pt.iter(NS + "category"):
                    if cat.get("variable") == "true" and cat.get("varName"):
                        varname = cat.get("varName")
                        b = se_v = p = None
                        for sub in cat.iter(NS + "category"):
                            st = sub.get("text")
                            if st in _B:
                                b = cell_number(sub)
                            elif st in _SE:
                                se_v = cell_number(sub)
                            elif st in _P:
                                p = cell_number(sub)
                        if b is not None:
                            coef[varname] = b
                            se[varname] = se_v
                            pvalue[varname] = p

        # 提取 N（Notes 表）
        for cat in root.iter(NS + "category"):
            if cat.get("text") in _N:
                for cell in cat.iter(NS + "cell"):
                    if cell.get("number"):
                        nobs = int(float(cell.get("number")))

        return EngineEstimate(
            engine="spss",
            status=STATUS_OK,
            coef=coef,
            se=se,
            pvalue=pvalue,
            nobs=nobs,
            r2=r2,
            adj_r2=adj_r2,
        )

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
        # SPSS 的 REGRESSION 不支持固定效应/聚类，明确降级并说明
        if fe or cluster:
            return EngineEstimate(
                engine="spss",
                status=STATUS_SKIPPED,
                message="SPSS 的 REGRESSION 不支持固定效应/聚类标准误，请使用 Stata/R 对接。",
            )

        work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="erk_spss_"))
        work.mkdir(parents=True, exist_ok=True)

        # 1. 导出数据（绝对 Windows 路径，SPSS 生产作业会重置工作目录）
        data_path = work / DATA_FILENAME
        df.to_csv(data_path, index=False)
        win_data = data_path.as_posix()

        result_path = work / RESULT_FILENAME
        win_result = result_path.as_posix()

        # 2. 生成 .sps 与 .spj
        sps = self.generate_sps(df, dep, indep, win_data, win_result)
        sps_path = work / SCRIPT_FILENAME
        sps_path.write_text(sps, encoding="utf-8")

        output_txt = work / "_erk_output.txt"
        spj = self.generate_spj(sps_path.as_posix(), output_txt.as_posix())
        spj_path = work / JOB_FILENAME
        spj_path.write_text(spj, encoding="utf-8")

        # 3. 生产作业静默运行
        proc = subprocess.run(
            [self.stats_exe, spj_path.as_posix(), "-production", "silent"],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=300,
        )

        # 4. 读 OMS 结果
        if not result_path.exists():
            return EngineEstimate(
                engine="spss",
                status="error",
                message=f"SPSS 未产出结果文件（返回码 {proc.returncode}）。输出见 {output_txt}",
            )
        est = self.parse_result(result_path.read_text(encoding="utf-8", errors="replace"))
        est.dep = dep
        return est


def _next_number(root, node) -> float | None:
    """占位函数已废弃，保留以避免外部引用报错。"""
    return None
