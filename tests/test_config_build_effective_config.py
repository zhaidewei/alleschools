from __future__ import annotations

from pathlib import Path

import pytest

import alleschools.config as cfg


def test_build_effective_config_loads_from_yaml() -> None:
    """从项目 config.yaml 加载时，应得到完整配置（data_root、po、vo 等）。"""
    config_path = Path(cfg.PROJECT_ROOT) / "config.yaml"
    effective = cfg.build_effective_config(config_path=config_path)

    assert effective["profile"] == "default"
    assert "data_root" in effective
    assert "po" in effective
    assert "vo" in effective
    assert effective["po"]["output"]["csv"] == "generated/schools_xy_coords_po.csv"
    assert effective["vo"]["output"]["csv"] == "generated/schools_xy_coords.csv"


@pytest.mark.skipif(cfg.yaml is None, reason="PyYAML not installed")
def test_build_effective_config_uses_defaults_and_profile(tmp_path: Path) -> None:
    """config.yaml 中的 defaults 与 profiles.<name> 正确合并。"""
    import yaml

    repo_config = Path(cfg.PROJECT_ROOT) / "config.yaml"
    content = repo_config.read_text(encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(content, encoding="utf-8")
    data = yaml.safe_load(content)
    data["profile"] = "dev"
    data.setdefault("profiles", {})["dev"] = {
        "data_root": "/data/dev",
        "po": {"thresholds": {"min_pupils_total": 42}},
    }
    config_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    effective = cfg.build_effective_config(config_path=config_path)
    assert effective["profile"] == "dev"
    assert effective["data_root"] == "/data/dev"
    assert "vo" in effective
    assert effective["po"]["thresholds"]["min_pupils_total"] == 42


def test_build_effective_config_overrides_has_highest_priority(tmp_path: Path) -> None:
    """overrides 应覆盖 defaults 与 profile。"""
    repo_config = Path(cfg.PROJECT_ROOT) / "config.yaml"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(repo_config.read_text(encoding="utf-8"), encoding="utf-8")

    overrides = {
        "data_root": "/data/override",
        "po": {"thresholds": {"min_pupils_total": 99}},
    }
    effective = cfg.build_effective_config(config_path=config_path, overrides=overrides)

    assert effective["data_root"] == "/data/override"
    assert effective["po"]["thresholds"]["min_pupils_total"] == 99
