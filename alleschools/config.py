"""
配置加载与少量领域常量。

约定：
- 所有运行时可调的默认值一律写在 config.yaml 中，本模块不做兜底；
- 若 config.yaml 缺失或 PyYAML 不可用，则抛出异常；
- 若指定的 profile 在 profiles 中不存在，则抛出 KeyError。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore[import]
except ImportError:
    yaml = None  # type: ignore[assignment]


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 学年标签（领域常量，用于 WOZ 等）
SCHOOLJARS = [
    ("2019", "2020"),
    ("2020", "2021"),
    ("2021", "2022"),
    ("2022", "2023"),
    ("2023", "2024"),
    ("2024", "2025"),
]

WOZ_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
WEIGHTS = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]
MIN_PUPILS_TOTAL = 10


def _load_config_file(path: Path) -> Dict[str, Any]:
    """从 YAML 加载配置。文件不存在或 PyYAML 不可用时抛出异常。"""
    if not path.exists() or path.is_dir():
        raise FileNotFoundError(f"Config file required but not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config.yaml")
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a mapping at top-level.")
    return data


def _merge_dict_shallow(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """一层浅合并：override 覆盖 base，同为 dict 时做一层嵌套合并。"""
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            inner = dict(merged[k])
            inner.update(v)
            merged[k] = inner
        else:
            merged[k] = v
    return merged


def build_effective_config(
    profile: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    从 config.yaml 构造生效配置。

    合并顺序：
        1. config.yaml 的 defaults
        2. config.yaml 的 profiles.<profile>
        3. overrides（如 CLI 传入）

    不再使用任何 Python 内建默认值；config.yaml 缺失或 profile 不存在时会报错。
    """
    if config_path is None:
        config_path = Path(PROJECT_ROOT) / "config.yaml"

    file_cfg = _load_config_file(config_path)
    file_defaults = file_cfg.get("defaults")
    if file_defaults is None:
        raise ValueError(f"Config file {config_path} must contain a 'defaults' key.")
    if not isinstance(file_defaults, dict):
        raise ValueError(f"Config file {config_path} 'defaults' must be a mapping.")

    profiles = file_cfg.get("profiles") or {}
    profile_name = profile or file_cfg.get("profile") or "default"
    if profiles and profile_name not in profiles:
        raise KeyError(f"Profile '{profile_name}' not found in config file {config_path}")

    profile_cfg = profiles.get(profile_name) or {}
    merged: Dict[str, Any] = _merge_dict_shallow(dict(file_defaults), profile_cfg)

    if overrides:
        merged = _merge_dict_shallow(merged, overrides)

    merged["profile"] = profile_name
    merged["config_path"] = str(config_path)
    return merged


__all__ = [
    "BASE_DIR",
    "PROJECT_ROOT",
    "SCHOOLJARS",
    "WOZ_YEARS",
    "WEIGHTS",
    "MIN_PUPILS_TOTAL",
    "build_effective_config",
]
