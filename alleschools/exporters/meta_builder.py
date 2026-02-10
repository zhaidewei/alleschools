from __future__ import annotations

"""
meta_builder: 构建符合 refactor/SCHEMA.md 的 meta JSON（axes/fields/i18n）。
"""

from pathlib import Path
from typing import Any, Dict, Sequence


SCHEMA_VERSION = "1.0.0"


def build_po_meta(
    data_file: Path,
    row_count: int,
    columns: Sequence[str],
    outliers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """为 PO points 数据构建 meta JSON。"""
    meta: Dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "layer": "po",
        "source": {
            "duo": "Schooladviezen 2019–2025",
            "cbs": "WOZ per PC4 2019–2024",
        },
        "axes": {
            "x": {
                "field": "x_linear",
                "scale": "linear",
                "domain": [0, 100],
                "metric_id": "po_vwo_advice_share",
            },
            "y": {
                "field": "y_linear",
                "scale": "linear",
                "domain": [0, 800],
                "metric_id": "po_woz_avg_pc4",
            },
            "size": {
                "field": "size",
                "metric_id": "po_pupils_total",
            },
        },
        "fields": {
            "id": {"kind": "id"},
            "brin": {"kind": "id"},
            "name": {"kind": "dimension", "searchable": True},
            "municipality": {"kind": "dimension", "searchable": True},
            "postcode": {"kind": "dimension"},
            "pc4": {"kind": "dimension"},
            "school_type": {"kind": "dimension", "searchable": True},
            "x_linear": {"kind": "metric"},
            "y_linear": {"kind": "metric"},
            "size": {"kind": "metric"},
        },
        "i18n": {
            "nl": {
                "metrics": {
                    "po_vwo_advice_share": {
                        "label": "VWO-advies aandeel",
                        "short": "VWO-advies %",
                        "description": "Gewogen aandeel leerlingen met een VWO-achtig advies over meerdere jaren.",
                    },
                    "po_woz_avg_pc4": {
                        "label": "Gemiddelde WOZ (PC4)",
                        "short": "WOZ (×1.000 EUR)",
                        "description": "Gewogen gemiddelde WOZ-waarde van woningen in deze 4-cijferige postcode.",
                    },
                    "po_pupils_total": {
                        "label": "Totaal aantal leerlingen (advies)",
                        "short": "Leerlingen",
                        "description": "Totaal aantal leerlingen met een schooladvies over alle jaren.",
                    },
                },
                "dimensions": {
                    "school_type": {
                        "values": {
                            "Bo": "Basisonderwijs",
                            "Sbo": "Speciaal basisonderwijs",
                        }
                    }
                },
            },
            "en": {
                "metrics": {
                    "po_vwo_advice_share": {
                        "label": "VWO-equivalent advice share",
                        "short": "VWO advice %",
                        "description": "Weighted share of pupils receiving a VWO-like advice across years.",
                    },
                    "po_woz_avg_pc4": {
                        "label": "Average WOZ (PC4)",
                        "short": "WOZ (×1,000 EUR)",
                        "description": "Weighted average property value (WOZ) for this 4-digit postcode.",
                    },
                    "po_pupils_total": {
                        "label": "Total pupils with advice",
                        "short": "Pupils",
                        "description": "Total number of pupils with a school advice across all years.",
                    },
                },
                "dimensions": {
                    "school_type": {
                        "values": {
                            "Bo": "Primary school",
                            "Sbo": "Special primary school",
                        }
                    }
                },
            },
            "zh": {
                "metrics": {
                    "po_vwo_advice_share": {
                        "label": "VWO 等价升学建议占比",
                        "short": "VWO 升学 %",
                        "description": "按年份加权的 VWO 等价升学建议占比。",
                    },
                    "po_woz_avg_pc4": {
                        "label": "平均房产估值（PC4）",
                        "short": "WOZ（千欧）",
                        "description": "该邮编 PC4 下住房 WOZ 估值的加权平均，单位为千欧元。",
                    },
                    "po_pupils_total": {
                        "label": "有升学建议的学生总数",
                        "short": "学生数",
                        "description": "所有年份中有升学建议的学生总数。",
                    },
                },
                "dimensions": {
                    "school_type": {
                        "values": {
                            "Bo": "普通小学",
                            "Sbo": "特殊小学",
                        }
                    }
                },
            },
        },
        "summary": {
            "data_file": data_file.name,
            "row_count": row_count,
            "columns": list(columns),
        },
    }
    if outliers:
        # 将当前使用的异常值截断策略记录在 summary 中，便于前端/分析端理解数值范围。
        meta["summary"]["outliers"] = {
            "clip_percentiles": outliers.get("clip_percentiles"),
        }
    return meta


def build_vo_meta(
    data_file: Path,
    row_count: int,
    columns: Sequence[str],
    outliers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """为 VO points 数据构建 meta JSON（示意版，重点是结构对齐）。"""
    meta: Dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "layer": "vo",
        "source": {
            "duo": "VO exam results (aggregated)",
        },
        "axes": {
            "x": {
                "field": "x_linear",
                "scale": "linear",
                "domain": [0, 100],
                "metric_id": "vo_vwo_pass_share",
            },
            "y": {
                "field": "y_linear",
                "scale": "linear",
                "domain": [0, 100],
                "metric_id": "vo_science_pass_share",
            },
            "size": {
                "field": "size",
                "metric_id": "vo_candidates_total",
            },
        },
        "fields": {
            "id": {"kind": "id"},
            "brin": {"kind": "id"},
            "name": {"kind": "dimension", "searchable": True},
            "municipality": {"kind": "dimension", "searchable": True},
            "postcode": {"kind": "dimension"},
            "pc4": {"kind": "dimension"},
            "school_type": {"kind": "dimension", "searchable": True},
            "x_linear": {"kind": "metric"},
            "y_linear": {"kind": "metric"},
            "size": {"kind": "metric"},
        },
        "i18n": {
            "nl": {
                "metrics": {
                    "vo_vwo_pass_share": {
                        "label": "VWO-slaagpercentage",
                        "short": "VWO geslaagd %",
                        "description": "Gewogen aandeel VWO-kandidaten dat geslaagd is.",
                    },
                    "vo_science_pass_share": {
                        "label": "Bèta-slaagpercentage",
                        "short": "Bèta geslaagd %",
                        "description": "Gewogen aandeel kandidaten dat geslaagd is voor een bèta-profiel.",
                    },
                    "vo_candidates_total": {
                        "label": "Totaal aantal kandidaten",
                        "short": "Kandidaten",
                        "description": "Totaal aantal examenkandidaten over alle jaren.",
                    },
                },
            },
        },
        "summary": {
            "data_file": data_file.name,
            "row_count": row_count,
            "columns": list(columns),
        },
    }
    if outliers:
        meta["summary"]["outliers"] = {
            "clip_percentiles": outliers.get("clip_percentiles"),
        }
    return meta


__all__ = ["SCHEMA_VERSION", "build_po_meta", "build_vo_meta"]

