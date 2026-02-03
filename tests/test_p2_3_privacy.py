from __future__ import annotations

"""P2-3：隐私与最小群体阈值（privacy.min_group_size）测试。"""

import json
from pathlib import Path

import pytest

import alleschools.config as cfg
from alleschools.pipeline import run_po_pipeline, run_vo_pipeline


def test_run_po_pipeline_records_privacy_info(pipeline_data_root) -> None:
    """设置较大的 privacy.min_group_size 时，run_report_po.json 中应记录隐私配置与统计。"""
    overrides = {
        "data_root": str(pipeline_data_root),
        "privacy": {"min_group_size": 1000000, "max_detail_level": "school"},
    }
    effective = cfg.build_effective_config(overrides=overrides)
    _, stats = run_po_pipeline(effective)
    report_path = Path(stats["run_report_path"])
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    run_report = reports[0]

    assert "privacy" in run_report
    privacy = run_report["privacy"]
    assert privacy["min_group_size"] == 1000000
    assert privacy["max_detail_level"] == "school"
    assert "n_suppressed" in privacy

    # 若有被隐私抑制的学校，应在 data_quality 中记录 privacy_suppressed 段
    dq = run_report.get("data_quality") or {}
    if privacy["n_suppressed"] > 0:
        assert "privacy_suppressed" in dq
        assert "count" in dq["privacy_suppressed"]
        assert "brins" in dq["privacy_suppressed"]


def test_run_vo_pipeline_records_privacy_info(pipeline_data_root) -> None:
    """有 VO 数据时，privacy.min_group_size 同样应反映在 run_report_vo.json 中。
    本测试设 min_group_size=1000000 会压制几乎所有学校，故 n_schools 可能为 0；
    仅当 pipeline 因缺少输入而报错（summary.status=error）时才 skip。"""
    overrides = {
        "data_root": str(pipeline_data_root),
        "privacy": {"min_group_size": 1000000, "max_detail_level": "school"},
    }
    effective = cfg.build_effective_config(overrides=overrides)
    _, stats = run_vo_pipeline(effective)
    report_path = Path(stats["run_report_path"])
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    run_report = reports[0]
    if run_report.get("summary", {}).get("status") == "error":
        pytest.skip("VO input files not present")

    assert "privacy" in run_report
    privacy = run_report["privacy"]
    assert privacy["min_group_size"] == 1000000
    assert privacy["max_detail_level"] == "school"
    assert "n_suppressed" in privacy

    dq = run_report.get("data_quality") or {}
    if privacy["n_suppressed"] > 0:
        assert "privacy_suppressed" in dq
        assert "count" in dq["privacy_suppressed"]
        assert "brins" in dq["privacy_suppressed"]

