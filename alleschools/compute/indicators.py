from __future__ import annotations

"""
核心指标计算。

本文件暂时只实现 PO 版本的 X/Y 计算逻辑，
未来可以在此扩展时间序列、缺失值策略等。
"""

from typing import Any, Dict, Iterable, List, Sequence, Tuple

from alleschools.config import SCHOOLJARS, WEIGHTS, WOZ_YEARS, MIN_PUPILS_TOTAL


def get_woz_for_year(
    woz: Dict[Tuple[str, int], float],
    available_years: List[int],
    pc4: str,
    year: int,
) -> float | None:
    """若 (pc4, year) 存在则返回；否则用该 pc4 下最近可用年份的 WOZ。"""
    if (pc4, year) in woz:
        return woz[(pc4, year)]
    if not available_years:
        return None
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


def _compute_percentile(values: Sequence[float], p: float) -> float:
    """简单百分位数计算（0–100），用于异常值截断。"""
    if not values:
        return 0.0
    vals = sorted(values)
    if p <= 0:
        return vals[0]
    if p >= 100:
        return vals[-1]
    k = (p / 100.0) * (len(vals) - 1)
    i = int(k)
    f = k - i
    if i + 1 < len(vals):
        return vals[i] + f * (vals[i + 1] - vals[i])
    return vals[i]


def _apply_outlier_clipping(
    rows: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    outliers: Dict[str, Any] | None,
) -> None:
    """
    在 rows 上就地对 X/Y 进行按百分位数的截断（winsorize）。

    outliers.clip_percentiles: [low, high]（例如 [1, 99]）
    """
    if not outliers:
        return
    clip = outliers.get("clip_percentiles")
    if (
        not isinstance(clip, (list, tuple))
        or len(clip) != 2
        or not all(isinstance(v, (int, float)) for v in clip)
    ):
        return
    low_p, high_p = float(clip[0]), float(clip[1])
    if not (0.0 <= low_p < high_p <= 100.0):
        return

    x_vals = [float(r[x_key]) for r in rows if isinstance(r.get(x_key), (int, float))]
    y_vals = [float(r[y_key]) for r in rows if isinstance(r.get(y_key), (int, float))]
    if not x_vals and not y_vals:
        return

    x_lo = _compute_percentile(x_vals, low_p) if x_vals else 0.0
    x_hi = _compute_percentile(x_vals, high_p) if x_vals else 0.0
    y_lo = _compute_percentile(y_vals, low_p) if y_vals else 0.0
    y_hi = _compute_percentile(y_vals, high_p) if y_vals else 0.0

    for row in rows:
        if isinstance(row.get(x_key), (int, float)):
            x = float(row[x_key])
            x_clipped = min(max(x, x_lo), x_hi)
            row[x_key] = round(x_clipped, 2)
        if isinstance(row.get(y_key), (int, float)):
            y = float(row[y_key])
            y_clipped = min(max(y, y_lo), y_hi)
            row[y_key] = round(y_clipped, 2)


def compute_po_xy(
    schools: Dict[str, dict],
    woz: Dict[Tuple[str, int], float],
    woz_years: Iterable[int],
    woz_strategy: str = "nearest_year",
    outliers: Dict[str, Any] | None = None,
) -> Tuple[List[dict], List[dict]]:
    """
    根据小学 Schooladviezen 与 WOZ 数据计算 X/Y。

    返回:
        rows_out: 可直接用于写 CSV 的行列表
        excluded: 因样本过少被排除的学校列表
    """
    rows_out: List[dict] = []
    excluded: List[dict] = []

    woz_years_list = list(woz_years)
    # 预计算每个 PC4 的 WOZ 平均值（用于 pc4_mean 策略）
    pc4_means: Dict[str, float] = {}
    if woz_strategy == "pc4_mean":
        sums: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for (pc4_key, _year), value in woz.items():
            sums[pc4_key] = sums.get(pc4_key, 0.0) + float(value)
            counts[pc4_key] = counts.get(pc4_key, 0) + 1
        for pc4_key, total in sums.items():
            c = counts.get(pc4_key, 0)
            if c > 0:
                pc4_means[pc4_key] = total / c

    for brin in sorted(schools.keys()):
        data = schools[brin]
        years_data = data["years"]
        if not years_data:
            continue

        pupils_total = sum(y["total"] for y in years_data.values())
        if pupils_total < MIN_PUPILS_TOTAL:
            excluded.append(
                {"BRIN": brin, "naam": data["naam"], "gemeente": data["gemeente"]}
            )
            continue

        pc4 = data.get("pc4") or ""
        sum_w = 0.0
        sum_w_x = 0.0
        sum_w_y = 0.0
        sum_w_y_weights = 0.0
        years_used: List[str] = []
        n_years_with_woz = 0

        for i, (start, end) in enumerate(SCHOOLJARS):
            key = (start, end)
            if key not in years_data:
                continue
            ydat = years_data[key]
            w = WEIGHTS[i]
            total = ydat["total"]
            if total <= 0:
                continue

            years_used.append(f"{start}-{end}")
            x_year = 100.0 * ydat["vwo_equiv"] / total
            sum_w += w
            sum_w_x += w * x_year

            woz_year = WOZ_YEARS[i]
            if pc4:
                if woz_strategy == "nearest_year":
                    woz_val = get_woz_for_year(woz, woz_years_list, pc4, woz_year)
                elif woz_strategy == "drop":
                    # 仅接受精确年份匹配
                    woz_val = woz.get((pc4, woz_year))
                elif woz_strategy == "pc4_mean":
                    # 优先使用精确年份；缺失则退回到该 PC4 的平均值
                    woz_val = woz.get((pc4, woz_year))
                    if woz_val is None:
                        woz_val = pc4_means.get(pc4)
                else:
                    # 未知策略时回退到当前默认行为（nearest_year）
                    woz_val = get_woz_for_year(woz, woz_years_list, pc4, woz_year)

                if woz_val is not None:
                    sum_w_y += w * woz_val
                    sum_w_y_weights += w
                    n_years_with_woz += 1

        x_linear = sum_w_x / sum_w if sum_w > 0 else 0.0
        y_linear = sum_w_y / sum_w_y_weights if sum_w_y_weights > 0 else 0.0

        type_label = data.get("soort_po") or "Bo"
        if type_label not in ("Bo", "Sbo"):
            type_label = "Bo"

        postcode = (data.get("postcode") or "").strip()
        years_covered_str = ",".join(years_used) if years_used else ""
        has_full_woz = bool(pc4 and len(years_used) > 0 and n_years_with_woz == len(years_used))

        row: Dict[str, Any] = {
            "BRIN": brin,
            "vestigingsnaam": data["naam"],
            "gemeente": data["gemeente"],
            "postcode": postcode,
            "type": type_label,
            "X_linear": round(x_linear, 2),
            "Y_linear": round(y_linear, 2),
            "pupils_total": pupils_total,
        }
        row["years_covered"] = years_covered_str
        row["has_full_woz"] = has_full_woz
        row["data_quality_flags"] = ""
        rows_out.append(row)

    if outliers:
        _apply_outlier_clipping(rows_out, "X_linear", "Y_linear", outliers)

    return rows_out, excluded


