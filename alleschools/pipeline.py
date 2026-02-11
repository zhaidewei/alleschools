from __future__ import annotations

"""
高层流水线封装。

- PO：加载 WOZ + DUO Schooladviezen → 计算 X/Y → 写出 CSV、excluded JSON、运行报告
- VO：加载 Vestigingen + 考试 CSV → 计算 X/Y → 写出 CSV、excluded JSON、运行报告
"""

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from alleschools import config as config_mod
from alleschools import schema_validator as sv
from alleschools.compute import (
    compute_po_xy,
    compute_vo_xy,
    compute_vwo_mean_latest_year,
    compute_vwo_profile_indices,
)
from alleschools.exporters import csv_exporter, geojson_exporter, json_exporter, long_table_exporter
from alleschools.exporters.meta_builder import (
    SCHEMA_VERSION,
    build_po_meta,
    build_vo_meta,
    build_vo_profiles_meta,
)
from alleschools.exporters.points_exporter import export_po_points, export_vo_points
from alleschools.loaders import (
    cbs_loader,
    duo_loader,
    vo_loader,
    load_vwo_exam_cijferlijst_scores,
    load_vwo_central_exam_scores,
)
from alleschools.logging_utils import setup_logger
from alleschools.quality import run_po_quality, run_vo_quality


