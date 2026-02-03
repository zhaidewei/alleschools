"""P1-1：更丰富的 CSV/JSON 输出 — meta 列与 meta JSON 测试。"""

import json
from pathlib import Path

import pytest

from alleschools.compute.indicators import compute_po_xy, compute_vo_xy
from alleschools.exporters import csv_exporter
from alleschools.exporters.meta_builder import build_po_meta, build_vo_meta, SCHEMA_VERSION
import alleschools.config as cfg
from alleschools.pipeline import run_po_pipeline, run_vo_pipeline


def test_compute_po_xy_includes_meta_columns():
    """compute_po_xy 返回的每行包含 years_covered、has_full_woz、data_quality_flags。"""
    schools = {
        "00AA": {
            "naam": "Test",
            "gemeente": "G",
            "postcode": "1234AB",
            "pc4": "1234",
            "soort_po": "Bo",
            "years": {("2019", "2020"): {"total": 50, "vwo_equiv": 10}},
        },
    }
    woz = {("1234", 2019): 200.0}
    woz_years = [2019]
    rows, _ = compute_po_xy(schools, woz, woz_years)
    assert len(rows) == 1
    r = rows[0]
    assert "years_covered" in r
    assert "has_full_woz" in r
    assert "data_quality_flags" in r
    assert r["years_covered"] == "2019-2020"
    assert r["has_full_woz"] is True


def test_export_po_csv_respects_include_meta_columns(tmp_path: Path):
    """export_po_csv(include_meta_columns=False) 只写基础列；True 时写基础+meta 列。"""
    row = {
        "BRIN": "00AA",
        "vestigingsnaam": "A",
        "gemeente": "G",
        "postcode": "1234",
        "type": "Bo",
        "X_linear": 1.0,
        "Y_linear": 2.0,
        "X_log": 0.01,
        "Y_log": 0.02,
        "pupils_total": 50,
        "years_covered": "2019-2020",
        "has_full_woz": True,
        "data_quality_flags": "",
    }
    path_no_meta = tmp_path / "no_meta.csv"
    path_with_meta = tmp_path / "with_meta.csv"
    csv_exporter.export_po_csv([row], path_no_meta, include_meta_columns=False)
    csv_exporter.export_po_csv([row], path_with_meta, include_meta_columns=True)
    header_no = path_no_meta.read_text(encoding="utf-8").splitlines()[0]
    header_with = path_with_meta.read_text(encoding="utf-8").splitlines()[0]
    assert "years_covered" not in header_no
    assert "years_covered" in header_with
    assert "has_full_woz" in header_with


def test_build_po_meta_structure_matches_schema():
    """build_po_meta 返回的结构应包含 version/layer/axes/fields/i18n 等关键字段。"""
    data_file = Path("schools_xy_coords_po.json")
    columns = ["id", "x_linear", "y_linear", "size"]
    meta = build_po_meta(data_file, row_count=10, columns=columns)
    assert meta["version"] == SCHEMA_VERSION
    assert meta["layer"] == "po"
    assert "axes" in meta and "fields" in meta and "i18n" in meta
    assert meta["axes"]["x"]["field"] == "x_linear"
    assert meta["axes"]["size"]["field"] == "size"
    assert "nl" in meta["i18n"]
    assert "po_vwo_advice_share" in meta["i18n"]["nl"]["metrics"]


def test_run_po_pipeline_writes_meta_json_and_stats(pipeline_data_root):
    """默认配置下 run_po_pipeline 写出 schema meta JSON 且 stats 含 meta_path。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    assert "meta_path" in stats
    meta_path = Path(stats["meta_path"])
    assert meta_path.name == "schools_xy_coords_po_meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["version"] == SCHEMA_VERSION
    assert meta["layer"] == "po"
    assert meta["summary"]["data_file"] == csv_path.name
    assert "axes" in meta and "fields" in meta and "i18n" in meta


def test_compute_vo_xy_includes_meta_columns():
    """compute_vo_xy 返回的每行包含 years_covered、data_quality_flags。"""
    year_cols = [[13, 14, "2019-2020", 0.2], [22, 23, "2020-2021", 0.4]]
    year_labels = [y[2] for y in year_cols]
    schools = {
        "00VO": {
            "naam": "VO Test",
            "gemeente": "G",
            "havo_vwo": {
                y: {"vwo": 10, "havo": 0, "science": 5, "total": 20} for y in year_labels
            },
            "vmbo": {y: {"techniek": 0, "total": 0} for y in year_labels},
            "all_kand": {y: 25 for y in year_labels},
        },
    }
    brin_to_postcode = {}
    rows, _ = compute_vo_xy(schools, brin_to_postcode, year_cols, min_havo_vwo_total=20)
    assert len(rows) == 1
    r = rows[0]
    assert "years_covered" in r
    assert "data_quality_flags" in r
    assert "2019-2020" in r["years_covered"]
    assert "2020-2021" in r["years_covered"]


def test_export_vo_csv_respects_include_meta_columns(tmp_path: Path):
    """export_vo_csv(include_meta_columns=False) 只写基础列；True 时写基础+meta 列。"""
    row = {
        "BRIN": "00VO",
        "vestigingsnaam": "A",
        "gemeente": "G",
        "postcode": "1234",
        "type": "HAVO/VWO",
        "X_linear": 1.0,
        "Y_linear": 2.0,
        "X_log": 0.01,
        "Y_log": 0.02,
        "candidates_total": 100,
        "years_covered": "2019-2020,2020-2021",
        "data_quality_flags": "",
    }
    path_no_meta = tmp_path / "vo_no_meta.csv"
    path_with_meta = tmp_path / "vo_with_meta.csv"
    csv_exporter.export_vo_csv([row], path_no_meta, include_meta_columns=False)
    csv_exporter.export_vo_csv([row], path_with_meta, include_meta_columns=True)
    header_no = path_no_meta.read_text(encoding="utf-8").splitlines()[0]
    header_with = path_with_meta.read_text(encoding="utf-8").splitlines()[0]
    assert "years_covered" not in header_no
    assert "years_covered" in header_with
    assert "data_quality_flags" in header_with


def test_run_vo_pipeline_writes_meta_json_and_stats(pipeline_data_root):
    """默认配置下 run_vo_pipeline 写出 schema meta JSON 且 stats 含 meta_path（有 VO 数据时）。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_vo_pipeline(effective)
    if stats.get("n_schools", 0) == 0:
        pytest.skip("VO input files not present; meta not written")
    assert "meta_path" in stats
    meta_path = Path(stats["meta_path"])
    assert meta_path.suffix == ".json" and "_meta" in meta_path.stem
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["version"] == SCHEMA_VERSION
    assert meta["layer"] == "vo"
    assert meta["summary"]["data_file"] == csv_path.name
    assert "axes" in meta and "fields" in meta
