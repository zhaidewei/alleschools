"""pytest 配置：保证从项目根可导入，并提供 pipeline 测试用临时 data_root 避免污染项目根。"""
import os
import shutil
import sys
from pathlib import Path

import pytest

# 项目根目录加入 path，便于 pre-commit 或从 tests/ 运行时能 import 到模块
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)


def _project_root() -> Path:
    return Path(_root)


@pytest.fixture
def pipeline_data_root(tmp_path):
    """
    供 pipeline 测试使用的临时 data_root，避免在项目根下生成 generated/ 与 run_report_*.json。
    若项目根存在 raw_data/，会复制到临时目录，以便需要真实输入的测试能跑通。
    """
    raw_src = _project_root() / "raw_data"
    if raw_src.is_dir():
        shutil.copytree(raw_src, tmp_path / "raw_data", dirs_exist_ok=True)
    return tmp_path
