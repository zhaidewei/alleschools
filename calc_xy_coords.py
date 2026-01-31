#!/usr/bin/env python3
"""
从 duo_examen_raw.csv 计算每所学校的 X（VWO 通过人数占比）和 Y（理科占比）。
- 横坐标 X：VWO 通过人数 / 全校考生总数（HAVO+VWO+VMBO 等所有类型），0–100%。
- 纵坐标 Y：理科通过人数 / 全校考生总数（0–100%）。
- 仅 HAVO+VWO 参与 X/Y 计算；VMBO 学校作为参考保留，X=0，Y=VMBO 内 techniek 占比。
- 历史年份加权平均：最近年份权重大，逐年递减。
- 输出线性坐标与对数坐标（log10(1+x)），并写入新 CSV。
"""
import csv
import json
import math
import os

# DUO CSV 列索引（0-based）。无表头，顺序与 DUO 官方一致。
COL_INSTELLING = 0
COL_VESTIGING = 1
COL_NAAM = 2
COL_GEMEENTE = 3
COL_ONDERWIJSTYPE = 4
COL_OPLEIDINGSNAAM = 6
# 每年 9 列：MAN kand, MAN geslaagd, MAN %, VROUW kand, VROUW geslaagd, VROUW %, TOTAAL kand, TOTAAL geslaagd, TOTAAL %
# (TOTAAL examenkandidaten 列, TOTAAL geslaagden 列, 学年名)。X 轴用 geslaagden 算 VWO 占比，便于区分纯 VWO 校；阈值仍用 kand 总数。
YEAR_COLS = [
    (13, 14, "2019-2020"),
    (22, 23, "2020-2021"),
    (31, 32, "2021-2022"),
    (40, 41, "2022-2023"),
    (49, 50, "2023-2024"),
]
# 权重：最近年份高，历史递减
WEIGHTS = [0.2, 0.4, 0.6, 0.8, 1.0]
# HAVO/VWO 总考生数低于此阈值的学校不输出（避免单一/极小样本导致 100/100 等异常点）
MIN_HAVO_VWO_TOTAL = 20


def parse_int(s):
    s = (s or "").strip().strip('"')
    if not s or s == "<5":
        return 2  # DUO 隐私，按 2 计
    try:
        return int(s)
    except ValueError:
        return 0


def is_havo_vwo(otype):
    return (otype or "").strip().strip('"').upper() in ("HAVO", "VWO")


def is_vmbo(otype):
    return (otype or "").strip().strip('"').upper() == "VMBO"


def is_science_havo_vwo(opleiding):
    """HAVO/VWO 理科：N&T, N&G, N&T/N&G"""
    o = (opleiding or "").upper()
    return "N&T" in o and "N&G" in o or "N&T" in o or "N&G" in o


