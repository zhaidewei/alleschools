#!/usr/bin/env python3
"""
从 DUO Open Onderwijsdata 下载全部中学的「Examenkandidaten en geslaagden」CSV，
保存为 duo_examen_raw_all.csv，供 calc_xy_coords.py 使用。
"""
import os
import urllib.request

DUO_URL = "https://duo.nl/open_onderwijsdata/images/examenkandidaten-en-geslaagden-2019-2024.csv"
OUT_FILENAME = "duo_examen_raw_all.csv"


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base, OUT_FILENAME)
    print(f"正在下载: {DUO_URL}")
    urllib.request.urlretrieve(DUO_URL, out_path)
    size = os.path.getsize(out_path)
    print(f"已保存: {out_path} ({size:,} 字节)")
    return 0


if __name__ == "__main__":
    exit(main())