def _get_git_commit(cwd: Path) -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=2,
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def run_po_pipeline(config: Optional[Dict[str, Any]] = None) -> tuple[Path, Dict[str, Any]]:
    """
    运行小学 PO X/Y 计算流水线。

    参数:
        config: 可选配置字典；若未提供，则从 config.yaml 加载（build_effective_config()）。

    返回:
        (csv_path, stats) 元组，其中 stats 至少包含:
            - n_schools: 写出的学校数量
            - n_excluded: 被排除学校数量
            - excluded_path: 被排除学校 JSON 路径
    """
    if config is None:
        # 使用统一配置构造函数，默认 profile 即可保持当前行为
        config = config_mod.build_effective_config()

    start = datetime.now(timezone.utc)
    data_root = Path(config.get("data_root") or config_mod.PROJECT_ROOT)
    # 原始数据目录：允许通过 raw_subdir 将 DUO/CBS 源文件移出项目根，便于 .gitignore 管理。
    raw_sub = str(config.get("raw_subdir") or "").strip()
    raw_root = data_root / raw_sub if raw_sub and not Path(raw_sub).is_absolute() else (
        Path(raw_sub) if raw_sub else data_root
    )
    po_cfg: Dict[str, Any] = dict(config.get("po") or {})
    input_cfg: Dict[str, Any] = dict(po_cfg.get("input") or {})
    output_cfg: Dict[str, Any] = dict(po_cfg.get("output") or {})

    # 初始化 logger（此处使用默认级别与 stderr 输出）
    logger = setup_logger()
    logger.info("Starting PO pipeline")

    # 1. 加载 WOZ（从原始数据目录）
    woz_rel = input_cfg.get("cbs_woz_csv") or "cbs_woz_per_postcode_year.csv"
    woz_path = raw_root / woz_rel
    woz, woz_years = cbs_loader.load_woz_pc4_year(str(woz_path))
    logger.info(
        "Loaded WOZ data",
        extra={"woz_entries": len(woz), "woz_years": list(woz_years)},
    )

    # 2. 加载 DUO Schooladviezen（从原始数据目录）
    schools = duo_loader.load_schooladviezen_po(str(raw_root))
    logger.info(
        "Loaded PO schooladviezen",
        extra={
            "n_schools": len(schools),
            "n_year_records": sum(len(s.get("years", {})) for s in schools.values()),
        },
    )

    # 必要输入缺失时写出 run_report 并提前返回（与 VO 行为一致）
    if not schools:
        logger.error("No PO schooladviezen data found")
        end = datetime.now(timezone.utc)
        duration = (end - start).total_seconds()
        csv_rel = output_cfg.get("csv") or "schools_xy_coords_po.csv"
        csv_path = data_root / csv_rel
        report_path = data_root / "run_report_po.json"
        run_report = {
            "pipeline_type": "po",
            "profile": config.get("profile"),
            "config_path": config.get("config_path"),
            "started_at": start.isoformat(),
            "finished_at": end.isoformat(),
            "duration_seconds": duration,
            "inputs": {"data_root": str(data_root), "po": input_cfg},
            "outputs": {
                "po": {
                    "csv_path": csv_rel,
                    "excluded_path": None,
                    "n_schools": 0,
                    "n_excluded": 0,
                    "geojson_path": None,
                    "long_table_path": None,
                    "points_path": None,
                    "meta_path": None,
                }
            },
            "summary": {"status": "error", "warnings": [], "errors": ["No PO schooladviezen data found"]},
        }
        json_exporter.export_json([run_report], report_path)
        stats = {
            "n_schools": 0,
            "n_excluded": 0,
            "excluded_path": "",
            "run_report_path": str(report_path),
            "summary_status": "error",
        }
        return csv_path, stats

    # 3. 计算 X/Y
    missing_cfg: Dict[str, Any] = dict(po_cfg.get("missing_values") or {})
    woz_strategy = str(missing_cfg.get("woz_strategy") or "nearest_year")
    outliers_cfg: Dict[str, Any] = dict(po_cfg.get("outliers") or {})
    rows_out, excluded = compute_po_xy(
        schools,
        woz,
        woz_years,
        woz_strategy=woz_strategy,
        outliers=outliers_cfg or None,
    )

    # 隐私抑制：根据 privacy.min_group_size 过滤过小样本（额外于业务阈值）。
    privacy_global: Dict[str, Any] = dict(config.get("privacy") or {})
    privacy_po: Dict[str, Any] = dict(po_cfg.get("privacy") or {})
    min_group_size_priv = privacy_po.get("min_group_size", privacy_global.get("min_group_size", 0)) or 0
    max_detail_level = privacy_po.get("max_detail_level", privacy_global.get("max_detail_level", "school"))
    privacy_excluded: List[Dict[str, Any]] = []
    if isinstance(min_group_size_priv, int) and min_group_size_priv > 0:
        kept: List[Dict[str, Any]] = []
        for row in rows_out:
            pupils_total = int(row.get("pupils_total") or 0)
            if pupils_total < min_group_size_priv:
                privacy_excluded.append({"BRIN": row.get("BRIN"), "pupils_total": pupils_total})
            else:
                kept.append(row)
        rows_out = kept

    # 4. 导出
    # 所有导出产物默认与 csv 位于同一目录（通常为 generated/ 前缀），
    # 通过 csv_rel 的父目录统一控制，便于在 config.yaml 中集中修改。
    csv_rel = output_cfg.get("csv") or "schools_xy_coords_po.csv"
    csv_path = data_root / csv_rel
    csv_rel_path = Path(csv_rel)
    out_dir_rel = csv_rel_path.parent  # 例如 "generated"
    stem = csv_rel_path.stem

    excluded_rel = output_cfg.get("excluded_json") or str(out_dir_rel / "excluded_schools_po.json")
    excluded_path = data_root / excluded_rel
    geo_rel_default = out_dir_rel / f"{stem}_geo.json"
    long_rel_default = out_dir_rel / f"{stem}_long.csv"
    points_rel_default = out_dir_rel / f"{stem}.json"
    meta_rel_default = out_dir_rel / f"{stem}_meta.json"

    include_meta_columns = output_cfg.get("include_meta_columns", True)
    write_meta_json_flag = output_cfg.get("write_meta_json", True)

    csv_exporter.export_po_csv(rows_out, csv_path, include_meta_columns=include_meta_columns)
    json_exporter.export_json(excluded, excluded_path)

    geo_rel: Optional[str] = None
    long_rel: Optional[str] = None
    points_rel: Optional[str] = None
    meta_rel: Optional[str] = None

    if output_cfg.get("export_geojson", True):
        geo_rel = str(geo_rel_default)
        geo_path = data_root / geo_rel
        pc4_path = (output_cfg.get("pc4_centroids_path") or "").strip()
        lookup_path = (
            str(data_root / pc4_path) if pc4_path and not Path(pc4_path).is_absolute() else (pc4_path or None)
        )
        geojson_exporter.export_geojson(rows_out, geo_path, lookup_path=lookup_path)
    if output_cfg.get("export_long_table", True):
        long_rel = str(long_rel_default)
        long_path = data_root / long_rel
        long_table_exporter.export_po_long_table(
            rows_out, long_path, include_meta_columns=include_meta_columns
        )
    points_path = None
    if output_cfg.get("export_points_json", True):
        points_rel = str(points_rel_default)
        points_path = data_root / points_rel
        export_po_points(rows_out, points_path)

    end = datetime.now(timezone.utc)
    duration = (end - start).total_seconds()

    dq_cfg: Dict[str, Any] = dict(po_cfg.get("data_quality") or {})
    data_quality: Optional[Dict[str, Any]] = None
    if dq_cfg.get("enabled", True):
        data_quality = run_po_quality(
            rows_out,
            excluded,
            raw_root,
            input_cfg,
            max_brins_in_report=int(dq_cfg.get("max_brins_in_report") or 50),
        )
        if dq_cfg.get("write_standalone_report"):
            dq_path = data_root / "data_quality_report_po.json"
            json_exporter.write_meta_json(
                {
                    "pipeline_type": "po",
                    "data_quality": data_quality,
                    "generated_at": end.isoformat(),
                    "schema_version": SCHEMA_VERSION,
                },
                dq_path,
            )

    # 构建运行报告（此时 meta 可能尚未写出，但可以先占位 meta_path/schema_version）
    run_report: Dict[str, Any] = {
        "pipeline_type": "po",
        "profile": config.get("profile"),
        "config_path": config.get("config_path"),
        "started_at": start.isoformat(),
        "finished_at": end.isoformat(),
        "duration_seconds": duration,
        "inputs": {
            "data_root": str(data_root),
            "po": {
                "duo_schooladviezen_pattern": input_cfg.get(
                    "duo_schooladviezen_pattern",
                ),
                "cbs_woz_csv": str(woz_path),
            },
        },
        "outputs": {
            "po": {
                # 所有输出路径在 run_report 中统一使用相对于 data_root 的相对路径，避免泄漏本机绝对路径，
                # 也便于在 Vercel 等环境中直接复用。
                "csv_path": csv_rel,
                "excluded_path": excluded_rel,
                "n_schools": len(rows_out),
                "n_excluded": len(excluded),
                "geojson_path": geo_rel if geo_rel is not None else None,
                "long_table_path": long_rel if long_rel is not None else None,
                "points_path": points_rel if points_rel is not None else None,
                "meta_path": None,
                "schema_version": SCHEMA_VERSION if write_meta_json_flag else None,
            }
        },
        "summary": {"status": "success", "warnings": [], "errors": []},
        "privacy": {
            "min_group_size": int(min_group_size_priv),
            "max_detail_level": max_detail_level,
            "n_suppressed": len(privacy_excluded),
        },
    }
    if data_quality is not None:
        run_report["data_quality"] = data_quality
        if privacy_excluded:
            run_report["data_quality"]["privacy_suppressed"] = {
                "count": len(privacy_excluded),
                "brins": [p["BRIN"] for p in privacy_excluded[: po_cfg.get("data_quality", {}).get("max_brins_in_report", 50)]],
            }

    meta_path = None
    if write_meta_json_flag:
        meta_rel = str(meta_rel_default)
        meta_path = data_root / meta_rel
        meta_columns = list(csv_exporter.PO_META_FIELDNAMES) if include_meta_columns else []
        fieldnames = list(csv_exporter.PO_FIELDNAMES) + meta_columns
        meta_dict = build_po_meta(
            csv_path,
            row_count=len(rows_out),
            columns=fieldnames,
            outliers=outliers_cfg or None,
        )
        json_exporter.write_meta_json(meta_dict, meta_path)

    # 可选：在流水线末尾对导出的 points/meta/GeoJSON/长表进行 schema 校验，
    # 并将错误（若有）写入 run_report.summary.errors。
    schema_val_cfg: Dict[str, Any] = dict(output_cfg.get("schema_validation") or {})
    if schema_val_cfg.get("enabled") and meta_path is not None:
        schema_errors: list[Dict[str, Any]] = []

        # points + meta 校验
        if points_path is not None:
            try:
                points_data = json.loads(Path(points_path).read_text(encoding="utf-8"))
                meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
                errs = sv.validate_points_against_meta(points_data, meta_data, layer="po")
                for e in errs:
                    d = e.to_dict()
                    d["artifact"] = "po_points_meta"
                    schema_errors.append(d)
            except Exception as exc:  # pragma: no cover - 极端 IO/JSON 异常
                schema_errors.append(
                    {
                        "kind": "schema_validator_exception",
                        "message": str(exc),
                        "artifact": "po_points_meta",
                    }
                )

        # GeoJSON 校验
        if output_cfg.get("export_geojson", True):
            geo_path = data_root / (csv_path.stem + "_geo.json")
            if geo_path.exists():
                try:
                    geo = json.loads(geo_path.read_text(encoding="utf-8"))
                    errs = sv.validate_geojson_schema(geo, layer="po")
                    for e in errs:
                        d = e.to_dict()
                        d["artifact"] = "po_geojson"
                        schema_errors.append(d)
                except Exception as exc:  # pragma: no cover
                    schema_errors.append(
                        {
                            "kind": "schema_validator_exception",
                            "message": str(exc),
                            "artifact": "po_geojson",
                        }
                    )

        # 长表 CSV 校验
        if output_cfg.get("export_long_table", True):
            long_path = data_root / (csv_path.stem + "_long.csv")
            if long_path.exists():
                try:
                    with long_path.open(encoding="utf-8", newline="") as f:
                        reader = csv.DictReader(f)
                        long_rows = list(reader)
                    errs = sv.validate_long_table_schema(long_rows, layer="po")
                    for e in errs:
                        d = e.to_dict()
                        d["artifact"] = "po_long_table"
                        schema_errors.append(d)
                except Exception as exc:  # pragma: no cover
                    schema_errors.append(
                        {
                            "kind": "schema_validator_exception",
                            "message": str(exc),
                            "artifact": "po_long_table",
                        }
                    )

        if schema_errors:
            summary = run_report.get("summary") or {}
            errors_list = summary.get("errors") or []
            errors_list.append({"kind": "schema_validation", "details": schema_errors})
            summary["errors"] = errors_list
            run_report["summary"] = summary

    # 补回运行报告中的 meta_path 引用并写出（同样使用相对于 data_root 的相对路径）
    if meta_rel is not None:
        run_report["outputs"]["po"]["meta_path"] = meta_rel

    report_path = data_root / "run_report_po.json"
    # 使用 export_json 写单个对象时包在列表里，保持现有格式习惯
    json_exporter.export_json([run_report], report_path)

    logger.info(
        "PO pipeline finished",
        extra={
            "csv_path": str(csv_path),
            "n_schools": len(rows_out),
            "n_excluded": len(excluded),
            "duration_seconds": duration,
        },
    )

    stats: Dict[str, Any] = {
        "n_schools": len(rows_out),
        "n_excluded": len(excluded),
        "excluded_path": str(excluded_path),
        "run_report_path": str(report_path),
        "summary_status": run_report["summary"].get("status", "success"),
    }
    if meta_path is not None:
        stats["meta_path"] = str(meta_path)
    if geo_rel is not None:
        stats["geojson_path"] = str(data_root / geo_rel)
    if long_rel is not None:
        stats["long_table_path"] = str(data_root / long_rel)
    if points_path is not None:
        stats["points_path"] = str(points_path)

    return csv_path, stats


