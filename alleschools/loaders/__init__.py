"""
数据加载模块。

封装 DUO / CBS 等数据源的读取与基础清洗逻辑。
"""

from .cbs_loader import load_woz_pc4_year  # noqa: F401
from .duo_loader import load_schooladviezen_po  # noqa: F401
from .vo_loader import load_exam_schools, load_vestigingen_postcode  # noqa: F401
from .vwo_exam_loader import (  # noqa: F401
    SchoolYearCentralExamScores,
    SchoolYearScores,
    load_vwo_central_exam_scores,
    load_vwo_exam_cijferlijst_scores,
)

__all__ = [
    "load_schooladviezen_po",
    "load_woz_pc4_year",
    "load_vestigingen_postcode",
    "load_exam_schools",
    "SchoolYearScores",
    "SchoolYearCentralExamScores",
    "load_vwo_exam_cijferlijst_scores",
    "load_vwo_central_exam_scores",
]

