"""多源数据接入。

v0.1 阶段支持常见表格文件（csv / xlsx / dta）。国泰安(CSMAR) 导出格式、
问卷星原始数据等国内平台的原生适配在 Roadmap 中规划，此处预留扩展点：
后续为每个数据源实现独立的 parser，统一返回 pandas.DataFrame。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_file(path: str | Path) -> pd.DataFrame:
    """按扩展名加载数据文件，返回 DataFrame。

    中文环境常见 GBK 编码，csv 先尝试 utf-8，失败回退 gbk，规避乱码。
    """
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(p)
    if suffix == ".csv":
        try:
            return pd.read_csv(p, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(p, encoding="gbk")
    if suffix == ".dta":
        # 需 pandas 编译时支持 stata 读取；不支持时给出明确提示
        return pd.read_stata(p)

    raise ValueError(f"暂不支持的文件类型: {suffix}（支持 .xlsx/.csv/.dta）")
