from __future__ import annotations

"""
CBS WOZ per postcode (PC4) per year 加载。

提供统一的 (pc4, year) -> woz_waarde 映射，
供 PO / VO 等不同流水线复用。
"""

import csv
import os
from typing import Dict, List, Tuple


def load_woz_pc4_year(path: str) -> Tuple[Dict[Tuple[str, int], float], List[int]]:
    """
    读取 cbs_woz_per_postcode_year.csv。

    返回:
        woz: (pc4, year) -> woz_waarde (float)
        years: 排好序的可用年份列表
    """
    if not os.path.exists(path):
        return {}, []

    out: Dict[Tuple[str, int], float] = {}
    years_set = set()

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pc4 = (row.get("pc4") or "").strip()
            year = row.get("year")
            val = row.get("woz_waarde")
            if not pc4 or not year or not val:
                continue
            try:
                y = int(year)
                v = float(val)
            except (ValueError, TypeError):
                continue
            out[(pc4, y)] = v
            years_set.add(y)

    return out, sorted(years_set)


__all__ = ["load_woz_pc4_year"]

