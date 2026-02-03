"""
从 CBS 下载邮编级「Gemiddelde WOZ-waarde woning」数据，按 PC4 和年份提取。

数据源: https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/gegevens-per-postcode
Zip 内为 Geopackage，用 sqlite3 读取表 postcode + gemiddelde_woz_waarde_woning。

年份说明（维护时参考）：
- 2024：当前 v1 中 WOZ 为 CBS 待发布编码(-99995)，脚本会下载但有效条数为 0；
  等 CBS 发布 2024 的 v2（或更新 zip）且含 WOZ 后，再跑脚本即可；若 zip 名变更需改 YEARS_ZIP。
- 2025：peildatum 1 januari 2025 的邮编数据尚未发布，通常会在 2026 年放出，
  届时可将 2025 加入 YEARS_ZIP。
- 查最新发布与 zip 名：https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/gegevens-per-postcode
"""

from __future__ import annotations

import sqlite3
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


def _find_data_table(conn: sqlite3.Connection) -> str | None:
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
    table = _find_data_table(conn)
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


__all__ = ["BASE_URL", "YEARS_ZIP", "extract_woz_from_gpkg"]
