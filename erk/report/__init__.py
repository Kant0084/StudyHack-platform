"""报告层：三线表渲染、报告组装与生成。"""

from erk.report.builder import ReportBuilder, df_to_markdown
from erk.report.empirical_report import build_empirical_report
from erk.report.survey_report import build_survey_report
from erk.report.table import RegressionTable

__all__ = [
    "RegressionTable",
    "ReportBuilder",
    "df_to_markdown",
    "build_survey_report",
    "build_empirical_report",
]
