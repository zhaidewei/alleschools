"""pytest 配置：保证从项目根可导入 calc_xy_coords / calc_xy_coords_po"""
import sys
import os

# 项目根目录加入 path，便于 pre-commit 或从 tests/ 运行时能 import 到模块
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
