"""P1-2：地图与 BI 格式 — GeoJSON 与长表导出测试（PO + VO）。"""

import csv
import json
from pathlib import Path

import pytest

from alleschools.exporters import geojson_exporter, long_table_exporter
import alleschools.config as cfg
from alleschools.pipeline import run_po_pipeline, run_vo_pipeline


def test_export_geojson_no_lookup(tmp_path: Path):
    """无 lookup 时 export_geojson 写出 FeatureCollection，每个 Feature 的 geometry 为 null。"""
    rows = [
        {
            "BRIN": "00AA",
            "vestigingsnaam": "Test",
            "gemeente": "G",
            "postcode": "1234AB",
            "type": "Bo",
            "X_linear": 1.0,
            "Y_linear": 2.0,
            "pupils_total": 50,
            "years_covered": "2019-2020",
            "has_full_woz": True,
            "data_quality_flags": "",
        },
    ]
    out = tmp_path / "out_geo.json"
    geojson_exporter.export_geojson(rows, out, lookup_path=None)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"] is None
    assert feat["properties"]["BRIN"] == "00AA"
    assert feat["properties"]["vestigingsnaam"] == "Test"
    assert feat["properties"]["X_linear"] == 1.0


def test_export_geojson_with_lookup(tmp_path: Path):
    """有 pc4 lookup CSV 时，能查到的 PC4 对应 Feature 的 geometry 为 Point。"""
    lookup = tmp_path / "pc4.csv"
    with lookup.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pc4", "lat", "lon"])
        w.writeheader()
        w.writerow({"pc4": "1234", "lat": "52.1", "lon": "5.2"})
    rows = [
        {
            "BRIN": "00AA",
            "vestigingsnaam": "Test",
            "postcode": "1234AB",
            "X_linear": 1.0,
            "Y_linear": 2.0,
        },
    ]
    out = tmp_path / "out_geo.json"
    geojson_exporter.export_geojson(rows, out, lookup_path=str(lookup))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["features"][0]["geometry"] is not None
    assert data["features"][0]["geometry"]["type"] == "Point"
    assert data["features"][0]["geometry"]["coordinates"] == [5.2, 52.1]


def test_export_po_long_table_expands_years(tmp_path: Path):
    """export_po_long_table 按 years_covered 拆成多行，每行有 year 列。"""
    rows = [
        {
            "BRIN": "00AA",
            "vestigingsnaam": "A",
            "gemeente": "G",
            "postcode": "1234",
            "type": "Bo",
            "X_linear": 1.0,
            "Y_linear": 2.0,
            "pupils_total": 50,
            "years_covered": "2019-2020,2020-2021",
            "has_full_woz": True,
            "data_quality_flags": "",
        },
    ]
    out = tmp_path / "po_long.csv"
    long_table_exporter.export_po_long_table(rows, out, include_meta_columns=True)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3  # header + 2 data rows
    header = lines[0]
    assert "year" in header
    assert "BRIN" in header
    assert lines[1].startswith("00AA,") or "2019-2020" in lines[1]
    assert "2020-2021" in lines[2] or "2020-2021" in lines[1]


def test_export_vo_long_table_expands_years(tmp_path: Path):
    """export_vo_long_table 按 years_covered 拆成多行。"""
    rows = [
        {
            "BRIN": "00VO",
            "vestigingsnaam": "VO A",
            "gemeente": "G",
            "postcode": "5678",
            "type": "HAVO/VWO",
            "X_linear": 10.0,
            "Y_linear": 20.0,
            "candidates_total": 100,
            "years_covered": "2019-2020,2020-2021,2021-2022",
            "data_quality_flags": "",
        },
    ]
    out = tmp_path / "vo_long.csv"
    long_table_exporter.export_vo_long_table(rows, out, include_meta_columns=True)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4  # header + 3 data rows
    assert "year" in lines[0]


def test_run_po_pipeline_writes_geojson_and_long_table(pipeline_data_root):
    """默认配置下 run_po_pipeline 写出 _geo.json 与 _long.csv，且 stats 含路径。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    assert "geojson_path" in stats
    assert "long_table_path" in stats
    geo_path = Path(stats["geojson_path"])
    long_path = Path(stats["long_table_path"])
    assert geo_path.name == "schools_xy_coords_po_geo.json"
    assert long_path.name == "schools_xy_coords_po_long.csv"
    assert geo_path.exists()
    assert long_path.exists()
    geo = json.loads(geo_path.read_text(encoding="utf-8"))
    assert geo["type"] == "FeatureCollection"
    assert "features" in geo
    long_lines = long_path.read_text(encoding="utf-8").strip().splitlines()
    assert "year" in long_lines[0]


def test_run_vo_pipeline_writes_geojson_and_long_table(pipeline_data_root):
    """默认配置下 run_vo_pipeline 写出 _geo.json 与 _long.csv（有 VO 数据时）。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_vo_pipeline(effective)
    if stats.get("n_schools", 0) == 0:
        pytest.skip("VO input files not present")
    assert "geojson_path" in stats
    assert "long_table_path" in stats
    geo_path = Path(stats["geojson_path"])
    long_path = Path(stats["long_table_path"])
    assert geo_path.exists()
    assert long_path.exists()
    geo = json.loads(geo_path.read_text(encoding="utf-8"))
    assert geo["type"] == "FeatureCollection"
    assert "year" in long_path.read_text(encoding="utf-8").splitlines()[0]


def test_run_po_pipeline_respects_export_geojson_false(pipeline_data_root):
    """export_geojson: false 时不写 GeoJSON，stats 无 geojson_path。"""
    overrides = {
        "data_root": str(pipeline_data_root),
        "po": {"output": {"export_geojson": False, "export_long_table": True}},
    }
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    assert "geojson_path" not in stats
    assert "long_table_path" in stats


def test_run_po_pipeline_respects_export_long_table_false(pipeline_data_root):
    """export_long_table: false 时不写长表，stats 无 long_table_path。"""
    overrides = {
        "data_root": str(pipeline_data_root),
        "po": {"output": {"export_geojson": True, "export_long_table": False}},
    }
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    assert "geojson_path" in stats
    assert "long_table_path" not in stats
