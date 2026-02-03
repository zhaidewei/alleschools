from __future__ import annotations

"""
长表导出：按「学校 × 学年」展开为 CSV，便于 BI 按年筛选。
"""

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .csv_exporter import (
    PO_FIELDNAMES,
    PO_META_FIELDNAMES,
    VO_FIELDNAMES,
    VO_META_FIELDNAMES,
)


def _expand_rows(
    rows: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    将每行按 years_covered 拆成多行，每行增加 year 列。
    fieldnames 为宽表列名（不含 year）；输出每行含 year 及与 fieldnames 一致的其余列。
    """
    out: List[Dict[str, Any]] = []
    names = list(fieldnames)
    if "years_covered" not in names:
        names = list(names) + ["years_covered"]
    if "BRIN" in names:
        idx = names.index("BRIN") + 1
        long_names = names[:idx] + ["year"] + names[idx:]
    else:
        long_names = ["year"] + list(names)
    for row in rows:
        row = dict(row)
        years_str = row.get("years_covered") or ""
        years_list = [y.strip() for y in str(years_str).split(",") if y.strip()]
        if not years_list:
            years_list = [""]
        for year in years_list:
            r = {k: row.get(k) for k in names if k in row}
            r["year"] = year
            out.append(r)
    return out, long_names


def export_po_long_table(
    rows: Iterable[Mapping[str, Any]],
    path: Path,
    include_meta_columns: bool = True,
) -> None:
    """将 PO 结果按 years_covered 展开为长表 CSV（BRIN, year, ...）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(PO_FIELDNAMES) + (list(PO_META_FIELDNAMES) if include_meta_columns else [])
    expanded, long_names = _expand_rows(rows, fieldnames)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=long_names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(expanded)


def export_vo_long_table(
    rows: Iterable[Mapping[str, Any]],
    path: Path,
    include_meta_columns: bool = True,
) -> None:
    """将 VO 结果按 years_covered 展开为长表 CSV（BRIN, year, ...）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(VO_FIELDNAMES) + (list(VO_META_FIELDNAMES) if include_meta_columns else [])
    expanded, long_names = _expand_rows(rows, fieldnames)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=long_names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(expanded)


__all__ = ["export_po_long_table", "export_vo_long_table"]
