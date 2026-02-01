#!/usr/bin/env python3
"""
从 DUO Open Onderwijsdata 下载小学「Schooladviezen」（毕业建议）CSV，
按学年保存为 duo_schooladviezen_YYYY_YYYY.csv。
数据源: https://duo.nl/open_onderwijsdata/primair-onderwijs/aantal-leerlingen/schooladviezen.jsp
"""
import os
import urllib.request

BASE_URL = "https://duo.nl/open_onderwijsdata/images"

# 学年 (start, end)，对应 DUO 页面上的文件名（部分年份文件名中 04 后多一个点）
SCHOOLJARS = [
    ("2024", "2025"),  # 04-leerlingen-bo-sbo-schooladviezen-2024-2025.csv
    ("2023", "2024"),
    ("2022", "2023"),
    ("2021", "2022"),
    ("2020", "2021"),  # 04.-leerlingen-bo-sbo-schooladviezen-2020-2021.csv
    ("2019", "2020"),
]


def filename_on_duo(start: str, end: str) -> str:
    """DUO 文件名：2019/2020 用 04. 前缀，其余用 04 前缀。"""
    if start == "2019" or start == "2020":
        return f"04.-leerlingen-bo-sbo-schooladviezen-{start}-{end}.csv"
    return f"04-leerlingen-bo-sbo-schooladviezen-{start}-{end}.csv"


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    ok = 0
    for start, end in SCHOOLJARS:
        duo_name = filename_on_duo(start, end)
        url = f"{BASE_URL}/{duo_name}"
        out_name = f"duo_schooladviezen_{start}_{end}.csv"
        out_path = os.path.join(base, out_name)
        try:
            print(f"正在下载: {out_name}")
            urllib.request.urlretrieve(url, out_path)
            size = os.path.getsize(out_path)
            print(f"  已保存: {out_path} ({size:,} 字节)")
            ok += 1
        except Exception as e:
            print(f"  失败: {e}")
    print(f"完成: 成功 {ok}/{len(SCHOOLJARS)} 个文件")
    return 0 if ok == len(SCHOOLJARS) else 1


if __name__ == "__main__":
    exit(main())
