"""P1-3：自动化数据质量检查 — 测试（PO + VO）。"""

import json
from pathlib import Path

import pytest

from alleschools.quality import run_po_quality, run_vo_quality
import alleschools.config as cfg
from alleschools.pipeline import run_po_pipeline, run_vo_pipeline


def test_run_po_quality_missing_postcode_and_excluded():
    """run_po_quality 能统计缺失邮编与 excluded 数量。"""
    rows_out = [
        {"BRIN": "00AA", "vestigingsnaam": "A", "postcode": "1234AB", "X_linear": 1.0},
        {"BRIN": "00BB", "vestigingsnaam": "B", "postcode": "", "X_linear": 2.0},
        {"BRIN": "00CC", "vestigingsnaam": "C", "postcode": "   ", "X_linear": 3.0},
    ]
    excluded = [{"BRIN": "00EX", "naam": "Ex", "gemeente": "G"}]
    data_root = Path(cfg.PROJECT_ROOT)
    input_cfg = {"duo_schooladviezen_pattern": "duo_schooladviezen_{start}_{end}.csv"}
    result = run_po_quality(rows_out, excluded, data_root, input_cfg, max_brins_in_report=50)
    assert "missing_postcode" in result
    assert result["missing_postcode"]["count"] == 2
    assert "00BB" in result["missing_postcode"]["brins"]
    assert "00CC" in result["missing_postcode"]["brins"]
    assert result["excluded_small_sample"]["count"] == 1
    assert "duplicate_brin_in_source" in result


def test_run_po_quality_caps_brins():
    """max_brins_in_report 限制 brins 列表长度。"""
    rows_out = [{"BRIN": f"0{i:02d}A", "postcode": ""} for i in range(10)]
    result = run_po_quality(rows_out, [], Path(cfg.PROJECT_ROOT), {}, max_brins_in_report=3)
    assert result["missing_postcode"]["count"] == 10
    assert len(result["missing_postcode"]["brins"]) == 3


def test_run_vo_quality_missing_postcode_and_excluded():
    """run_vo_quality 能统计缺失邮编与 excluded 数量。"""
    rows_out = [
        {"BRIN": "01VO", "vestigingsnaam": "V1", "postcode": "5678XY", "X_linear": 1.0},
        {"BRIN": "02VO", "vestigingsnaam": "V2", "postcode": "", "X_linear": 2.0},
    ]
    excluded = [{"BRIN": "03VO", "naam": "Ex", "gemeente": "G"}]
    data_root = Path(cfg.PROJECT_ROOT)
    input_cfg = {"exams_all_csv": "duo_examen_raw_all.csv", "exams_small_csv": "duo_examen_raw.csv"}
    result = run_vo_quality(rows_out, excluded, data_root, input_cfg, max_brins_in_report=50)
    assert result["missing_postcode"]["count"] == 1
    assert "02VO" in result["missing_postcode"]["brins"]
    assert result["excluded_small_sample"]["count"] == 1
    assert "duplicate_brin_in_source" in result


def test_run_po_pipeline_run_report_contains_data_quality(pipeline_data_root):
    """默认配置下 run_po_pipeline 的 run_report 包含 data_quality。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    report_path = Path(stats["run_report_path"])
    assert report_path.exists()
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(reports, list) and len(reports) == 1
    run_report = reports[0]
    assert "data_quality" in run_report
    dq = run_report["data_quality"]
    assert "duplicate_brin_in_source" in dq
    assert "missing_postcode" in dq
    assert "excluded_small_sample" in dq
    assert "count" in dq["excluded_small_sample"]


def test_run_po_pipeline_data_quality_disabled(pipeline_data_root):
    """data_quality.enabled: false 时 run_report 不包含 data_quality。"""
    overrides = {
        "data_root": str(pipeline_data_root),
        "po": {"data_quality": {"enabled": False}},
    }
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    report_path = Path(stats["run_report_path"])
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    run_report = reports[0]
    assert "data_quality" not in run_report or run_report.get("data_quality") is None


def test_run_po_pipeline_standalone_quality_report(pipeline_data_root):
    """write_standalone_report: true 时写出 data_quality_report_po.json（需有 PO 输入数据否则 pipeline 会提前返回）。"""
    overrides = {
        "data_root": str(pipeline_data_root),
        "po": {
            "data_quality": {"enabled": True, "write_standalone_report": True},
            "input": {
                "duo_schooladviezen_pattern": "duo_schooladviezen_{start}_{end}.csv",
                "cbs_woz_csv": "cbs_woz_per_postcode_year.csv",
            },
            "output": {"csv": "out_po.csv", "excluded_json": "excluded_po.json"},
        },
    }
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_po_pipeline(effective)
    if stats.get("n_schools", 0) == 0:
        pytest.skip("PO input files not present in pipeline_data_root")
    dq_path = pipeline_data_root / "data_quality_report_po.json"
    assert dq_path.exists(), "standalone data quality report should be written"
    data = json.loads(dq_path.read_text(encoding="utf-8"))
    assert data["pipeline_type"] == "po"
    assert "data_quality" in data
    assert "generated_at" in data
    # 新增：应记录当前 schema 版本，便于审计
    assert "schema_version" in data


def test_run_vo_pipeline_run_report_contains_data_quality(pipeline_data_root):
    """有 VO 数据时 run_vo_pipeline 的 run_report 包含 data_quality。"""
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)
    csv_path, stats = run_vo_pipeline(effective)
    if stats.get("n_schools", 0) == 0:
        pytest.skip("VO input files not present")
    report_path = Path(stats["run_report_path"])
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    run_report = reports[0]
    assert "data_quality" in run_report
    dq = run_report["data_quality"]
    assert "missing_postcode" in dq
    assert "excluded_small_sample" in dq
