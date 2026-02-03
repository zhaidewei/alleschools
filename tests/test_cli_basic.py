from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import alleschools.config as cfg


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alleschools.cli", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_cli_help_shows_subcommands(tmp_path: Path) -> None:
    """python -m alleschools.cli --help 应该展示 po/vo 子命令。"""
    # 在项目根目录下运行，确保 alleschools 包可被找到
    from alleschools import config as cfg_mod

    project_root = Path(cfg_mod.PROJECT_ROOT)
    proc = _run_cli(["--help"], cwd=project_root)
    assert proc.returncode == 0
    out = proc.stdout
    assert "po" in out
    assert "vo" in out


def test_cli_po_runs_pipeline_with_default_config(pipeline_data_root: Path) -> None:
    """po 子命令应成功返回；使用 --data-root 指向临时目录，避免在项目根生成 generated/。"""
    project_root = Path(cfg.PROJECT_ROOT)
    proc = _run_cli(["--data-root", str(pipeline_data_root), "po"], cwd=project_root)
    assert proc.returncode == 0
    assert "PO:" in proc.stdout


def test_cli_vo_runs_pipeline_with_default_config(pipeline_data_root: Path) -> None:
    """vo 子命令应成功返回；使用 --data-root 指向临时目录，避免在项目根生成 generated/。"""
    project_root = Path(cfg.PROJECT_ROOT)
    proc = _run_cli(["--data-root", str(pipeline_data_root), "vo"], cwd=project_root)
    assert proc.returncode == 0
    assert "VO:" in proc.stdout

