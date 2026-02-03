"""
数据质量检查实现：基于 rows_out、excluded 及源文件扫描。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from alleschools.config import SCHOOLJARS


def _collect_duplicate_brins_po(data_root: Path, pattern: str) -> List[str]:
    """
    扫描 PO DUO Schooladviezen CSV，返回在同一文件内出现多于一次的 BRIN 列表。
    pattern 如 "duo_schooladviezen_{start}_{end}.csv"。
    """
    seen_brins: List[str] = []
    for start, end in SCHOOLJARS:
        path = data_root / pattern.replace("{start}", start).replace("{end}", end)
        if not path.is_file():
            continue
        counts: Dict[str, int] = {}
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with path.open("r", encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=";", quotechar='"')
                    rows = list(reader)
                break
            except (UnicodeDecodeError, OSError):
                continue
        else:
            continue
        for row in rows:
            inst = (row.get("INSTELLINGSCODE") or row.get("BRIN_NUMMER") or "").strip().strip('"')
            vest = (row.get("VESTIGINGSCODE") or row.get("VESTIGINGSNUMMER") or "").strip().strip('"')
            brin = (inst + vest) if (inst + vest) else (row.get("BRIN_NUMMER") or "").strip().strip('"')
            if not brin:
                continue
            counts[brin] = counts.get(brin, 0) + 1
        for brin, cnt in counts.items():
            if cnt > 1 and brin not in seen_brins:
                seen_brins.append(brin)
    return sorted(seen_brins)


def _collect_duplicate_brins_vo(data_root: Path, exams_all: str, exams_small: str) -> List[str]:
    """扫描 VO 考试 CSV，返回同一文件中出现多于一次的 VESTIGINGSCODE（BRIN）列表。"""
    inp_all = data_root / exams_all
    inp_small = data_root / exams_small
    inp = inp_all if inp_all.exists() else inp_small
    if not inp.exists():
        return []
    counts: Dict[str, int] = {}
    try:
        with inp.open("r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";", quotechar='"')
            skip = True
            for row in reader:
                if len(row) <= 1:
                    continue
                brin = (row[1] or "").strip().strip('"')  # COL_VESTIGING
                if skip and brin.upper() == "VESTIGINGSCODE":
                    skip = False
                    continue
                skip = False
                if brin:
                    counts[brin] = counts.get(brin, 0) + 1
    except (OSError, UnicodeDecodeError):
        return []
    return sorted(b for b, c in counts.items() if c > 1)


def _missing_postcode_brins(rows_out: Sequence[Mapping[str, Any]]) -> List[str]:
    """从输出行中收集 postcode 为空或仅空格的 BRIN。"""
    return sorted(
        str(r.get("BRIN", "")).strip()
        for r in rows_out
        if not (str(r.get("postcode") or "").strip())
    )


def _cap_list(brins: List[str], max_n: int) -> List[str]:
    if max_n <= 0 or len(brins) <= max_n:
        return brins
    return brins[:max_n]


def run_po_quality(
    rows_out: Sequence[Mapping[str, Any]],
    excluded: Sequence[Mapping[str, Any]],
    data_root: Path,
    input_cfg: Mapping[str, Any],
    *,
    max_brins_in_report: int = 50,
) -> Dict[str, Any]:
    """
    执行 PO 数据质量检查。

    返回 data_quality 字典，可直接并入 run_report。
    """
    pattern = str(input_cfg.get("duo_schooladviezen_pattern") or "duo_schooladviezen_{start}_{end}.csv")
    duplicate_brins = _collect_duplicate_brins_po(data_root, pattern)
    missing = _missing_postcode_brins(rows_out)
    return {
        "duplicate_brin_in_source": {
            "count": len(duplicate_brins),
            "brins": _cap_list(duplicate_brins, max_brins_in_report),
        },
        "missing_postcode": {
            "count": len(missing),
            "brins": _cap_list(missing, max_brins_in_report),
        },
        "excluded_small_sample": {
            "count": len(excluded),
        },
    }


def run_vo_quality(
    rows_out: Sequence[Mapping[str, Any]],
    excluded: Sequence[Mapping[str, Any]],
    data_root: Path,
    input_cfg: Mapping[str, Any],
    *,
    max_brins_in_report: int = 50,
) -> Dict[str, Any]:
    """
    执行 VO 数据质量检查。

    返回 data_quality 字典，可直接并入 run_report。
    """
    exams_all = str(input_cfg.get("exams_all_csv") or "duo_examen_raw_all.csv")
    exams_small = str(input_cfg.get("exams_small_csv") or "duo_examen_raw.csv")
    duplicate_brins = _collect_duplicate_brins_vo(data_root, exams_all, exams_small)
    missing = _missing_postcode_brins(rows_out)
    return {
        "duplicate_brin_in_source": {
            "count": len(duplicate_brins),
            "brins": _cap_list(duplicate_brins, max_brins_in_report),
        },
        "missing_postcode": {
            "count": len(missing),
            "brins": _cap_list(missing, max_brins_in_report),
        },
        "excluded_small_sample": {
            "count": len(excluded),
        },
    }


__all__ = ["run_po_quality", "run_vo_quality"]