def run_vo_pipeline(config: Optional[Dict[str, Any]] = None) -> tuple[Path, Dict[str, Any]]:
    """
    运行中学 VO X/Y 计算流水线。

    返回 (csv_path, stats)，stats 含 n_schools, n_excluded, excluded_path, run_report_path。
    若输入文件不存在，仍写出 run_report_vo.json（status=error），并返回 would-be csv_path 与 stats。
    """
    if config is None:
        config = config_mod.build_effective_config()

    start = datetime.now(timezone.utc)
    data_root = Path(config.get("data_root") or config_mod.PROJECT_ROOT)
    raw_sub = str(config.get("raw_subdir") or "").strip()
    raw_root = data_root / raw_sub if raw_sub and not Path(raw_sub).is_absolute() else (
        Path(raw_sub) if raw_sub else data_root
    )
    vo_cfg: Dict[str, Any] = dict(config.get("vo") or {})
    input_cfg: Dict[str, Any] = dict(vo_cfg.get("input") or {})
    output_cfg: Dict[str, Any] = dict(vo_cfg.get("output") or {})
    thresholds: Dict[str, Any] = dict(vo_cfg.get("thresholds") or {})
    weights_cfg: Dict[str, Any] = dict(vo_cfg.get("weights") or {})
    year_cols: List[Any] = list(weights_cfg.get("year_cols") or [])
    min_havo_vwo_total = int(thresholds.get("min_havo_vwo_total") or 20)
    min_vwo_subjects_per_year = int(thresholds.get("min_vwo_subjects_per_year") or 3)

    logger = setup_logger(name="alleschools.vo")
    logger.info("Starting VO pipeline")

    vestigingen_csv = input_cfg.get("duo_vestigingen_vo_csv") or "duo_vestigingen_vo.csv"
    brin_to_postcode = vo_loader.load_vestigingen_postcode(str(raw_root), vestigingen_csv)
    if brin_to_postcode:
        logger.info("Loaded vestigingen postcode", extra={"n": len(brin_to_postcode)})
    else:
        logger.info("No duo_vestigingen_vo.csv found; postcode column will be empty")

    exams_all = input_cfg.get("exams_all_csv") or "duo_examen_raw_all.csv"
    exams_small = input_cfg.get("exams_small_csv") or "duo_examen_raw.csv"
    if not year_cols:
        # 内建默认与 config 一致
        year_cols = [
            [13, 14, "2019-2020", 0.2],
            [22, 23, "2020-2021", 0.4],
            [31, 32, "2021-2022", 0.6],
            [40, 41, "2022-2023", 0.8],
            [49, 50, "2023-2024", 1.0],
        ]

    schools = vo_loader.load_exam_schools(str(raw_root), exams_all, exams_small, year_cols)
    if not schools:
        logger.error("VO input file not found (exams_all or exams_small)")
        end = datetime.now(timezone.utc)
        duration = (end - start).total_seconds()
        report_path = data_root / "run_report_vo.json"
        run_report = {
            "pipeline_type": "vo",
            "profile": config.get("profile"),
            "config_path": config.get("config_path"),
            "started_at": start.isoformat(),
            "finished_at": end.isoformat(),
            "duration_seconds": duration,
            "inputs": {"data_root": str(data_root), "vo": input_cfg},
            "outputs": {"vo": {"csv_path": None, "excluded_path": None, "n_schools": 0, "n_excluded": 0}},
            "summary": {"status": "error", "warnings": [], "errors": ["Input exam CSV not found"]},
        }
        json_exporter.export_json([run_report], report_path)
        csv_rel = output_cfg.get("csv") or "schools_xy_coords.csv"
        csv_path = data_root / csv_rel
        stats = {
            "n_schools": 0,
            "n_excluded": 0,
            "excluded_path": "",
            "run_report_path": str(report_path),
            "summary_status": "error",
        }
        return csv_path, stats

    logger.info("Loaded VO exam schools", extra={"n_schools": len(schools)})

    outliers_cfg_vo: Dict[str, Any] = dict(vo_cfg.get("outliers") or {})
    rows_out, excluded = compute_vo_xy(
        schools,
        brin_to_postcode,
        year_cols,
        min_havo_vwo_total,
        outliers=outliers_cfg_vo or None,
    )

    # ------------------------------------------------------------------
    # VWO profiel 指数（NT/NG/EM/CM）—— 基于 VWO 统考的四个 X 轴
    # ------------------------------------------------------------------
    # 设计取舍记录：
    # - 我们保留现有 VO 宽表 X/Y（学术度 × 理科度）作为主图不变，
    #   另行导出 4 组「profiel 指数」点集给前端使用，避免破坏已有视图。
    # - profiel 指数完全遵循 backlog 3.5：按指定科目的 VWO 统考平均分组合，
    #   不再使用此前的「所有 VWO 科目 cijferlijst 中位数/平均数」方案。
    # - 时间加权采用最近 5 学年，权重 w_0..w_4 = 5,4,3,2,1，其中 w_0 对应最新学年。
    vwo_exam_files = {
        "2020-2021": "examenkandidaten-vwo-en-examencijfers-2020-2021.csv",
        "2021-2022": "examenkandidaten-vwo-en-examencijfers-2021-2022.csv",
        "2022-2023": "examenkandidaten-vwo-en-examencijfers-2022-2023.csv",
        "2023-2024": "examenkandidaten-vwo-en-examencijfers-2023-2024.csv",
        "2024-2025": "examenkandidaten-vwo-en-examencijfers-2024-2025.csv",
    }
    year_order = sorted(vwo_exam_files.keys())  # 升序："2020-2021" ... "2024-2025"
    # 最近学年权重最高：2024-2025 -> 5, 2023-2024 -> 4, ...
    year_weights: Dict[str, float] = {}
    weights_desc = [1.0, 2.0, 3.0, 4.0, 5.0]
    # Python 3.9 中内置 zip 不支持 strict 参数，这里依赖 year_order 与 weights_desc 长度一致的事实。
    for label, w in zip(year_order, weights_desc):
        year_weights[label] = w

    vwo_central = load_vwo_central_exam_scores(str(raw_root), vwo_exam_files)
    profile_indices: Dict[str, Dict[str, float]] = {}
    if vwo_central:
        profile_indices = compute_vwo_profile_indices(
            vwo_central,
            year_order=year_order,
            year_weights=year_weights,
        )

    # 隐私抑制：根据 privacy.min_group_size 过滤过小样本（VO 使用 candidates_total）。
    privacy_global_vo: Dict[str, Any] = dict(config.get("privacy") or {})
    privacy_vo_cfg: Dict[str, Any] = dict(vo_cfg.get("privacy") or {})
    min_group_size_priv_vo = privacy_vo_cfg.get("min_group_size", privacy_global_vo.get("min_group_size", 0)) or 0
    max_detail_level_vo = privacy_vo_cfg.get("max_detail_level", privacy_global_vo.get("max_detail_level", "school"))
    privacy_excluded_vo: List[Dict[str, Any]] = []
    if isinstance(min_group_size_priv_vo, int) and min_group_size_priv_vo > 0:
        kept_vo: List[Dict[str, Any]] = []
        for row in rows_out:
            cand_total = int(row.get("candidates_total") or 0)
            if cand_total < min_group_size_priv_vo:
                privacy_excluded_vo.append({"BRIN": row.get("BRIN"), "candidates_total": cand_total})
            else:
                kept_vo.append(row)
        rows_out = kept_vo

    csv_rel = output_cfg.get("csv") or "schools_xy_coords.csv"
    csv_path = data_root / csv_rel
    csv_rel_path = Path(csv_rel)
    out_dir_rel = csv_rel_path.parent
    stem = csv_rel_path.stem

    excluded_rel = output_cfg.get("excluded_json") or str(out_dir_rel / "excluded_schools.json")
    excluded_path = data_root / excluded_rel
    geo_rel_default = out_dir_rel / f"{stem}_geo.json"
    long_rel_default = out_dir_rel / f"{stem}_long.csv"
    points_rel_default = out_dir_rel / f"{stem}.json"
    meta_rel_default = out_dir_rel / f"{stem}_meta.json"
    include_meta_columns = output_cfg.get("include_meta_columns", True)
    write_meta_json_flag = output_cfg.get("write_meta_json", True)

    csv_exporter.export_vo_csv(rows_out, csv_path, include_meta_columns=include_meta_columns)
    json_exporter.export_json(excluded, excluded_path)

    geo_rel: Optional[str] = None
    long_rel: Optional[str] = None
    points_rel: Optional[str] = None
    meta_rel: Optional[str] = None

    # ------------------------------------------------------------------
    # VO profiel 指数导出（CSV + points JSON + meta）
    # ------------------------------------------------------------------
    profiles_csv_rel: Dict[str, Optional[str]] = {"NT": None, "NG": None, "EM": None, "CM": None}
    profiles_points_rel: Dict[str, Optional[str]] = {"NT": None, "NG": None, "EM": None, "CM": None}
    profiles_meta_rel: Optional[str] = None

    if profile_indices:
        # 为每个 profiel 组装点列表：与主 VO 宽表行 join，以 BRIN 对齐。
        profile_rows: Dict[str, list[Dict[str, Any]]] = {"NT": [], "NG": [], "EM": [], "CM": []}
        for row in rows_out:
            brin = row.get("BRIN")
            if not brin:
                continue
            brin_str = str(brin)
            naam = row.get("vestigingsnaam")
            gemeente = row.get("gemeente")
            postcode = (row.get("postcode") or "").strip()
            # backlog 约定：现有 VO 主图的 X 轴（VWO 占比）作为 profiel 图的 Y 轴。
            y_vwo_share = row.get("X_linear")
            candidates_total = row.get("candidates_total")
            candidates_weighted_avg = row.get("candidates_weighted_avg")

            for prof in ("NT", "NG", "EM", "CM"):
                prof_map = profile_indices.get(prof) or {}
                x_prof = prof_map.get(brin_str)
                if x_prof is None:
                    continue
                # 进入 profile 的学校必有 VWO 统考数据，统一标为 HAVO/VWO（避免主表 type=VMBO 的误标）
                profile_rows[prof].append(
                    {
                        "BRIN": brin_str,
                        "vestigingsnaam": naam,
                        "naam": naam,
                        "gemeente": gemeente,
                        "postcode": postcode,
                        "type": "HAVO/VWO",
                        "profile_id": prof,
                        "X_profile": float(x_prof),
                        "Y_vwo_share": float(y_vwo_share) if y_vwo_share is not None else None,
                        "candidates_total": int(candidates_total or 0),
                        "candidates_weighted_avg": (
                            float(candidates_weighted_avg)
                            if candidates_weighted_avg is not None
                            else None
                        ),
                    }
                )

        # 写出 4 个 CSV + 4 个 points JSON（相对路径固定在主 VO CSV 的目录下）
        for prof in ("NT", "NG", "EM", "CM"):
            rows_prof = profile_rows.get(prof) or []
            if not rows_prof:
                continue
            csv_rel_prof = str(out_dir_rel / f"schools_profiles_{prof.lower()}.csv")
            points_rel_prof = str(out_dir_rel / f"schools_profiles_{prof.lower()}.json")
            csv_path_prof = data_root / csv_rel_prof
            points_path_prof = data_root / points_rel_prof

            csv_exporter.export_vo_profiles_csv(rows_prof, csv_path_prof)
            json_exporter.export_json(rows_prof, points_path_prof)

            profiles_csv_rel[prof] = csv_rel_prof
            profiles_points_rel[prof] = points_rel_prof


    if output_cfg.get("export_geojson", True):
        geo_rel = str(geo_rel_default)
        geo_path = data_root / geo_rel
        pc4_path = (output_cfg.get("pc4_centroids_path") or "").strip()
        lookup_path = (
            str(data_root / pc4_path) if pc4_path and not Path(pc4_path).is_absolute() else (pc4_path or None)
        )
        geojson_exporter.export_geojson(rows_out, geo_path, lookup_path=lookup_path)
    if output_cfg.get("export_long_table", True):
        long_rel = str(long_rel_default)
        long_path = data_root / long_rel
        long_table_exporter.export_vo_long_table(
            rows_out, long_path, include_meta_columns=include_meta_columns
        )
    points_path = None
    if output_cfg.get("export_points_json", True):
        points_rel = str(points_rel_default)
        points_path = data_root / points_rel
        export_vo_points(rows_out, points_path)

    end = datetime.now(timezone.utc)
    duration = (end - start).total_seconds()

    dq_cfg_vo: Dict[str, Any] = dict(vo_cfg.get("data_quality") or {})
    data_quality_vo: Optional[Dict[str, Any]] = None
    if dq_cfg_vo.get("enabled", True):
        data_quality_vo = run_vo_quality(
            rows_out,
            excluded,
            raw_root,
            input_cfg,
            max_brins_in_report=int(dq_cfg_vo.get("max_brins_in_report") or 50),
        )
        if dq_cfg_vo.get("write_standalone_report"):
            dq_path_vo = data_root / "data_quality_report_vo.json"
            json_exporter.write_meta_json(
                {
                    "pipeline_type": "vo",
                    "data_quality": data_quality_vo,
                    "generated_at": end.isoformat(),
                    "schema_version": SCHEMA_VERSION,
                },
                dq_path_vo,
            )

    run_report = {
        "pipeline_type": "vo",
        "profile": config.get("profile"),
        "config_path": config.get("config_path"),
        "started_at": start.isoformat(),
        "finished_at": end.isoformat(),
        "duration_seconds": duration,
        "inputs": {
            "data_root": str(data_root),
            "vo": {
                "exams_all_csv": exams_all,
                "exams_small_csv": exams_small,
                "duo_vestigingen_vo_csv": vestigingen_csv,
            },
        },
        "outputs": {
            "vo": {
                # 与 PO 一致，在运行报告中使用相对于 data_root 的路径片段。
                "csv_path": csv_rel,
                "excluded_path": excluded_rel,
                "n_schools": len(rows_out),
                "n_excluded": len(excluded),
                "geojson_path": geo_rel if geo_rel is not None else None,
                "long_table_path": long_rel if long_rel is not None else None,
                "points_path": points_rel if points_rel is not None else None,
                "meta_path": None,
                "schema_version": SCHEMA_VERSION if write_meta_json_flag else None,
                # VO profiel 导出产物：在有数据时填充具体路径（相对于 data_root）
                "profiles_csv_paths": None,
                "profiles_points_paths": None,
                "profiles_meta_path": None,
            }
        },
        "summary": {"status": "success", "warnings": [], "errors": []},
        "privacy": {
            "min_group_size": int(min_group_size_priv_vo),
            "max_detail_level": max_detail_level_vo,
            "n_suppressed": len(privacy_excluded_vo),
        },
    }
    if data_quality_vo is not None:
        run_report["data_quality"] = data_quality_vo
        if privacy_excluded_vo:
            run_report["data_quality"]["privacy_suppressed"] = {
                "count": len(privacy_excluded_vo),
                "brins": [
                    p["BRIN"]
                    for p in privacy_excluded_vo[: vo_cfg.get("data_quality", {}).get("max_brins_in_report", 50)]
                ],
            }
    meta_path = None
    if write_meta_json_flag:
        meta_rel = str(meta_rel_default)
        meta_path = data_root / meta_rel
        meta_columns = list(csv_exporter.VO_META_FIELDNAMES) if include_meta_columns else []
        vo_fieldnames = list(csv_exporter.VO_FIELDNAMES) + meta_columns
        meta_dict_vo = build_vo_meta(
            csv_path,
            row_count=len(rows_out),
            columns=vo_fieldnames,
            outliers=outliers_cfg_vo or None,
        )
        json_exporter.write_meta_json(meta_dict_vo, meta_path)

    # VO profiel meta：仅在存在至少一个 profiel CSV 时写出
    profiles_meta_path = None
    if any(profiles_csv_rel.values()):
        profiles_meta_rel = str(out_dir_rel / "schools_profiles_meta.json")
        profiles_meta_path = data_root / profiles_meta_rel
        # 构建 profile_id -> Path 与行数映射
        data_files_map: Dict[str, Path] = {}
        row_counts_map: Dict[str, int] = {}
        for prof, rel in profiles_csv_rel.items():
            if not rel:
                continue
            data_files_map[prof] = Path(rel)
            # 这里不重新读取 CSV，只依据导出时的列表长度；与 profiles_csv_rel 的 key 对应。
            # profile_rows 在上文中已按 profiel 聚合。
            # 为避免在此作用域重复构造，保守起见设置为 -1，表示“未知行数但存在文件”。
            row_counts_map[prof] = -1
        meta_profiles = build_vo_profiles_meta(
            data_files=data_files_map,
            row_counts=row_counts_map,
            y_domain=[0.0, 100.0],
        )
        json_exporter.write_meta_json(meta_profiles, profiles_meta_path)

    # 可选：在流水线末尾对导出的 points/meta/GeoJSON/长表进行 schema 校验，
    # 并将错误（若有）写入 run_report.summary.errors。
    schema_val_cfg_vo: Dict[str, Any] = dict(output_cfg.get("schema_validation") or {})
    if schema_val_cfg_vo.get("enabled") and meta_path is not None:
        schema_errors_vo: list[Dict[str, Any]] = []

        # points + meta 校验
        if points_path is not None:
            try:
                points_data_vo = json.loads(Path(points_path).read_text(encoding="utf-8"))
                meta_data_vo = json.loads(meta_path.read_text(encoding="utf-8"))
                errs_vo = sv.validate_points_against_meta(points_data_vo, meta_data_vo, layer="vo")
                for e in errs_vo:
                    d = e.to_dict()
                    d["artifact"] = "vo_points_meta"
                    schema_errors_vo.append(d)
            except Exception as exc:  # pragma: no cover
                schema_errors_vo.append(
                    {
                        "kind": "schema_validator_exception",
                        "message": str(exc),
                        "artifact": "vo_points_meta",
                    }
                )

        # GeoJSON 校验
        if output_cfg.get("export_geojson", True):
            geo_path_vo = data_root / (csv_path.stem + "_geo.json")
            if geo_path_vo.exists():
                try:
                    geo_vo = json.loads(geo_path_vo.read_text(encoding="utf-8"))
                    errs_vo = sv.validate_geojson_schema(geo_vo, layer="vo")
                    for e in errs_vo:
                        d = e.to_dict()
                        d["artifact"] = "vo_geojson"
                        schema_errors_vo.append(d)
                except Exception as exc:  # pragma: no cover
                    schema_errors_vo.append(
                        {
                            "kind": "schema_validator_exception",
                            "message": str(exc),
                            "artifact": "vo_geojson",
                        }
                    )

        # 长表 CSV 校验
        if output_cfg.get("export_long_table", True):
            long_path_vo = data_root / (csv_path.stem + "_long.csv")
            if long_path_vo.exists():
                try:
                    with long_path_vo.open(encoding="utf-8", newline="") as f:
                        reader_vo = csv.DictReader(f)
                        long_rows_vo = list(reader_vo)
                    errs_vo = sv.validate_long_table_schema(long_rows_vo, layer="vo")
                    for e in errs_vo:
                        d = e.to_dict()
                        d["artifact"] = "vo_long_table"
                        schema_errors_vo.append(d)
                except Exception as exc:  # pragma: no cover
                    schema_errors_vo.append(
                        {
                            "kind": "schema_validator_exception",
                            "message": str(exc),
                            "artifact": "vo_long_table",
                        }
                    )

        if schema_errors_vo:
            summary_vo = run_report.get("summary") or {}
            errors_list_vo = summary_vo.get("errors") or []
            errors_list_vo.append({"kind": "schema_validation", "details": schema_errors_vo})
            summary_vo["errors"] = errors_list_vo
            run_report["summary"] = summary_vo

    if meta_rel is not None:
        run_report["outputs"]["vo"]["meta_path"] = meta_rel
    if profiles_meta_path is not None:
        rel_profiles_meta = str(profiles_meta_path.relative_to(data_root))
        run_report["outputs"]["vo"]["profiles_meta_path"] = rel_profiles_meta
    # 仅当存在至少一个 profiles points/CSV 时记录对应映射（保持与其他路径一样使用相对路径）
    if any(profiles_points_rel.values()):
        run_report["outputs"]["vo"]["profiles_points_paths"] = {
            prof: rel for prof, rel in profiles_points_rel.items() if rel
        }
    if any(profiles_csv_rel.values()):
        run_report["outputs"]["vo"]["profiles_csv_paths"] = {
            prof: rel for prof, rel in profiles_csv_rel.items() if rel
        }

    report_path = data_root / "run_report_vo.json"
    json_exporter.export_json([run_report], report_path)

    logger.info(
        "VO pipeline finished",
        extra={
            "csv_path": str(csv_path),
            "n_schools": len(rows_out),
            "n_excluded": len(excluded),
            "duration_seconds": duration,
        },
    )

    stats: Dict[str, Any] = {
        "n_schools": len(rows_out),
        "n_excluded": len(excluded),
        "excluded_path": str(excluded_path),
        "run_report_path": str(report_path),
        "summary_status": run_report["summary"].get("status", "success"),
    }
    if meta_path is not None:
        stats["meta_path"] = str(meta_path)
    if geo_rel is not None:
        stats["geojson_path"] = str(data_root / geo_rel)
    if long_rel is not None:
        stats["long_table_path"] = str(data_root / long_rel)
    if points_path is not None:
        stats["points_path"] = str(points_path)
    return csv_path, stats


__all__ = ["run_po_pipeline", "run_vo_pipeline"]


