#!/usr/bin/env python3
"""
从 DUO 小学 Schooladviezen CSV 与 CBS WOZ 邮编数据计算每所小学的 X/Y 坐标。
- X：VWO 升学率（0–100%）= (VWO + 0.5×HAVO_VWO + 0.1×HAVO) / 总建议人数，按年加权。
- Y：学校邮编(PC4)对应的 WOZ 均值（千欧），按年加权；允许某年缺失（如 2024、2025 无 WOZ）。
- 输出 schools_xy_coords_po.csv，格式与中学 schools_xy_coords.csv 类似，命名区分小学(PO)。
"""
import csv
import json
import math
import os
from typing import Dict, List, Optional, Tuple

BASE = os.path.dirname(os.path.abspath(__file__))

# 学年标签 -> 用于 WOZ 的年份（1 月 1 日 peildatum）
SCHOOLJARS = [
    ("2019", "2020"),  # WOZ 用 2019
    ("2020", "2021"),  # WOZ 用 2020
    ("2021", "2022"),  # WOZ 用 2021
    ("2022", "2023"),  # WOZ 用 2022
    ("2023", "2024"),  # WOZ 用 2023
    ("2024", "2025"),  # WOZ 用 2024（当前无 WOZ 数据则自动跳过）
]
WOZ_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]  # 与 SCHOOLJARS 一一对应
# 按年权重：近年权重大
WEIGHTS = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]

MIN_PUPILS_TOTAL = 10  # 各年建议人数合计低于此的学校不输出


def parse_int(s: str) -> int:
    s = (s or "").strip().strip('"')
    if not s or s == "<5":
        return 2
    try:
        return int(s)
    except ValueError:
        return 0


def load_woz(base: str) -> Tuple[Dict[Tuple[str, int], float], List[int]]:
    """(pc4, year) -> woz_waarde；pc4 为 4 位字符串。返回 (woz_dict, 可用年份列表)。"""
    path = os.path.join(base, "cbs_woz_per_postcode_year.csv")
    if not os.path.exists(path):
        return {}, []
    out = {}
    years_set = set()
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            pc4 = (row.get("pc4") or "").strip()
            year = row.get("year")
            val = row.get("woz_waarde")
            if not pc4 or not year or not val:
                continue
            try:
                y = int(year)
                v = float(val)
                out[(pc4, y)] = v
                years_set.add(y)
            except (ValueError, TypeError):
                continue
    return out, sorted(years_set)


def get_woz_for_year(woz: Dict[Tuple[str, int], float], available_years: List[int], pc4: str, year: int) -> Optional[float]:
    """若 (pc4, year) 存在则返回；否则用该 pc4 下最近可用年份的 WOZ。"""
    if (pc4, year) in woz:
        return woz[(pc4, year)]
    if not available_years:
        return None
    # 找该 pc4 在 available_years 中任意一年的值（优先同年或最近年）
    best = None
    best_diff = 9999
    for ay in available_years:
        key = (pc4, ay)
        if key in woz:
            d = abs(ay - year)
            if d < best_diff:
                best_diff = d
                best = woz[key]
    return best


def load_schooladviezen(base: str) -> Dict[str, dict]:
    """
    读取所有 duo_schooladviezen_YYYY_YYYY.csv，按 BRIN 聚合。
    返回: brin -> { naam, gemeente, postcode, soort_po, years: { (start,end): { total, vwo_equiv } } }
    """
    schools: Dict[str, dict] = {}
    for start, end in SCHOOLJARS:
        path = os.path.join(base, f"duo_schooladviezen_{start}_{end}.csv")
        if not os.path.exists(path):
            continue
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(path, "r", encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=";", quotechar='"')
                    rows_list = list(reader)
                break
            except UnicodeDecodeError:
                continue
        else:
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

                vso = parse_int(row.get("VSO") or "")
                pro = parse_int(row.get("PRO") or "")
                vmbo_b = parse_int(row.get("VMBO_B") or "")
                vmbo_b_k = parse_int(row.get("VMBO_B_K") or "")
                vmbo_k = parse_int(row.get("VMBO_K") or "")
                vmbo_k_gt = parse_int(row.get("VMBO_K_GT") or "")
                vmbo_gt = parse_int(row.get("VMBO_GT") or "")
                vmbo_gt_havo = parse_int(row.get("VMBO_GT_HAVO") or "")
                havo = parse_int(row.get("HAVO") or "")
                havo_vwo = parse_int(row.get("HAVO_VWO") or "")
                vwo = parse_int(row.get("VWO") or "")
                niet = parse_int(row.get("ADVIES_NIET_MOGELIJK") or "")

                total = vso + pro + vmbo_b + vmbo_b_k + vmbo_k + vmbo_k_gt + vmbo_gt + vmbo_gt_havo + havo + havo_vwo + vwo + niet
                # VWO 升学等价人数：VWO=1，HAVO_VWO=0.5，HAVO=0.1
                vwo_equiv = vwo + 0.5 * havo_vwo + 0.1 * havo

                key = (start, end)
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


