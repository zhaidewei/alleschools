#!/usr/bin/env python3
"""
从 CBS 下载邮编级「Gemiddelde WOZ-waarde woning」数据，按 PC4 和年份提取，
输出 cbs_woz_per_postcode_year.csv（pc4, year, woz_waarde，单位：千欧）。
数据源: https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/gegevens-per-postcode
Zip 内为 Geopackage，用 sqlite3 读取表 postcode + gemiddelde_woz_waarde_woning。

年份说明（维护时参考）：
- 2024：当前 v1 中 WOZ 为 CBS 待发布编码(-99995)，脚本会下载但有效条数为 0；
  等 CBS 发布 2024 的 v2（或更新 zip）且含 WOZ 后，再跑脚本即可；若 zip 名变更需改 YEARS_ZIP。
- 2025：peildatum 1 januari 2025 的邮编数据尚未发布，通常会在 2026 年放出（如 2026-cbs_pc4_2025_v1.zip），
  届时可将 2025 加入 YEARS_ZIP。
- 查最新发布与 zip 名：https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/gegevens-per-postcode
"""
import csv
import os
import sqlite3
import tempfile
import urllib.request
import zipfile
from typing import List, Tuple

BASE_URL = "https://download.cbs.nl/postcode"

# 年份 -> zip 文件名（不含路径）。详见本文件顶部 docstring 中「年份说明」
YEARS_ZIP = {
    2024: "2025-cbs_pc4_2024_v1.zip",
    2023: "2025-cbs_pc4_2023_v2.zip",
    2022: "2025-cbs_pc4_2022_vol.zip",
    2021: "2024-cbs_pc4_2021_vol.zip",
}

# CBS 保密/待发布编码，不写入最终 CSV
WOZ_MISSING = (-99997, -99995)


def find_data_table(conn):
    """在 Geopackage 中找到含 postcode 与 gemiddelde_woz_waarde_woning 的表名。"""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cbs%'")
    for (name,) in cur.fetchall():
        cur.execute("PRAGMA table_info(%s)" % name)
        cols = [row[1] for row in cur.fetchall()]
        if "postcode" in cols and "gemiddelde_woz_waarde_woning" in cols:
            return name
    return None


def extract_woz_from_gpkg(gpkg_path: str, year: int) -> List[Tuple[str, int, float]]:
    """从单个 .gpkg 提取 (pc4, year, woz_waarde)。woz 无效则跳过。"""
    conn = sqlite3.connect(gpkg_path)
    table = find_data_table(conn)
    if not table:
        conn.close()
        return []
    cur = conn.cursor()
    cur.execute(
        "SELECT postcode, gemiddelde_woz_waarde_woning FROM %s" % table
    )
    rows = []
    for (postcode, woz) in cur.fetchall():
        if postcode is None or woz is None:
            continue
        if woz in WOZ_MISSING or (isinstance(woz, (int, float)) and woz < 0):
            continue
        pc4 = str(int(postcode)).zfill(4)  # 1011 -> "1011"
        rows.append((pc4, year, float(woz)))
    conn.close()
    return rows


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base, "cbs_woz_per_postcode_year.csv")

    all_rows = []  # (pc4, year, woz_waarde)

    with tempfile.TemporaryDirectory() as tmpdir:
        for year, zip_name in sorted(YEARS_ZIP.items()):
            url = f"{BASE_URL}/{zip_name}"
            zip_path = os.path.join(tmpdir, zip_name)
            try:
                print(f"正在下载: {zip_name}")
                urllib.request.urlretrieve(url, zip_path)
            except Exception as e:
                print(f"  下载失败: {e}")
                continue
            if not zipfile.is_zipfile(zip_path):
                print(f"  无效 zip: {zip_path}")
                continue
            with zipfile.ZipFile(zip_path, "r") as z:
                gpkg_names = [n for n in z.namelist() if n.endswith(".gpkg")]
                if not gpkg_names:
                    print(f"  未找到 .gpkg: {zip_name}")
                    continue
                z.extract(gpkg_names[0], tmpdir)
                gpkg_path = os.path.join(tmpdir, gpkg_names[0])
            rows = extract_woz_from_gpkg(gpkg_path, year)
            all_rows.extend(rows)
            print(f"  {year}: {len(rows)} 条有效 WOZ 记录")

    all_rows.sort(key=lambda r: (r[0], r[1]))

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pc4", "year", "woz_waarde"])
        writer.writerows(all_rows)

    print(f"已写入: {out_path}（共 {len(all_rows)} 条，单位：千欧）")
    return 0


if __name__ == "__main__":
    exit(main())
