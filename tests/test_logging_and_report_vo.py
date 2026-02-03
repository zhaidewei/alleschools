"""测试 VO 流水线中的日志与运行报告生成。"""

import json
from pathlib import Path

import alleschools.config as cfg
from alleschools.pipeline import run_vo_pipeline


def test_run_vo_pipeline_creates_run_report(pipeline_data_root):
    """
    验证 stats 含 run_report_path，且报告文件存在且 pipeline_type 为 vo；
    使用临时 data_root 避免在项目根生成 generated/。
    """
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)

    csv_path, stats = run_vo_pipeline(effective)

    assert "run_report_path" in stats
    report_path = Path(stats["run_report_path"])
    assert report_path.name == "run_report_vo.json"
    assert report_path.is_absolute() and report_path.exists()

    raw = json.loads(report_path.read_text(encoding="utf-8"))
    # export_json 写入的是 [run_report]，所以是列表
    report = raw[0] if isinstance(raw, list) else raw
    assert report["pipeline_type"] == "vo"
    assert report.get("profile") is not None
    assert "summary" in report
    assert "status" in report["summary"]
    if report["summary"]["status"] == "success":
        assert isinstance(stats["n_schools"], int)
        assert isinstance(stats["n_excluded"], int)