def compute_vo_xy(
    schools: Dict[str, dict],
    brin_to_postcode: Dict[str, str],
    year_cols: List[Any],
    min_havo_vwo_total: int,
    outliers: Dict[str, Any] | None = None,
) -> Tuple[List[dict], List[dict]]:
    """
    根据 VO 考试聚合数据计算每校 X/Y（线性与对数坐标）。

    year_cols: 每项 [col_kand, col_geslaagd, year_label, weight]，与 load_exam_schools 一致。
    返回 (rows_out, excluded)。
    """
    rows_out: List[dict] = []
    excluded: List[dict] = []

    for brin in sorted(schools.keys()):
        data = schools[brin]
        hw = data["havo_vwo"]
        vmbo = data["vmbo"]
        year_labels = [y[2] for y in year_cols]
        weights = [float(y[3]) for y in year_cols]

        total_havo_vwo = sum(hw[y]["total"] for y in year_labels)
        all_kand = data["all_kand"]

        years_used_vo: List[str] = []
        if total_havo_vwo >= min_havo_vwo_total:
            sum_w = 0.0
            sum_w_x = 0.0
            sum_w_y = 0.0
            for i, year in enumerate(year_labels):
                w = weights[i]
                vwo_g = hw[year]["vwo"]
                t_all = all_kand[year]
                if t_all <= 0:
                    continue
                years_used_vo.append(year)
                x_year = 100.0 * vwo_g / t_all
                y_year = 100.0 * hw[year]["science"] / t_all
                sum_w += w
                sum_w_x += w * x_year
                sum_w_y += w * y_year
            x_linear = sum_w_x / sum_w if sum_w > 0 else 0.0
            y_linear = sum_w_y / sum_w if sum_w > 0 else 0.0
            type_label = "HAVO/VWO"
        elif sum(vmbo[y]["total"] for y in year_labels) > 0:
            sum_w = 0.0
            sum_w_y = 0.0
            for i, year in enumerate(year_labels):
                w = weights[i]
                t = vmbo[year]["total"]
                if t <= 0:
                    continue
                years_used_vo.append(year)
                tech = vmbo[year]["techniek"]
                y_year = 100.0 * tech / t
                sum_w += w
                sum_w_y += w * y_year
            x_linear = 0.0
            y_linear = sum_w_y / sum_w if sum_w > 0 else 0.0
            type_label = "VMBO"
        else:
            excluded.append({
                "BRIN": brin,
                "naam": data["naam"],
                "gemeente": data["gemeente"],
            })
            continue

        candidates_total = sum(all_kand[y] for y in year_labels)
        postcode = brin_to_postcode.get(brin, "")
        years_covered_str = ",".join(years_used_vo) if years_used_vo else ""

        row_vo: Dict[str, Any] = {
            "BRIN": brin,
            "vestigingsnaam": data["naam"],
            "gemeente": data["gemeente"],
            "postcode": postcode,
            "type": type_label,
            "X_linear": round(x_linear, 2),
            "Y_linear": round(y_linear, 2),
            "candidates_total": candidates_total,
        }
        row_vo["years_covered"] = years_covered_str
        row_vo["data_quality_flags"] = ""
        rows_out.append(row_vo)

    if outliers:
        _apply_outlier_clipping(rows_out, "X_linear", "Y_linear", outliers)

    return rows_out, excluded


__all__ = ["get_woz_for_year", "compute_po_xy", "compute_vo_xy"]

