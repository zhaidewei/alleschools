import sqlite3

from alleschools.fetch_cbs_woz import YEARS_ZIP, extract_woz_from_gpkg


def test_current_cbs_pc4_archives_are_configured():
    assert YEARS_ZIP[2019] == "2026-cbs_pc4_2019_vol.zip"
    assert YEARS_ZIP[2020] == "2026-cbs_pc4_2020_vol.zip"
    assert YEARS_ZIP[2024] == "2026-cbs_pc4_2024_v2.zip"
    assert YEARS_ZIP[2025] == "2026-cbs_pc4_2025_v1.zip"


def test_extract_woz_skips_cbs_missing_codes(tmp_path):
    gpkg = tmp_path / "sample.gpkg"
    conn = sqlite3.connect(gpkg)
    conn.execute(
        "CREATE TABLE cbs_pc4_2025 "
        "(postcode INTEGER, gemiddelde_woz_waarde_woning INTEGER)"
    )
    conn.executemany(
        "INSERT INTO cbs_pc4_2025 VALUES (?, ?)",
        [(1011, 525), (1012, -99995), (1013, -99997)],
    )
    conn.commit()
    conn.close()

    assert extract_woz_from_gpkg(str(gpkg), 2025) == [("1011", 2025, 525.0)]
