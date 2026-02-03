from __future__ import annotations

"""P2-1：X/Y 异常值截断（winsorization）策略测试。"""

from pathlib import Path

from alleschools.compute.indicators import compute_po_xy, compute_vo_xy


def test_compute_po_xy_outliers_clip_percentiles() -> None:
    """配置 outliers.clip_percentiles 时，PO X/Y 会被按百分位数截断。"""
    # 构造 5 所学校，X 值从 0 到 100，便于观察截断效果。
    schools = {}
    for i, x in enumerate([0, 25, 50, 75, 100]):
        brin = f"00A{i}"
        schools[brin] = {
            "naam": f"S{i}",
            "gemeente": "G",
            "postcode": "1234AB",
            "pc4": "1234",
            "soort_po": "Bo",
            "years": {("2019", "2020"): {"total": 100, "vwo_equiv": x}},
        }
    # 不关心 Y，WOZ 留空并使用 drop 策略使其为 0
    woz = {}
    woz_years = []
    rows, _ = compute_po_xy(
        schools,
        woz,
        woz_years,
        woz_strategy="drop",
        outliers={"clip_percentiles": [20, 80]},
    )
    xs = sorted(r["X_linear"] for r in rows)
    # 20/80 百分位应介于第二/第四个值附近，最小/最大被抬高/压低
    assert xs[0] > 0.0
    assert xs[-1] < 100.0
    # 所有值仍在原始范围内
    assert 0.0 <= xs[0] <= xs[-1] <= 100.0


def test_compute_vo_xy_outliers_clip_percentiles() -> None:
    """配置 outliers.clip_percentiles 时，VO X/Y 也会被截断。"""
    year_cols = [[0, 1, "2019-2020", 1.0]]
    year_label = "2019-2020"

    def mk_school(brin: str, vwo_share: float) -> dict:
        # vwo_share 以 0–100 表示百分比
        vwo = vwo_share
        total = 100.0
        return {
            "naam": brin,
            "gemeente": "G",
            "havo_vwo": {
                year_label: {"vwo": vwo, "havo": 0.0, "science": 0.0, "total": total},
            },
            "vmbo": {year_label: {"techniek": 0.0, "total": 0.0}},
            "all_kand": {year_label: total},
        }

    schools = {
        "00V0": mk_school("00V0", 0.0),
        "00V1": mk_school("00V1", 25.0),
        "00V2": mk_school("00V2", 50.0),
        "00V3": mk_school("00V3", 75.0),
        "00V4": mk_school("00V4", 100.0),
    }

    rows, _ = compute_vo_xy(
        schools,
        brin_to_postcode={},
        year_cols=year_cols,
        min_havo_vwo_total=1,
        outliers={"clip_percentiles": [20, 80]},
    )
    xs = sorted(r["X_linear"] for r in rows)
    assert xs[0] > 0.0
    assert xs[-1] < 100.0
    assert 0.0 <= xs[0] <= xs[-1] <= 100.0

