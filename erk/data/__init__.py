"""数据层：多源数据接入、清洗与变量构造、示例数据生成。"""

from erk.data.loader import load_file
from erk.data.synthetic import generate_finance_panel

__all__ = ["load_file", "generate_finance_panel"]