def main() -> int:
    base = BASE
    woz, woz_years = load_woz(base)
    if not woz:
        print("未找到 cbs_woz_per_postcode_year.csv，Y 将全部为 0")
        woz_years = []
    else:
        print(f"已加载 WOZ: {len(woz)} 条 (pc4, year)，可用年份: {woz_years}")

    schools = load_schooladviezen(base)
    if not schools:
        print("未找到任何 duo_schooladviezen_YYYY_YYYY.csv")
        return 1
    print(f"已加载小学: {len(schools)} 所，{sum(len(s['years']) for s in schools.values())} 条学年记录")

    rows_out: List[dict] = []
    excluded: List[dict] = []

    for brin in sorted(schools.keys()):
        data = schools[brin]
        years_data = data["years"]
        if not years_data:
            continue
        pupils_total = sum(y["total"] for y in years_data.values())
        if pupils_total < MIN_PUPILS_TOTAL:
            excluded.append({"BRIN": brin, "naam": data["naam"], "gemeente": data["gemeente"]})
            continue

        pc4 = data.get("pc4") or ""
        sum_w = 0.0
        sum_w_x = 0.0
        sum_w_y = 0.0
        sum_w_y_weights = 0.0
        for i, (start, end) in enumerate(SCHOOLJARS):
            key = (start, end)
            if key not in years_data:
                continue
            ydat = years_data[key]
            w = WEIGHTS[i]
            total = ydat["total"]
            if total <= 0:
                continue
            x_year = 100.0 * ydat["vwo_equiv"] / total
            sum_w += w
            sum_w_x += w * x_year

            woz_year = WOZ_YEARS[i]
            if pc4:
                woz_val = get_woz_for_year(woz, woz_years, pc4, woz_year)
                if woz_val is not None:
                    sum_w_y += w * woz_val
                    sum_w_y_weights += w

        x_linear = sum_w_x / sum_w if sum_w > 0 else 0.0
        # Y 仅用有 WOZ 的年份加权（允许年份缺失，如 2024/2025 无 WOZ）
        y_linear = sum_w_y / sum_w_y_weights if sum_w_y_weights > 0 else 0.0

        x_log = math.log10(1.0 + x_linear / 100.0)
        y_log = math.log10(1.0 + y_linear / 100.0) if y_linear > 0 else 0.0

        type_label = data.get("soort_po") or "Bo"
        if type_label not in ("Bo", "Sbo"):
            type_label = "Bo"

        postcode = (data.get("postcode") or "").strip()
        rows_out.append({
            "BRIN": brin,
            "vestigingsnaam": data["naam"],
            "gemeente": data["gemeente"],
            "postcode": postcode,
            "type": type_label,
            "X_linear": round(x_linear, 2),
            "Y_linear": round(y_linear, 2),
            "X_log": round(x_log, 4),
            "Y_log": round(y_log, 4),
            "pupils_total": pupils_total,
        })

    out_path = os.path.join(base, "schools_xy_coords_po.csv")
    fieldnames = ["BRIN", "vestigingsnaam", "gemeente", "postcode", "type", "X_linear", "Y_linear", "X_log", "Y_log", "pupils_total"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    excluded_path = os.path.join(base, "excluded_schools_po.json")
    with open(excluded_path, "w", encoding="utf-8") as f:
        json.dump(excluded, f, ensure_ascii=False, indent=0)
    if excluded:
        print(f"已排除样本过少学校 {len(excluded)} 所，列表: {excluded_path}")

    n = len(rows_out)
    print(f"已写入: {out_path}（共 {n} 所小学）")
    for r in rows_out[:5]:
        print(f"  {r['BRIN']} {r['vestigingsnaam']}: X={r['X_linear']}, Y={r['Y_linear']} ({r['type']})")
    if n > 5:
        print(f"  ... 等共 {n} 所")
    return 0


if __name__ == "__main__":
    exit(main())
