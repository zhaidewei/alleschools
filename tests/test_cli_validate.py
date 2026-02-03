from __future__ import annotations

"""CLI validate 子命令测试。"""

import subprocess
from pathlib import Path

import alleschools.config as cfg


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cfg.PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_cli_validate_help_shows_options() -> None:
    """验证 validate 子命令出现在 --help 输出中。"""
    proc = _run(["python", "-m", "alleschools.cli", "--help"])
    assert proc.returncode == 0
    assert "validate" in proc.stdout


def test_cli_validate_po_after_pipeline(pipeline_data_root: Path) -> None:
    """先跑一次 PO 流水线（临时 data_root），再用 CLI validate 对其输出做 schema 校验。"""
    root = str(pipeline_data_root)
    proc_po = _run(["python", "-m", "alleschools.cli", "--data-root", root, "po"])
    assert proc_po.returncode == 0
    data_path = str(pipeline_data_root / "generated" / "schools_xy_coords_po.json")
    meta_path = str(pipeline_data_root / "generated" / "schools_xy_coords_po_meta.json")
    proc_val = _run(
        [
            "python", "-m", "alleschools.cli", "validate", "--layer", "po",
            "--data", data_path, "--meta", meta_path,
        ]
    )
    assert proc_val.returncode == 0
    assert "Schema validation OK for layer=po" in proc_val.stdout

