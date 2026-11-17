"""问卷分析引擎。

覆盖：数据接入、描述统计、信效度检验、差异与相关分析。
"""

from erk.survey.dataset import QuestionnaireDataset
from erk.survey.factor_analysis import FactorResult, factor_analysis, varimax_rotation
from erk.survey.importer import QuestionnaireImporter, Variable, detect_type, parse_header
from erk.survey.reliability import ReliabilityResult, run_reliability

__all__ = [
    "QuestionnaireDataset",
    "QuestionnaireImporter",
    "Variable",
    "detect_type",
    "parse_header",
    "ReliabilityResult",
    "run_reliability",
    "FactorResult",
    "factor_analysis",
    "varimax_rotation",
]
