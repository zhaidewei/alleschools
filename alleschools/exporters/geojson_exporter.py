from __future__ import annotations

"""
GeoJSON 导出：按学校输出 FeatureCollection，便于地图工具使用。

几何坐标来自可选的 PC4/邮编 → (lat, lon) 查找表；未配置或查不到时 geometry 为 null。
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


def _load_pc4_centroids(path: Optional[Path]) -> Dict[str, Tuple[float, float]]:
    """
    从 CSV 加载 pc4 -> (lat, lon)。
    期望列名：pc4, lat, lon（或 postcode, lat, lon，取前 4 位作为 key）。
    返回 dict: pc4 -> (lat, lon)。
    """
    out: Dict[str, Tuple[float, float]] = {}
    p = Path(path) if path else None
    if not p or not p.is_file():
        return out
    with p.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return out
        # 支持 pc4 或 postcode 列
        key_col = "pc4" if "pc4" in (reader.fieldnames or []) else "postcode"
        if key_col not in (reader.fieldnames or []) or "lat" not in (reader.fieldnames or []) or "lon" not in (reader.fieldnames or []):
            return out
        for row in reader:
            k = (row.get(key_col) or "").strip()
            if key_col == "postcode" and len(k) >= 4:
                k = k[:4]
            if not k:
                continue
            try:
                lat = float(row.get("lat", 0))
                lon = float(row.get("lon", 0))
                out[k] = (lat, lon)
            except (TypeError, ValueError):
                continue
    return out


def _row_to_properties(row: Mapping[str, Any]) -> Dict[str, Any]:
    """将一行转为 JSON 可序列化的 properties 字典。"""
    return {k: v for k, v in row.items()}


def export_geojson(
    rows: Iterable[Mapping[str, Any]],
    path: Path,
    lookup_path: Optional[str] = None,
) -> None:
    """
    将学校结果写出为 GeoJSON FeatureCollection。

    - properties：每行所有键值（与主 CSV 列一致）。
    - geometry：若 lookup_path 指向的 CSV 中存在该行的 PC4（由 postcode 前 4 位得到）则为 Point(lon, lat)，否则为 null。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    centroids = _load_pc4_centroids(Path(lookup_path) if (lookup_path and str(lookup_path).strip()) else None)
    features: List[Dict[str, Any]] = []
    for row in rows:
        props = _row_to_properties(dict(row))
        pc4 = (str(row.get("postcode") or "").strip())[:4]
        coords = centroids.get(pc4) if pc4 else None
        if coords is not None:
            lat, lon = coords
            geometry = {"type": "Point", "coordinates": [lon, lat]}
        else:
            geometry = None
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geometry,
        })
    fc = {"type": "FeatureCollection", "features": features}
    with path.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)


__all__ = ["export_geojson"]
