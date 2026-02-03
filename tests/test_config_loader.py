"""测试 alleschools.config 中的配置加载与合并逻辑。"""

from pathlib import Path

import pytest

import alleschools.config as cfg


def test_build_effective_config_missing_file_raises(tmp_path: Path) -> None:
    """config.yaml 不存在时应抛出 FileNotFoundError。"""
    fake_config_path = tmp_path / "config.yaml"
    assert not fake_config_path.exists()
    with pytest.raises(FileNotFoundError):
        cfg.build_effective_config(config_path=fake_config_path)


def test_build_effective_config_with_overrides(tmp_path: Path) -> None:
    """存在 config.yaml 时，overrides 应正确覆盖。"""
    repo_config = Path(cfg.PROJECT_ROOT) / "config.yaml"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(repo_config.read_text(encoding="utf-8"), encoding="utf-8")

    overrides = {
        "data_root": str(tmp_path),
        "po": {"output": {"csv": "custom_po.csv"}},
    }
    effective = cfg.build_effective_config(
        config_path=config_path,
        overrides=overrides,
    )

    assert effective["data_root"] == str(tmp_path)
    assert effective["po"]["output"]["csv"] == "custom_po.csv"


@pytest.mark.skipif(cfg.yaml is None, reason="PyYAML not installed")
def test_build_effective_config_with_minimal_yaml_defaults_and_profile(tmp_path: Path) -> None:
    """存在 config.yaml 时，应正确合并 defaults 和 profiles.default。"""
    import yaml

    repo_config = Path(cfg.PROJECT_ROOT) / "config.yaml"
    data = yaml.safe_load(repo_config.read_text(encoding="utf-8"))
    data["profiles"]["default"] = {"po": {"output": {"csv": "custom_po.csv"}}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    effective = cfg.build_effective_config(config_path=config_path)

    assert effective["data_root"] == "."
    assert effective["profile"] == "default"
    assert effective["po"]["output"]["csv"] == "custom_po.csv"


@pytest.mark.skipif(cfg.yaml is None, reason="PyYAML not installed")
def test_build_effective_config_missing_profile_raises(tmp_path: Path) -> None:
    """当 config 中 profile 指向不存在的 profile 时，应抛出 KeyError。"""
    import yaml

    repo_config = Path(cfg.PROJECT_ROOT) / "config.yaml"
    data = yaml.safe_load(repo_config.read_text(encoding="utf-8"))
    data["profile"] = "research"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    with pytest.raises(KeyError):
        cfg.build_effective_config(config_path=config_path)


@pytest.mark.skipif(cfg.yaml is None, reason="PyYAML not installed")
def test_build_effective_config_invalid_yaml_top_level_raises(tmp_path: Path) -> None:
    """当 config.yaml 顶层不是 mapping 时，应抛出 ValueError。"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("- 1\n- 2\n", encoding="utf-8")

    with pytest.raises(ValueError):
        cfg.build_effective_config(config_path=config_path)


def test_build_effective_config_vo_overrides(tmp_path: Path) -> None:
    """运行时 overrides 可覆盖 vo 子树。"""
    repo_config = Path(cfg.PROJECT_ROOT) / "config.yaml"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(repo_config.read_text(encoding="utf-8"), encoding="utf-8")

    overrides = {
        "vo": {
            "output": {"csv": "custom_vo.csv", "excluded_json": "custom_excluded_vo.json"},
        },
    }
    effective = cfg.build_effective_config(
        config_path=config_path,
        overrides=overrides,
    )
    assert effective["vo"]["output"]["csv"] == "custom_vo.csv"
    assert effective["vo"]["output"]["excluded_json"] == "custom_excluded_vo.json"
