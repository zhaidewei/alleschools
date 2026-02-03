from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import alleschools.config as cfg
from alleschools import schema_validator as sv


def test_validate_points_schema_happy_path() -> None:
    """简单的合法 points 对象应通过 validate_points_schema。"""
    points = [
        {
            "id": "00AA",
            "layer": "po",
            "brin": "00AA",
            "name": "Test",
            "municipality": "G",
            "postcode": "1234AB",
            "pc4": "1234",
            "school_type": "Bo",
            "x_linear": 1.0,
            "y_linear": 2.0,
            "x_log": 0.01,
            "y_log": 0.02,
            "size": 50,
            "years_covered": ["2019-2020"],
            "flags": {"has_full_woz": True, "low_sample_excluded": False},
        }
    ]
    errors = sv.validate_points_schema(points, layer="po")
    assert errors == []


def test_validate_points_schema_reports_missing_and_type_errors() -> None:
    """缺字段或类型不符时，validate_points_schema 应返回对应错误。"""
    points = [
        {
            # 缺少 id
            "layer": "po",
            "brin": "00AA",
            "name": "Test",
            "municipality": "G",
            "postcode": "1234AB",
            "pc4": "1234",
            "school_type": "Bo",
            "x_linear": "not-a-number",
            "y_linear": 2.0,
            "x_log": 0.01,
            "y_log": 0.02,
            "size": 50,
            "years_covered": "2019-2020",  # 应为 list
            "flags": [],
        }
    ]
    errors = sv.validate_points_schema(points, layer="po")
    kinds = {e.kind for e in errors}
    paths = {e.path for e in errors}
    assert "missing_field" in kinds
    assert "$[0].id" in paths
    assert "type_error" in kinds
    # 至少要有针对 x_linear / years_covered / flags 的类型错误
    assert any("x_linear" in e.path for e in errors)
    assert any("years_covered" in e.path for e in errors)
    assert any("flags" in e.path for e in errors)


def test_validate_meta_schema_and_points_against_meta_with_real_files() -> None:
    """使用当前导出的 PO points + meta 进行整体校验应无错误。"""
    root = Path(cfg.PROJECT_ROOT)
    data_path = root / "generated" / "schools_xy_coords_po.json"
    meta_path = root / "generated" / "schools_xy_coords_po_meta.json"
    assert data_path.exists(), "PO points JSON should exist for schema validation test"
    assert meta_path.exists(), "PO meta JSON should exist for schema validation test"

    points = json.loads(data_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    errors = sv.validate_points_against_meta(points, meta, layer="po")
    # 若此处失败，说明当前导出的 data/meta 与 validator 或 SCHEMA 不一致，需要优先修复
    assert errors == []


def test_validate_meta_schema_detects_version_and_axes_errors() -> None:
    """构造一个有明显问题的 meta，验证 validator 能识别。"""
    bad_meta = {
        "version": "0.9.0",
        "layer": "po",
        "axes": {
            # 故意缺少 y/size
            "x": {"field": "x_linear", "scale": "linear", "metric_id": "po_vwo_advice_share"},
        },
        "fields": {},
        "i18n": {},
    }
    errors = sv.validate_meta_schema(bad_meta, expected_layer="po")
    kinds = {e.kind for e in errors}
    paths = {e.path for e in errors}
    assert "version_mismatch" in kinds
    # axes.y 与 axes.size 缺失
    assert "$.axes.y" in paths
    assert "$.axes.size" in paths


def test_validate_geojson_schema_happy_path() -> None:
    """简单合法的 FeatureCollection 应通过 validate_geojson_schema。"""
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "BRIN": "00AA",
                    "X_linear": 1.0,
                    "Y_linear": 2.0,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [5.2, 52.1],
                },
            }
        ],
    }
    errors = sv.validate_geojson_schema(geo, layer="po")
    assert errors == []


def test_validate_long_table_schema_happy_path_po_and_vo() -> None:
    """构造最小长表行，验证 PO/VO 层的基本结构通过校验。"""
    po_rows = [
        {
            "BRIN": "00AA",
            "year": "2019-2020",
            "X_linear": "1.0",
            "Y_linear": "2.0",
            "pupils_total": "50",
        }
    ]
    vo_rows = [
        {
            "BRIN": "00VO",
            "year": "2019-2020",
            "X_linear": "10.0",
            "Y_linear": "20.0",
            "candidates_total": "100",
        }
    ]
    assert sv.validate_long_table_schema(po_rows, layer="po") == []
    assert sv.validate_long_table_schema(vo_rows, layer="vo") == []


def test_validate_geojson_and_long_table_with_real_po_files_if_present() -> None:
    """
    若 generated 下存在 PO 的 GeoJSON 与长表 CSV，则对其运行 schema 校验应无错误。
    方便在本地/CI 上对实际导出结果做端到端验证。
    """
    root = Path(cfg.PROJECT_ROOT)
    geo_path = root / "generated" / "schools_xy_coords_po_geo.json"
    long_path = root / "generated" / "schools_xy_coords_po_long.csv"

    if not geo_path.exists() or not long_path.exists():
        pytest.skip("generated PO geojson/long-table files not present")

    geo = json.loads(geo_path.read_text(encoding="utf-8"))
    errors_geo = sv.validate_geojson_schema(geo, layer="po")
    assert errors_geo == []

    with long_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    errors_long = sv.validate_long_table_schema(rows, layer="po")
    assert errors_long == []

