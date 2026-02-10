from __future__ import annotations

import json
from pathlib import Path

import alleschools.config as cfg
from alleschools.exporters.points_exporter import export_po_points, export_vo_points
from alleschools.pipeline import run_po_pipeline, run_vo_pipeline


def test_export_po_points_structure(tmp_path: Path) -> None:
    """export_po_points 应按 schema 输出关键字段和 flags 结构。"""
    rows = [
        {
            "BRIN": "00AA",
            "vestigingsnaam": "Test PO",
            "gemeente": "G",
            "postcode": "1234AB",
            "type": "Bo",
            "X_linear": 1.0,
            "Y_linear": 2.0,
            "pupils_total": 50,
            "years_covered": "2019-2020,2020-2021",
            "has_full_woz": True,
        }
    ]
    out = tmp_path / "points_po.json"
    export_po_points(rows, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 1
    pt = data[0]
    assert pt["id"] == "00AA"
    assert pt["layer"] == "po"
    assert pt["brin"] == "00AA"
    assert pt["name"] == "Test PO"
    assert pt["municipality"] == "G"
    assert pt["postcode"] == "1234AB"
    assert pt["pc4"] == "1234"
    assert pt["school_type"] == "Bo"
    assert pt["x_linear"] == 1.0
    assert pt["y_linear"] == 2.0
    assert pt["size"] == 50
    assert "2019-2020" in pt["years_covered"]
    assert pt["flags"]["has_full_woz"] is True
    assert pt["flags"]["low_sample_excluded"] is False


def test_export_vo_points_structure(tmp_path: Path) -> None:
    """export_vo_points 应按 schema 输出关键字段并设置 layer=vo。"""
    rows = [
        {
            "BRIN": "00VO",
            "vestigingsnaam": "Test VO",
            "gemeente": "G",
            "postcode": "5678CD",
            "type": "HAVO/VWO",
            "X_linear": 10.0,
            "Y_linear": 20.0,
            "candidates_total": 100,
            "years_covered": "2019-2020",
        }
    ]
    out = tmp_path / "points_vo.json"
    export_vo_points(rows, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 1
    pt = data[0]
    assert pt["id"] == "00VO"
    assert pt["layer"] == "vo"
    assert pt["pc4"] == "5678"
    assert pt["size"] == 100
    assert "2019-2020" in pt["years_covered"]
    assert pt["flags"]["low_sample_excluded"] is False


def test_run_po_pipeline_writes_points_json(pipeline_data_root) -> None:
    """默认配置下 run_po_pipeline 应写出 points JSON 并在 stats 中返回路径。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    points_path_str = stats.get("points_path")
    assert points_path_str, "stats 中应包含 points_path"
    points_path = Path(points_path_str)
    assert points_path.exists()
    data = json.loads(points_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)


def test_run_vo_pipeline_writes_points_json_when_data_available(pipeline_data_root) -> None:
    """有 VO 数据时 run_vo_pipeline 也应写出 points JSON。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_vo_pipeline(effective)
    if stats.get("n_schools", 0) == 0:
        # 本地无 VO 输入文件时跳过
        return
    points_path_str = stats.get("points_path")
    assert points_path_str
    points_path = Path(points_path_str)
    assert points_path.exists()
    data = json.loads(points_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)

