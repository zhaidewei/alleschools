"""测试 PO 流水线中的日志与运行报告生成。"""

from pathlib import Path

import alleschools.config as cfg
from alleschools.pipeline import run_po_pipeline


def test_run_po_pipeline_creates_run_report(pipeline_data_root):
    """
    验证运行报告路径字段是否写出；使用临时 data_root 避免在项目根生成 generated/。
    """
    overrides = {"data_root": str(pipeline_data_root)}
    effective = cfg.build_effective_config(overrides=overrides)

    csv_path, stats = run_po_pipeline(effective)

    # 确认统计字段存在
    assert isinstance(stats["n_schools"], int)
    assert isinstance(stats["n_excluded"], int)
    # 确认报告路径字段存在
    report_path = Path(stats["run_report_path"])
    assert report_path.name == "run_report_po.json"

