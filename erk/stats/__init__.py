"""统计层：内置基础统计引擎 + 统一结果契约 + 内生性工具箱。"""

from erk.stats.endogeneity import run_did, run_iv
from erk.stats.psm import PsmResult, run_psm
from erk.stats.rdd import RddResult, run_rdd
from erk.stats.regression import RegressionResult, run_ols
from erk.stats.results import to_jsonable

__all__ = [
    "RegressionResult", "run_ols", "to_jsonable",
    "PsmResult", "run_psm",
    "RddResult", "run_rdd",
    "run_did", "run_iv",
]
