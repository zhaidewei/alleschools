from __future__ import annotations

"""
points data 导出：将内部宽表行转换为前端使用的 points JSON（见 refactor/SCHEMA.md）。
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import json


def _po_row_to_point(row: Mapping[str, Any]) -> Dict[str, Any]:
    """将 PO 宽表行映射为 points data schema 的单个点对象。"""
    postcode_full = (row.get("postcode") or "").strip()
    pc4 = postcode_full.replace(" ", "")[:4] if postcode_full else ""
    years_str = row.get("years_covered") or ""
    years_list: List[str] = [y.strip() for y in str(years_str).split(",") if y.strip()]
    has_full_woz = bool(row.get("has_full_woz"))

    return {
        "id": row.get("BRIN"),
        "layer": "po",
        "brin": row.get("BRIN"),
        "name": row.get("vestigingsnaam"),
        "municipality": row.get("gemeente"),
        "postcode": postcode_full,
        "pc4": pc4,
        "school_type": row.get("type"),
        "x_linear": row.get("X_linear"),
        "y_linear": row.get("Y_linear"),
        "size": row.get("pupils_total"),
        "years_covered": years_list,
        "flags": {
            "has_full_woz": has_full_woz,
            # 主数据文件中的点本身没有因为样本过小被排除
            "low_sample_excluded": False,
        },
    }


def _vo_row_to_point(row: Mapping[str, Any]) -> Dict[str, Any]:
    """将 VO 宽表行映射为 points data schema 的单个点对象。"""
    postcode_full = (row.get("postcode") or "").strip()
    pc4 = postcode_full.replace(" ", "")[:4] if postcode_full else ""
    years_str = row.get("years_covered") or ""
    years_list: List[str] = [y.strip() for y in str(years_str).split(",") if y.strip()]

    return {
        "id": row.get("BRIN"),
        "layer": "vo",
        "brin": row.get("BRIN"),
        "name": row.get("vestigingsnaam"),
        "municipality": row.get("gemeente"),
        "postcode": postcode_full,
        "pc4": pc4,
        "school_type": row.get("type"),
        "x_linear": row.get("X_linear"),
        "y_linear": row.get("Y_linear"),
        "size": row.get("candidates_total"),
        "years_covered": years_list,
        "flags": {
            # 目前 VO 未接入 WOZ，先统一为 False，未来如接入可更新
            "has_full_woz": False,
            "low_sample_excluded": False,
        },
    }


def export_po_points(
    rows: Iterable[Mapping[str, Any]],
    path: Path,
) -> None:
    """将 PO 宽表行导出为 points JSON 数组。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    points = [_po_row_to_point(r) for r in rows]
    with path.open("w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=2)


def export_vo_points(
    rows: Iterable[Mapping[str, Any]],
    path: Path,
) -> None:
    """将 VO 宽表行导出为 points JSON 数组。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    points = [_vo_row_to_point(r) for r in rows]
    with path.open("w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=2)


__all__ = ["export_po_points", "export_vo_points"]

