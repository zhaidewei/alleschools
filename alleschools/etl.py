from __future__ import annotations

"""
统一 ETL 入口的高阶封装。

本模块提供三个核心能力，供 CLI 调用：

- fetch_*: 只负责下载 / 更新原始数据到 data_root;
- run_*_etl: 基于已有原始数据跑聚合流水线;
- run_full_*: 先 fetch 再 etl（并复用 pipeline 中已有的 schema 校验逻辑）。

注意：
- URL、字段解析等“业务逻辑”仍然保留在原脚本/模块中，本模块只聚合 IO 路径和步骤顺序；
- data_root 由 alleschools.config.build_effective_config 统一提供。
"""

import csv
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import urllib.request

from alleschools import config as config_mod
from alleschools import fetch_cbs_woz as cbs_woz
from alleschools import pipeline


def _get_data_root(cfg: Dict[str, Any]) -> Path:
    """根据配置获取 data_root（回退到 PROJECT_ROOT）。"""
    return Path(cfg.get("data_root") or config_mod.PROJECT_ROOT)


def _get_raw_root(cfg: Dict[str, Any]) -> Path:
    """
    根据配置获取原始数据目录。

    规则：
    - 若配置中存在 raw_subdir，则视为相对于 data_root 的子目录；
      若 raw_subdir 为绝对路径，则直接使用；
    - 否则退回到 data_root 本身（保持向后兼容）。
    """
    data_root = _get_data_root(cfg)
    raw_sub = str(cfg.get("raw_subdir") or "").strip()
    if not raw_sub:
        return data_root
    raw_path = Path(raw_sub)
    if not raw_path.is_absolute():
        raw_path = data_root / raw_path
    return raw_path


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_vo_exams(data_root: Path) -> Path:
    """
    下载 VO 考试全量 CSV 到 data_root。

    返回实际写入的文件路径。
    """
    url = "https://duo.nl/open_onderwijsdata/images/examenkandidaten-en-geslaagden-2019-2024.csv"
    data_root.mkdir(parents=True, exist_ok=True)
    out_path = data_root / "duo_examen_raw_all.csv"
    print(f"[fetch] VO exams: {url} -> {out_path}")
    urllib.request.urlretrieve(url, out_path)
    return out_path


def fetch_vo_vestigingen(data_root: Path) -> Path:
    """
    下载 VO vestigingen（含 postcode）CSV 到 data_root。

    返回实际写入的文件路径。
    """
    url = "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv"
    data_root.mkdir(parents=True, exist_ok=True)
    out_path = data_root / "duo_vestigingen_vo.csv"
    print(f"[fetch] VO vestigingen: {url} -> {out_path}")
    urllib.request.urlretrieve(url, out_path)
    return out_path


def _schooladviezen_duo_filename(start: str, end: str) -> str:
    """复制 fetch_duo_schooladviezen 中对 DUO 文件名的约定。"""
    if start in {"2019", "2020"}:
        return f"04.-leerlingen-bo-sbo-schooladviezen-{start}-{end}.csv"
    return f"04-leerlingen-bo-sbo-schooladviezen-{start}-{end}.csv"


def fetch_po_schooladviezen(
    data_root: Path,
    schoolyears: Iterable[Tuple[str, str]] | None = None,
) -> None:
    """
    下载 PO schooladviezen CSV 到 data_root。

    行为等价于顶层脚本 fetch_duo_schooladviezen.py，只是输出目录改为 data_root。
    """
    base_url = "https://duo.nl/open_onderwijsdata/images"
    if schoolyears is None:
        schoolyears = [
            ("2024", "2025"),
            ("2023", "2024"),
            ("2022", "2023"),
            ("2021", "2022"),
            ("2020", "2021"),
            ("2019", "2020"),
        ]

    data_root.mkdir(parents=True, exist_ok=True)
    ok = 0
    schoolyears = list(schoolyears)
    for start, end in schoolyears:
        duo_name = _schooladviezen_duo_filename(start, end)
        url = f"{base_url}/{duo_name}"
        out_name = f"duo_schooladviezen_{start}_{end}.csv"
        out_path = data_root / out_name
        try:
            print(f"[fetch] PO schooladviezen: {url} -> {out_path}")
            urllib.request.urlretrieve(url, out_path)
            ok += 1
        except Exception as exc:  # pragma: no cover - 网络异常
            print(f"[fetch]   failed for {out_name}: {exc}")
    print(f"[fetch] PO schooladviezen done: {ok}/{len(schoolyears)} files")


