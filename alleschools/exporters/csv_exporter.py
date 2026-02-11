from __future__ import annotations

"""
CSV 导出工具。
"""

import csv
from pathlib import Path
from typing import Iterable, Mapping, Sequence


PO_FIELDNAMES: Sequence[str] = [
    "BRIN",
    "vestigingsnaam",
    "gemeente",
    "postcode",
    "type",
    "X_linear",
    "Y_linear",
    "pupils_total",
]

PO_META_FIELDNAMES: Sequence[str] = [
    "years_covered",
    "has_full_woz",
    "data_quality_flags",
]


VO_FIELDNAMES: Sequence[str] = [
    "BRIN",
    "vestigingsnaam",
    "gemeente",
    "postcode",
    "type",
    "X_linear",
    "Y_linear",
    "candidates_total",
    "candidates_weighted_avg",
]

VO_META_FIELDNAMES: Sequence[str] = [
    "years_covered",
    "data_quality_flags",
]


VO_PROFILES_FIELDNAMES: Sequence[str] = [
    "BRIN",
    "vestigingsnaam",
    "gemeente",
    "postcode",
    "type",
    "profile_id",
    "X_profile",
    "Y_vwo_share",
    "candidates_total",
    "candidates_weighted_avg",
]


def export_po_csv(
    rows: Iterable[Mapping[str, object]],
    path: Path,
    include_meta_columns: bool = True,
) -> None:
    """
    将小学 X/Y 结果写出为 CSV。
    若 include_meta_columns 为 True，则追加 years_covered、has_full_woz、data_quality_flags 列。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(PO_FIELDNAMES)
    if include_meta_columns:
        fieldnames = list(fieldnames) + list(PO_META_FIELDNAMES)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_vo_csv(
    rows: Iterable[Mapping[str, object]],
    path: Path,
    include_meta_columns: bool = True,
) -> None:
    """将中学 VO X/Y 结果写出为 CSV。若 include_meta_columns 为 True，则追加 years_covered、data_quality_flags 列。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(VO_FIELDNAMES)
    if include_meta_columns:
        fieldnames = list(fieldnames) + list(VO_META_FIELDNAMES)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_vo_profiles_csv(
    rows: Iterable[Mapping[str, object]],
    path: Path,
) -> None:
    """
    将 VO profiel 指数结果写出为 CSV。

    字段包含：
        BRIN, vestigingsnaam, gemeente, postcode, type,
        profile_id (NT/NG/EM/CM), X_profile, Y_vwo_share, candidates_total
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(VO_PROFILES_FIELDNAMES)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


__all__ = [
    "PO_FIELDNAMES",
    "PO_META_FIELDNAMES",
    "VO_FIELDNAMES",
    "VO_META_FIELDNAMES",
    "VO_PROFILES_FIELDNAMES",
    "export_po_csv",
    "export_vo_csv",
    "export_vo_profiles_csv",
]

