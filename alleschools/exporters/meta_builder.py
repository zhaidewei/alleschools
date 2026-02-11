from __future__ import annotations

"""
meta_builder: 构建符合 refactor/SCHEMA.md 的 meta JSON（axes/fields/i18n）。
"""

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


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
            # X 轴：VWO 平均分（10 分制）
            "x": {
                "field": "x_linear",
                "scale": "linear",
                "domain": [4, 10],
                "metric_id": "vo_vwo_mean_cijferlijst",
            },
            # Y 轴仍然为理科方向通过占比（0–100%）
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
                    "vo_vwo_mean_cijferlijst": {
                        "label": "VWO-gemiddelde cijferlijst",
                        "short": "VWO-gemiddelde",
                        "description": "Per vestiging het gemiddelde van vakgemiddelden (cijferlijst, 1–10) voor VWO-examens, gebruikmakend van het laatste jaar met voldoende vakken.",
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
            "en": {
                "metrics": {
                    "vo_vwo_mean_cijferlijst": {
                        "label": "VWO average final mark",
                        "short": "VWO average",
                        "description": "For each school (vestiging) the simple average of subject-level final marks (cijferlijst, 1–10) for VWO exams, using the latest year with sufficient subjects.",
                    },
                    "vo_science_pass_share": {
                        "label": "Science pass share",
                        "short": "Science pass %",
                        "description": "Weighted share of candidates passing a science-oriented profile.",
                    },
                    "vo_candidates_total": {
                        "label": "Total exam candidates",
                        "short": "Candidates",
                        "description": "Total number of exam candidates across all years.",
                    },
                },
            },
            "zh": {
                "metrics": {
                    "vo_vwo_mean_cijferlijst": {
                        "label": "VWO 平均分（cijferlijst）",
                        "short": "VWO 平均分",
                        "description": "以学校为单位，对该校所有 VWO 科目成绩单平均分（1–10）再取算术平均，使用最近一个有足够科目的学年。",
                    },
                    "vo_science_pass_share": {
                        "label": "理科通过占比",
                        "short": "理科通过 %",
                        "description": "在所有考试考生中，选修理科方向（bèta）并通过的占比，经多学年加权。",
                    },
                    "vo_candidates_total": {
                        "label": "考试考生总数",
                        "short": "考生数",
                        "description": "多学年合计的考试考生总人数。",
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


def build_vo_profiles_meta(
    data_files: Mapping[str, Path],
    row_counts: Mapping[str, int],
    *,
    y_domain: Sequence[float] | None = None,
) -> Dict[str, Any]:
    """
    为 VO profiel 图构建 meta JSON。

    data_files:
        profile_id -> CSV 文件路径（例如 {"NT": Path("generated/schools_profiles_nt.csv"), ...}）
    row_counts:
        profile_id -> 行数
    y_domain:
        VWO 占比 Y 轴 domain，默认 [0, 100]。
    """
    y_dom = list(y_domain) if y_domain is not None else [0.0, 100.0]
    profiles_summary: Dict[str, Any] = {}
    for prof_id, path in data_files.items():
        profiles_summary[prof_id] = {
            "data_file": path.name,
            "row_count": int(row_counts.get(prof_id, 0)),
        }

    meta: Dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "layer": "vo_profiles",
        "sources": {
            "duo": "VWO central exam results (per subject, 5-year window)",
        },
        # 这里的 axes 是「通用」定义：X_profile / Y_vwo_share / size，
        # 具体某个 profiel 使用哪个 metric_id 由 profiles 字段指定。
        "axes": {
            "x": {
                "field": "X_profile",
                "scale": "linear",
                "domain": [4, 10],
            },
            "y": {
                "field": "Y_vwo_share",
                "scale": "linear",
                "domain": y_dom,
                "metric_id": "vo_vwo_share",
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
            "profile_id": {"kind": "dimension"},
            "X_profile": {"kind": "metric"},
            "Y_vwo_share": {"kind": "metric"},
            "size": {"kind": "metric"},
        },
        # 为 4 个 profiel 定义 X 轴 metric，与 backlog 3.5 中权重一致。
        "profiles": {
            "NT": {
                "metric_id": "vo_nt_index",
                "domain": [4, 10],
            },
            "NG": {
                "metric_id": "vo_ng_index",
                "domain": [4, 10],
            },
            "EM": {
                "metric_id": "vo_em_index",
                "domain": [4, 10],
            },
            "CM": {
                "metric_id": "vo_cm_index",
                "domain": [4, 10],
            },
        },
        "i18n": {
            "nl": {
                "metrics": {
                    "vo_nt_index": {
                        "label": "VWO-profielindex Natuur & Techniek",
                        "short": "Index N&T",
                        "description": "Voor iedere school en jaar: 0,50 × C(WISB) + 0,25 × C(NAT) + 0,25 × C(SCHK), op basis van VWO centrale examens, daarna 5-jaars gewogen gemiddelde.",
                    },
                    "vo_ng_index": {
                        "label": "VWO-profielindex Natuur & Gezondheid",
                        "short": "Index N&G",
                        "description": "0,35 × C(BIOL) + 0,25 × C(SCHK) + 0,40 × C(WISB), gewogen over de laatste 5 schooljaren.",
                    },
                    "vo_em_index": {
                        "label": "VWO-profielindex Economie & Maatschappij",
                        "short": "Index E&M",
                        "description": "0,333 × C(ECON) + 0,334 × C(BECO) + 0,333 × C_WIS^EM, waarbij C_WIS^EM het gemiddelde is van Wiskunde A/B (of de enige aanwezige).",
                    },
                    "vo_cm_index": {
                        "label": "VWO-profielindex Cultuur & Maatschappij",
                        "short": "Index C&M",
                        "description": "0,333 × C(GES) + 0,333 × C_WIS^CM + 0,333 × C_TALEN, met C_WIS^CM uit Wiskunde C/A en C_TALEN het gemiddelde van Engels/Duits/Frans.",
                    },
                    "vo_vwo_share": {
                        "label": "VWO-aandeel geslaagden",
                        "short": "VWO-aandeel %",
                        "description": "VWO geslaagden / alle examenkandidaten (HAVO, VWO, VMBO) over meerdere jaren, in procenten.",
                    },
                    "vo_candidates_total": {
                        "label": "Totaal aantal examenkandidaten",
                        "short": "Kandidaten (5 jr)",
                        "description": "Totaal aantal examenkandidaten over dezelfde 5-jaarsperiode.",
                    },
                },
            },
            "en": {
                "metrics": {
                    "vo_nt_index": {
                        "label": "VWO profile index – Nature & Technology",
                        "short": "Index N&T",
                        "description": "For each school/year: 0.50 × C(WISB) + 0.25 × C(NAT) + 0.25 × C(SCHK) using VWO central exam averages, then time-weighted over 5 schoolyears.",
                    },
                    "vo_ng_index": {
                        "label": "VWO profile index – Nature & Health",
                        "short": "Index N&G",
                        "description": "0.35 × C(BIOL) + 0.25 × C(SCHK) + 0.40 × C(WISB), aggregated as a 5-year weighted average.",
                    },
                    "vo_em_index": {
                        "label": "VWO profile index – Economics & Society",
                        "short": "Index E&M",
                        "description": "0.333 × C(ECON) + 0.334 × C(BECO) + 0.333 × C_WIS^EM, where C_WIS^EM is based on Wiskunde A/B if present.",
                    },
                    "vo_cm_index": {
                        "label": "VWO profile index – Culture & Society",
                        "short": "Index C&M",
                        "description": "0.333 × C(GES) + 0.333 × C_WIS^CM + 0.333 × C_TALEN, with C_WIS^CM from Wiskunde C/A and C_TALEN the mean of English/German/French.",
                    },
                    "vo_vwo_share": {
                        "label": "VWO share of passes",
                        "short": "VWO share %",
                        "description": "VWO passes / all exam candidates (HAVO, VWO, VMBO) over multiple years, as a percentage.",
                    },
                    "vo_candidates_total": {
                        "label": "Total exam candidates",
                        "short": "Candidates (5 yr)",
                        "description": "Total number of exam candidates in the 5-year window.",
                    },
                },
            },
            "zh": {
                "metrics": {
                    "vo_nt_index": {
                        "label": "VWO 理工 profiel 指数（Natuur & Techniek）",
                        "short": "N&T 指数",
                        "description": "按学校和学年：0.50×C(WISB) + 0.25×C(NAT) + 0.25×C(SCHK)，基于 VWO 统考平均分，再对最近 5 学年按时间加权求平均。",
                    },
                    "vo_ng_index": {
                        "label": "VWO 理生 profiel 指数（Natuur & Gezondheid）",
                        "short": "N&G 指数",
                        "description": "0.35×C(BIOL) + 0.25×C(SCHK) + 0.40×C(WISB)，在 5 个学年上按时间加权聚合。",
                    },
                    "vo_em_index": {
                        "label": "VWO 经社 profiel 指数（Economie & Maatschappij）",
                        "short": "E&M 指数",
                        "description": "0.333×C(ECON) + 0.334×C(BECO) + 0.333×C_WIS^EM，其中 C_WIS^EM 由 A/B 数学科目（若存在）构成。",
                    },
                    "vo_cm_index": {
                        "label": "VWO 文社 profiel 指数（Cultuur & Maatschappij）",
                        "short": "C&M 指数",
                        "description": "0.333×C(GES) + 0.333×C_WIS^CM + 0.333×C_TALEN，C_WIS^CM 来自 Wiskunde C/A，C_TALEN 为英/德/法平均。",
                    },
                    "vo_vwo_share": {
                        "label": "VWO 通过人数占比",
                        "short": "VWO 占比 %",
                        "description": "VWO 通过人数 / 全部考试考生人数（含 HAVO/VWO/VMBO 等），按学年加权后的百分比。",
                    },
                    "vo_candidates_total": {
                        "label": "考试考生总数",
                        "short": "考生数（5 年）",
                        "description": "同一 5 学年窗口内的全部考试考生总数。",
                    },
                },
            },
        },
        "summary": {
            "profiles": profiles_summary,
            "y_domain": y_dom,
        },
    }
    return meta


__all__ = ["SCHEMA_VERSION", "build_po_meta", "build_vo_meta", "build_vo_profiles_meta"]