def fetch_cbs_woz(data_root: Path) -> Path:
    """
    从 CBS 下载 WOZ 数据并写入 data_root/cbs_woz_per_postcode_year.csv。
    """
    data_root.mkdir(parents=True, exist_ok=True)
    out_path = data_root / "cbs_woz_per_postcode_year.csv"
    all_rows = []  # (pc4, year, woz_waarde)

    with tempfile.TemporaryDirectory() as tmpdir:
        for year, zip_name in sorted(cbs_woz.YEARS_ZIP.items()):
            url = f"{cbs_woz.BASE_URL}/{zip_name}"
            zip_path = os.path.join(tmpdir, zip_name)
            try:
                print(f"[fetch] CBS WOZ: downloading {url}")
                urllib.request.urlretrieve(url, zip_path)
            except Exception as exc:  # pragma: no cover - 网络异常
                print(f"[fetch]   download failed for {zip_name}: {exc}")
                continue
            if not zipfile.is_zipfile(zip_path):
                print(f"[fetch]   invalid zip: {zip_path}")
                continue
            with zipfile.ZipFile(zip_path, "r") as zf:
                gpkg_names = [n for n in zf.namelist() if n.endswith(".gpkg")]
                if not gpkg_names:
                    print(f"[fetch]   no .gpkg found in {zip_name}")
                    continue
                zf.extract(gpkg_names[0], tmpdir)
                gpkg_path = os.path.join(tmpdir, gpkg_names[0])
            rows = cbs_woz.extract_woz_from_gpkg(gpkg_path, year)
            all_rows.extend(rows)
            print(f"[fetch]   {year}: {len(rows)} valid WOZ rows")

    all_rows.sort(key=lambda r: (r[0], r[1]))
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pc4", "year", "woz_waarde"])
        writer.writerows(all_rows)

    print(f"[fetch] CBS WOZ written: {out_path} ({len(all_rows)} rows)")
    return out_path


def run_etl_vo(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """基于当前配置跑 VO 聚合流水线。返回 pipeline 的 stats（含 summary_status）。"""
    csv_path, stats = pipeline.run_vo_pipeline(cfg)
    n = int(stats.get("n_schools", 0))
    n_excluded = int(stats.get("n_excluded", 0))
    print(f"VO: 已写入 {csv_path}（共 {n} 所中学，排除 {n_excluded} 所）")
    if stats.get("run_report_path"):
        print(f"VO 运行报告: {stats['run_report_path']}")
    return stats


def run_etl_po(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """基于当前配置跑 PO 聚合流水线。返回 pipeline 的 stats（含 summary_status）。"""
    csv_path, stats = pipeline.run_po_pipeline(cfg)
    n = int(stats.get("n_schools", 0))
    n_excluded = int(stats.get("n_excluded", 0))
    print(f"PO: 已写入 {csv_path}（共 {n} 所小学，排除 {n_excluded} 所）")
    if stats.get("run_report_path"):
        print(f"PO 运行报告: {stats['run_report_path']}")
    return stats


def run_fetch_from_cli_args(cfg: Dict[str, Any], *, vo: bool, po: bool, cbs_woz: bool) -> None:
    """根据 CLI 解析结果执行 fetch 步骤。"""
    raw_root = _get_raw_root(cfg)
    if vo:
        # VO fetch 同时需要考试数据和 vestigingen 映射
        fetch_vo_exams(raw_root)
        fetch_vo_vestigingen(raw_root)
    if po:
        fetch_po_schooladviezen(raw_root)
    if cbs_woz:
        fetch_cbs_woz(raw_root)


def run_etl_from_cli_args(cfg: Dict[str, Any], *, vo: bool, po: bool) -> bool:
    """
    根据 CLI 解析结果执行 ETL 步骤。
    返回 True 表示至少有一个 layer 的 run_report.summary.status 为 "error"（便于 CLI 设置退出码）。
    """
    had_error = False
    if vo:
        stats = run_etl_vo(cfg)
        if stats.get("summary_status") == "error":
            had_error = True
    if po:
        stats = run_etl_po(cfg)
        if stats.get("summary_status") == "error":
            had_error = True
    return had_error


__all__ = [
    "fetch_vo_exams",
    "fetch_vo_vestigingen",
    "fetch_po_schooladviezen",
    "fetch_cbs_woz",
    "_get_data_root",
    "_get_raw_root",
    "run_etl_vo",
    "run_etl_po",
    "run_fetch_from_cli_args",
    "run_etl_from_cli_args",
]

