"""问卷星数据接入（本地文件导入）。

解析问卷星导出的 Excel/CSV（题目文本作为表头），自动识别题型与变量，
构造带元数据的 QuestionnaireDataset。

设计说明：
  - 本模块解析问卷星「导出数据文件」的本地格式，不依赖问卷星 API，
    符合 ERK「全本地运行、不上传数据」原则。
  - 问卷星 API 方式（get_survey + query_responses + submitdata 解码）
    见 Roadmap，参考 wjx-ai-kit 的题型映射（q_type 3=单选 4=多选 5=填空 7=矩阵）。

格式假设（问卷星常见导出格式，解析器对常见变体做了兼容）：
  - 表头为题目文本，如 "1.您的性别"、"1、您的性别"、"1. 您的性别"；
  - 单选题：选项文本，或选项序号（数字编码）；
  - 多选题：逗号/分号/顿号分隔的选项；
  - 量表题：数字 1–N（Likert）；
  - 矩阵题：多个子题列，表头如 "3.满意度[响应速度]"。

风险说明：题型识别是启发式的，量表题与数字编码单选题可能混淆；导出格式
因问卷星版本/设置而异，遇到无法识别的格式请在报告中人工复核。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from erk.survey.dataset import QuestionnaireDataset


@dataclass
class Variable:
    """单个问卷变量的元数据。"""

    name: str              # 列名（表头原文）
    label: str             # 题目文本（去题号）
    q_type: str            # single / multi / scale / text
    q_number: int | None = None   # 题号
    sub_label: str = ""    # 子题标签（矩阵题）
    options: list = field(default_factory=list)  # 选项（single/multi）

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "q_type": self.q_type,
            "q_number": self.q_number,
            "sub_label": self.sub_label,
            "options": self.options,
        }


def parse_header(col: str) -> tuple[int | None, str, str]:
    """解析表头，返回 (题号, 题目文本, 子题标签)。

    兼容格式：
      "1.您的性别" / "1、您的性别" / "1. 您的性别" / "第1题 您的性别"
      矩阵题："3.满意度[响应速度]" / "3.满意度（响应速度）"
    """
    col = str(col).strip()
    q_number = None
    rest = col

    # 题号：数字 + 分隔符（. 、 ． 空格 或 "题"字，如 "第4题 使用的功能"）
    m = re.match(r"^(?:第)?(\d+)[题\.、．\s]+(.*)$", col)
    if m:
        q_number = int(m.group(1))
        rest = m.group(2).strip()

    # 子题标签：方括号或圆括号
    sub_label = ""
    m2 = re.match(r"^(.*?)[\[\（\(](.*?)[\]\）\)]$", rest)
    if m2:
        rest = m2.group(1).strip()
        sub_label = m2.group(2).strip()

    return q_number, rest, sub_label


def detect_type(series: pd.Series) -> tuple[str, list]:
    """从一列数据推断题型，返回 (题型, 选项列表)。"""
    s = series.dropna().astype(str)
    if s.empty:
        return "text", []

    # 多选题：含分隔符（逗号/分号/顿号/竖线）
    if s.str.contains(r"[，,;；、|]", regex=True).any():
        opts = sorted(set(x.strip() for v in s for x in re.split(r"[，,;；、|]", v) if x.strip()))
        return "multi", opts

    # 数值列（可能是量表题 / 数字编码单选题 / 连续变量）
    numeric = pd.to_numeric(s, errors="coerce")
    if numeric.notna().all():
        vals = sorted(numeric.unique())
        n = len(vals)
        if 1 <= min(vals) and max(vals) <= 11 and n <= 11:
            # 连续且 ≥3 档判定为 Likert 量表
            if vals == list(range(min(vals), max(vals) + 1)) and n >= 3:
                return "scale", vals
            return "single", vals
        # 大范围数值（如年龄）→ 连续变量
        return "continuous", []

    # 文本：唯一值少 → 单选，否则填空
    n_unique = s.nunique()
    if n_unique <= 15:
        return "single", sorted(s.unique().tolist())
    return "text", []


class QuestionnaireImporter:
    """问卷星导出文件的导入器。"""

    # 系统列（非题目列），按子串匹配跳过
    _SKIP_HINTS = (
        "序号", "编号", "答卷id", "提交答卷时间", "所用时间", "来源", "来自ip",
        "ip", "城市", "自定义", "总分", "答题时长",
    )

    @classmethod
    def _is_system_col(cls, name: str) -> bool:
        low = str(name).lower()
        return any(h in low for h in cls._SKIP_HINTS)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> QuestionnaireDataset:
        """从宽表 DataFrame 构造带元数据的问卷数据集。"""
        variables: list[Variable] = []
        for col in df.columns:
            if cls._is_system_col(col):
                continue
            q_number, label, sub_label = parse_header(col)
            q_type, options = detect_type(df[col])
            variables.append(
                Variable(
                    name=str(col),
                    label=label or str(col),
                    q_type=q_type,
                    q_number=q_number,
                    sub_label=sub_label,
                    options=options,
                )
            )
        return QuestionnaireDataset(df, variables=variables)

    @classmethod
    def from_excel(cls, path: str | Path) -> QuestionnaireDataset:
        return cls.from_dataframe(pd.read_excel(path))

    @classmethod
    def from_csv(cls, path: str | Path) -> QuestionnaireDataset:
        p = Path(path)
        try:
            df = pd.read_csv(p, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(p, encoding="gbk")
        return cls.from_dataframe(df)
