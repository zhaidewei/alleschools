"""
VO（中学）考试数据加载。

- 从 duo_vestigingen_vo.csv 加载 VESTIGINGSCODE -> POSTCODE
- 从 duo_examen_raw_all.csv / duo_examen_raw.csv 按学校聚合 HAVO/VWO/VMBO 与理科数据
"""

from __future__ import annotations

import csv
import os
from typing import Any, Dict, List, Union

# DUO 考试 CSV 列索引（0-based）
COL_INSTELLING = 0
COL_VESTIGING = 1
COL_NAAM = 2
COL_GEMEENTE = 3
COL_ONDERWIJSTYPE = 4
COL_OPLEIDINGSNAAM = 6


def _parse_int(s: Union[str, None]) -> int:
    s = (s or "").strip().strip('"')
    if not s or s == "<5":
        return 2
    try:
        return int(s)
    except ValueError:
        return 0


def is_havo_vwo(otype: Union[str, None]) -> bool:
    return (otype or "").strip().strip('"').upper() in ("HAVO", "VWO")


def is_vmbo(otype: Union[str, None]) -> bool:
    return (otype or "").strip().strip('"').upper() == "VMBO"


def is_science_havo_vwo(opleiding: Union[str, None]) -> bool:
    o = (opleiding or "").upper()
    return "N&T" in o and "N&G" in o or "N&T" in o or "N&G" in o


def is_science_vmbo(opleiding: Union[str, None]) -> bool:
    return "techniek" in (opleiding or "").lower()


def load_vestigingen_postcode(
    base_dir: str,
    vestigingen_csv: str = "duo_vestigingen_vo.csv",
) -> Dict[str, str]:
    """
    从指定 CSV 加载 VESTIGINGSCODE -> POSTCODE。
    返回 dict，无文件或无数据则返回空 dict。
    """
    path = os.path.join(base_dir, vestigingen_csv)
    out: Dict[str, str] = {}
    if not os.path.exists(path):
        return out
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc) as f:
                reader = csv.DictReader(f, delimiter=";", quotechar='"')
                for row in reader:
                    vest = (row.get("VESTIGINGSCODE") or "").strip().strip('"')
                    pc = (row.get("POSTCODE") or "").strip().strip('"')
                    if vest:
                        out[vest] = pc
            break
        except UnicodeDecodeError:
            continue
    return out


def load_exam_schools(
    base_dir: str,
    exams_all_csv: str,
    exams_small_csv: str,
    year_cols: List[Any],
) -> Dict[str, dict]:
    """
    从考试 CSV 按学校聚合，得到 brin -> { naam, gemeente, havo_vwo, vmbo, all_kand }。

    year_cols: 来自配置的 weights.year_cols，每项 [col_kand, col_geslaagd, year_label, weight]。
    """
    inp_all = os.path.join(base_dir, exams_all_csv)
    inp_small = os.path.join(base_dir, exams_small_csv)
    inp = inp_all if os.path.exists(inp_all) else inp_small
    if not os.path.exists(inp):
        return {}

    schools: Dict[str, dict] = {}
    year_labels = [y[2] for y in year_cols]

    with open(inp, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        skip_header = True
        for row in reader:
            if len(row) <= 49:
                continue
            if skip_header and (row[COL_INSTELLING] or "").strip().strip('"').upper() == "INSTELLINGSCODE":
                skip_header = False
                continue
            skip_header = False

            brin = (row[COL_VESTIGING] or "").strip().strip('"')
            naam = (row[COL_NAAM] or "").strip().strip('"')
            gemeente = (row[COL_GEMEENTE] or "").strip().strip('"')
            otype = (row[COL_ONDERWIJSTYPE] or "").strip().strip('"')
            opleiding = (row[COL_OPLEIDINGSNAAM] or "").strip().strip('"')

            if brin not in schools:
                schools[brin] = {
                    "naam": naam,
                    "gemeente": gemeente,
                    "havo_vwo": {y: {"vwo": 0, "havo": 0, "science": 0, "total": 0} for y in year_labels},
                    "vmbo": {y: {"techniek": 0, "total": 0} for y in year_labels},
                    "all_kand": {y: 0 for y in year_labels},
                }

            for y in year_cols:
                col_kand, col_geslaagd, year = int(y[0]), int(y[1]), y[2]
                n_kand = _parse_int(row[col_kand] if col_kand < len(row) else "")
                n_geslaagd = _parse_int(row[col_geslaagd] if col_geslaagd < len(row) else "")
                schools[brin]["all_kand"][year] += n_kand
                if is_havo_vwo(otype):
                    schools[brin]["havo_vwo"][year]["total"] += n_kand
                    if (otype or "").strip().strip('"').upper() == "VWO":
                        schools[brin]["havo_vwo"][year]["vwo"] += n_geslaagd
                    else:
                        schools[brin]["havo_vwo"][year]["havo"] += n_geslaagd
                    if is_science_havo_vwo(opleiding):
                        schools[brin]["havo_vwo"][year]["science"] += n_geslaagd
                elif is_vmbo(otype):
                    schools[brin]["vmbo"][year]["total"] += n_kand
                    if is_science_vmbo(opleiding):
                        schools[brin]["vmbo"][year]["techniek"] += n_kand

    return schools


__all__ = [
    "load_vestigingen_postcode",
    "load_exam_schools",
    "_parse_int",
    "is_havo_vwo",
    "is_vmbo",
    "is_science_havo_vwo",
    "is_science_vmbo",
]
