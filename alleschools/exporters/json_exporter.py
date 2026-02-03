from __future__ import annotations

"""
JSON 导出工具。

当前仅用于写出被排除学校列表，后续可以扩展 meta 信息等。
"""

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def export_json(items: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # 与现有实现保持格式一致：ensure_ascii=False, indent=0
    with path.open("w", encoding="utf-8") as f:
        json.dump(list(items), f, ensure_ascii=False, indent=0)


def write_meta_json(meta: Mapping[str, Any], path: Path) -> None:
    """将单条 meta 信息写出为 JSON 文件（便于工具与文档消费）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(dict(meta), f, ensure_ascii=False, indent=2)


__all__ = ["export_json", "write_meta_json"]

