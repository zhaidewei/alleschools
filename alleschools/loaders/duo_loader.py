from __future__ import annotations

"""
DUO Schooladviezen (PO) 加载。

负责从 duo_schooladviezen_YYYY_YYYY.csv 中按 BRIN 聚合出：
    brin -> {
        "naam": ...,
        "gemeente": ...,
        "postcode": ...,
        "pc4": ...,
        "soort_po": ...,
        "years": { (start, end): { "total": int, "vwo_equiv": float } }
    }
"""

import csv
import os
from typing import Dict, List, Tuple

from alleschools.config import SCHOOLJARS


def _parse_int(s: str) -> int:
    s = (s or "").strip().strip('"')
    if not s or s == "<5":
        return 2
    try:
        return int(s)
    except ValueError:
        return 0


def load_schooladviezen_po(base_dir: str) -> Dict[str, dict]:
    """
    读取所有 duo_schooladviezen_YYYY_YYYY.csv，按 BRIN 聚合。

    参数:
        base_dir: CSV 所在目录，一般为项目根目录。

    返回:
        brin -> { naam, gemeente, postcode, pc4, soort_po, years: { (start,end): { total, vwo_equiv } } }
    """
    schools: Dict[str, dict] = {}

    for start, end in SCHOOLJARS:
        path = os.path.join(base_dir, f"duo_schooladviezen_{start}_{end}.csv")
        if not os.path.exists(path):
            continue

        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(path, "r", encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=";", quotechar='"')
                    rows_list: List[dict] = list(reader)
                break
            except UnicodeDecodeError:
                continue
        else:
            # 所有编码尝试失败，跳过该年份
            continue

        for row in rows_list:
            # 新表头: INSTELLINGSCODE + VESTIGINGSCODE；旧表头: BRIN_NUMMER + VESTIGINGSNUMMER
            inst = (row.get("INSTELLINGSCODE") or row.get("BRIN_NUMMER") or "").strip().strip('"')
            vest = (row.get("VESTIGINGSCODE") or row.get("VESTIGINGSNUMMER") or "").strip().strip('"')
            brin = (inst + vest) if (inst + vest) else (row.get("BRIN_NUMMER") or "").strip().strip('"')
            if not brin:
                continue

            naam = (row.get("INSTELLINGSNAAM_VESTIGING") or "").strip().strip('"')
            gemeente = (row.get("GEMEENTENAAM") or "").strip().strip('"')
            postcode = (row.get("POSTCODE_VESTIGING") or "").strip().strip('"').replace(" ", "")
            soort = (row.get("SOORT_PO") or "").strip().strip('"')
            pc4 = postcode[:4] if len(postcode) >= 4 else ""

            vso = _parse_int(row.get("VSO") or "")
            pro = _parse_int(row.get("PRO") or "")
            vmbo_b = _parse_int(row.get("VMBO_B") or "")
            vmbo_b_k = _parse_int(row.get("VMBO_B_K") or "")
            vmbo_k = _parse_int(row.get("VMBO_K") or "")
            vmbo_k_gt = _parse_int(row.get("VMBO_K_GT") or "")
            vmbo_gt = _parse_int(row.get("VMBO_GT") or "")
            vmbo_gt_havo = _parse_int(row.get("VMBO_GT_HAVO") or "")
            havo = _parse_int(row.get("HAVO") or "")
            havo_vwo = _parse_int(row.get("HAVO_VWO") or "")
            vwo = _parse_int(row.get("VWO") or "")
            niet = _parse_int(row.get("ADVIES_NIET_MOGELIJK") or "")

            total = (
                vso
                + pro
                + vmbo_b
                + vmbo_b_k
                + vmbo_k
                + vmbo_k_gt
                + vmbo_gt
                + vmbo_gt_havo
                + havo
                + havo_vwo
                + vwo
                + niet
            )
            # VWO 升学等价人数：VWO=1，HAVO_VWO=0.5，HAVO=0.1
            vwo_equiv = vwo + 0.5 * havo_vwo + 0.1 * havo

            key: Tuple[str, str] = (start, end)
            if brin not in schools:
                schools[brin] = {
                    "naam": naam,
                    "gemeente": gemeente,
                    "postcode": postcode,
                    "pc4": pc4,
                    "soort_po": soort,
                    "years": {},
                }
            schools[brin]["years"][key] = {"total": total, "vwo_equiv": vwo_equiv}

    return schools


__all__ = ["load_schooladviezen_po"]