def is_science_vmbo(opleiding):
    """VMBO 理科：techniek"""
    return "techniek" in (opleiding or "").lower()


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    # 优先用全量数据，否则用 Amstelveen 四校
    inp_all = os.path.join(base, "duo_examen_raw_all.csv")
    inp_small = os.path.join(base, "duo_examen_raw.csv")
    inp = inp_all if os.path.exists(inp_all) else inp_small
    out = os.path.join(base, "schools_xy_coords.csv")

    if not os.path.exists(inp):
        print(f"找不到输入文件。请放置 duo_examen_raw_all.csv 或 duo_examen_raw.csv")
        return 1

    print(f"输入: {os.path.basename(inp)}")

    # 按学校聚合：brin -> { "naam", "gemeente", "havo_vwo": { year: { vwo, havo, science, total } }, "vmbo": { year: { techniek, total } } }
    schools = {}
    skip_header = True

    with open(inp, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        for row in reader:
            if len(row) <= 49:
                continue
            # 若有表头则跳过第一行
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
                    "havo_vwo": {y: {"vwo": 0, "havo": 0, "science": 0, "total": 0} for (_, _, y) in YEAR_COLS},
                    "vmbo": {y: {"techniek": 0, "total": 0} for (_, _, y) in YEAR_COLS},
                    "all_kand": {y: 0 for (_, _, y) in YEAR_COLS},  # 全校考生总数（所有类型）
                }

            for i, (col_kand, col_geslaagd, year) in enumerate(YEAR_COLS):
                n_kand = parse_int(row[col_kand])
                n_geslaagd = parse_int(row[col_geslaagd])
                schools[brin]["all_kand"][year] += n_kand  # 全校考生数（每行都累加）

                if is_havo_vwo(otype):
                    schools[brin]["havo_vwo"][year]["total"] += n_kand  # 阈值用考生总数
                    if otype.strip().strip('"').upper() == "VWO":
                        schools[brin]["havo_vwo"][year]["vwo"] += n_geslaagd  # X 分子：VWO 通过人数
                    else:
                        schools[brin]["havo_vwo"][year]["havo"] += n_geslaagd
                    if is_science_havo_vwo(opleiding):
                        schools[brin]["havo_vwo"][year]["science"] += n_geslaagd
                elif is_vmbo(otype):
                    schools[brin]["vmbo"][year]["total"] += n_kand
                    if is_science_vmbo(opleiding):
                        schools[brin]["vmbo"][year]["techniek"] += n_kand

    # 计算每校加权平均 X, Y（线性），再算对数坐标
    rows_out = []
    excluded_low_sample = []  # 因 HAVO/VWO 考生数过少而排除的学校
    for brin, data in sorted(schools.items()):
        hw = data["havo_vwo"]
        vmbo = data["vmbo"]

        total_havo_vwo = sum(hw[y]["total"] for (_, _, y) in YEAR_COLS)  # 阈值：HAVO/VWO 考生总数

        if total_havo_vwo >= MIN_HAVO_VWO_TOTAL:
            # HAVO/VWO 学校：X = VWO 通过人数 / 全校考生总数；Y = 理科通过人数 / 全校考生总数
            sum_w = 0
            sum_w_x = 0.0
            sum_w_y = 0.0
            all_kand = data["all_kand"]
            for i, (_, _, year) in enumerate(YEAR_COLS):
                w = WEIGHTS[i]
                vwo_g = hw[year]["vwo"]
                t_all = all_kand[year]  # 全校考生总数（HAVO+VWO+VMBO 等）
                if t_all <= 0:
                    continue
                x_year = 100.0 * vwo_g / t_all  # X = VWO 通过人数 / 全校考生数
                y_year = 100.0 * hw[year]["science"] / t_all  # Y = 理科通过人数 / 全校考生数
                sum_w += w
                sum_w_x += w * x_year
                sum_w_y += w * y_year
            x_linear = sum_w_x / sum_w if sum_w > 0 else 0.0
            y_linear = sum_w_y / sum_w if sum_w > 0 else 0.0
            type_label = "HAVO/VWO"
        elif sum(vmbo[y]["total"] for (_, _, y) in YEAR_COLS) > 0:
            # 仅 VMBO：X=0，Y=VMBO 内 techniek 占比（加权）
            sum_w = 0
            sum_w_y = 0.0
            for i, (_, _, year) in enumerate(YEAR_COLS):
                w = WEIGHTS[i]
                t = vmbo[year]["total"]
                if t <= 0:
                    continue
                tech = vmbo[year]["techniek"]
                y_year = 100.0 * tech / t if t else 0
                sum_w += w
                sum_w_y += w * y_year
            x_linear = 0.0
            y_linear = (sum_w_y / sum_w) if sum_w > 0 else 0.0
            type_label = "VMBO"
        else:
            excluded_low_sample.append({
                "BRIN": brin,
                "naam": data["naam"],
                "gemeente": data["gemeente"],
            })
            continue

        # 对数坐标：log10(1 + x)，避免 log(0)。这里 x 已是 0–100，用 log10(1 + x/100) 使结果约在 0–2
        x_log = math.log10(1.0 + x_linear / 100.0)
        y_log = math.log10(1.0 + y_linear / 100.0)

        # 5 年考生总数（毕业年级人数），用于图表中点的大小
        candidates_total = sum(data["all_kand"][year] for (_, _, year) in YEAR_COLS)

        rows_out.append({
            "BRIN": brin,
            "vestigingsnaam": data["naam"],
            "gemeente": data["gemeente"],
            "type": type_label,
            "X_linear": round(x_linear, 2),
            "Y_linear": round(y_linear, 2),
            "X_log": round(x_log, 4),
            "Y_log": round(y_log, 4),
            "candidates_total": candidates_total,
        })

    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["BRIN", "vestigingsnaam", "gemeente", "type", "X_linear", "Y_linear", "X_log", "Y_log", "candidates_total"])
        writer.writeheader()
        writer.writerows(rows_out)

    excluded_path = os.path.join(base, "excluded_schools.json")
    with open(excluded_path, "w", encoding="utf-8") as f:
        json.dump(excluded_low_sample, f, ensure_ascii=False, indent=0)
    if excluded_low_sample:
        print(f"已排除样本过少学校 {len(excluded_low_sample)} 所，列表写入: {excluded_path}")

    n = len(rows_out)
    print(f"已写入: {out}（共 {n} 所学校）")
    if n <= 10:
        for r in rows_out:
            print(f"  {r['BRIN']} {r['vestigingsnaam']}: X={r['X_linear']}, Y={r['Y_linear']} ({r['type']})")
    else:
        for r in rows_out[:5]:
            print(f"  {r['BRIN']} {r['vestigingsnaam']}: X={r['X_linear']}, Y={r['Y_linear']} ({r['type']})")
        print(f"  ... 等共 {n} 所")
    return 0


if __name__ == "__main__":
    exit(main())
