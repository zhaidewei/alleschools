from __future__ import annotations

"""
命令行入口。

示例用法：

    python -m alleschools.cli po --profile default
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from alleschools import config as config_mod
from alleschools import etl as etl_mod
from alleschools import schema_validator as sv
from alleschools.pipeline import run_po_pipeline, run_vo_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alleschools")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--profile", type=str, default=None, help="Config profile name")
    parser.add_argument(
        "--data-root",
        type=str,
        default=None,
        help="Override data_root (base directory for input files)",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Override output_root (base directory for outputs)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 旧版语法糖：直接跑单层 ETL（保留向后兼容）
    subparsers.add_parser("po", help="Run PO (primary schools) pipeline")
    subparsers.add_parser("vo", help="Run VO (secondary schools) pipeline")

    # 新版统一入口：只 fetch 原始数据
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch/update raw source data (DUO/CBS) only",
    )
    fetch_group = fetch_parser.add_mutually_exclusive_group()
    fetch_group.add_argument("--all", action="store_true", help="Fetch all sources (VO, PO, CBS WOZ)")
    fetch_parser.add_argument(
        "--vo",
        action="store_true",
        help="Fetch VO exam data (and vestigingen list)",
    )
    fetch_parser.add_argument(
        "--po",
        action="store_true",
        help="Fetch PO schooladviezen data",
    )
    fetch_parser.add_argument(
        "--cbs-woz",
        action="store_true",
        help="Fetch CBS WOZ per PC4 data",
    )

    # 只跑聚合 ETL，不主动下载
    etl_parser = subparsers.add_parser(
        "etl",
        help="Run aggregation pipeline only (no fetching)",
    )
    etl_group = etl_parser.add_mutually_exclusive_group()
    etl_group.add_argument("--all", action="store_true", help="Run VO + PO pipelines")
    etl_group.add_argument("--vo", action="store_true", help="Run VO pipeline only")
    etl_group.add_argument("--po", action="store_true", help="Run PO pipeline only")

    # 一键从 fetch -> etl（可用于本地/CI/Vercel）
    full_parser = subparsers.add_parser(
        "full",
        help="Fetch raw data then run ETL (VO/PO)",
    )
    full_group = full_parser.add_mutually_exclusive_group()
    full_group.add_argument("--all", action="store_true", help="Fetch+ETL for both VO and PO")
    full_group.add_argument("--vo", action="store_true", help="Fetch+ETL for VO layer only")
    full_group.add_argument("--po", action="store_true", help="Fetch+ETL for PO layer only")

    # validate 子命令：对已导出的 data/meta 进行 schema 校验
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate exported data/meta files against schema",
    )
    validate_parser.add_argument(
        "--layer",
        choices=["po", "vo"],
        required=True,
        help="Layer to validate (po or vo)",
    )
    validate_parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Override path to points data JSON (defaults to generated path based on config)",
    )
    validate_parser.add_argument(
        "--meta",
        type=str,
        default=None,
        help="Override path to meta JSON (defaults to generated path based on config)",
    )

    return parser


def make_effective_config(args: argparse.Namespace) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if args.data_root:
        overrides["data_root"] = args.data_root
    if args.output_root:
        overrides["output_root"] = args.output_root

    config_path = None
    if args.config:
        from pathlib import Path

        config_path = Path(args.config)

    return config_mod.build_effective_config(
        profile=args.profile,
        overrides=overrides or None,
        config_path=config_path,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = make_effective_config(args)

    # 向后兼容：旧的 po / vo 子命令等价于新的 etl --po/--vo
    if args.command == "po":
        csv_path, stats = run_po_pipeline(cfg)
        n = int(stats.get("n_schools", 0))
        n_excluded = int(stats.get("n_excluded", 0))
        print(f"PO: 已写入 {csv_path}（共 {n} 所小学，排除 {n_excluded} 所）")
        if stats.get("run_report_path"):
            print(f"PO 运行报告: {stats['run_report_path']}")
        return 0

    if args.command == "vo":
        csv_path, stats = run_vo_pipeline(cfg)
        n = int(stats.get("n_schools", 0))
        n_excluded = int(stats.get("n_excluded", 0))
        print(f"VO: 已写入 {csv_path}（共 {n} 所中学，排除 {n_excluded} 所）")
        if stats.get("run_report_path"):
            print(f"VO 运行报告: {stats['run_report_path']}")
        return 0

    if args.command == "fetch":
        vo = bool(args.vo or args.all)
        po = bool(args.po or args.all)
        cbs_woz = bool(args.cbs_woz or args.all)
        # 若用户未显式指定任何层，则默认等价于 --all
        if not (vo or po or cbs_woz):
            vo = po = cbs_woz = True
        etl_mod.run_fetch_from_cli_args(cfg, vo=vo, po=po, cbs_woz=cbs_woz)
        return 0

    if args.command == "etl":
        vo = bool(args.vo or args.all)
        po = bool(args.po or args.all)
        if not (vo or po):
            vo = po = True
        had_error = etl_mod.run_etl_from_cli_args(cfg, vo=vo, po=po)
        return 1 if had_error else 0

    if args.command == "full":
        vo = bool(args.vo or args.all)
        po = bool(args.po or args.all)
        if not (vo or po):
            vo = po = True
        # 1) fetch 原始数据
        etl_mod.run_fetch_from_cli_args(cfg, vo=vo, po=po, cbs_woz=True)
        # 2) 跑 ETL
        had_error = etl_mod.run_etl_from_cli_args(cfg, vo=vo, po=po)
        # schema 校验与错误合并逻辑由 pipeline 中的 schema_validation 配置控制
        return 1 if had_error else 0

    if args.command == "validate":
        layer = args.layer
        data_path_arg = args.data
        meta_path_arg = args.meta

        # 根据 config 中的 output.csv 计算默认的 points/meta 路径
        root = Path(cfg.get("data_root") or cfg.get("output_root") or ".")
        if layer == "po":
            out_cfg = dict(cfg.get("po", {}).get("output", {}) or {})
        else:
            out_cfg = dict(cfg.get("vo", {}).get("output", {}) or {})
        csv_rel = out_cfg.get("csv") or (
            "generated/schools_xy_coords_po.csv" if layer == "po" else "generated/schools_xy_coords.csv"
        )
        csv_path = Path(csv_rel)
        if not csv_path.is_absolute():
            csv_path = root / csv_path
        stem = csv_path.with_suffix("").name
        default_data = csv_path.with_name(f"{stem}.json")
        default_meta = csv_path.with_name(f"{stem}_meta.json")

        data_path = Path(data_path_arg) if data_path_arg else default_data
        meta_path = Path(meta_path_arg) if meta_path_arg else default_meta

        points = sv._load_json(data_path)  # type: ignore[attr-defined]
        meta = sv._load_json(meta_path)  # type: ignore[attr-defined]
        errors = sv.validate_points_against_meta(points, meta, layer=layer)
        if errors:
            # 详细错误仍输出到 stderr，保持与 schema_validator 模块一致
            sv._print_errors(errors)  # type: ignore[attr-defined]
            # 额外在 stdout 打一行醒目的红色 ❌ 提示
            print(
                f"\033[91m❌ Schema validation FAILED for layer={layer} "
                f"data={data_path} meta={meta_path}\033[0m"
            )
            return 1

        # 成功时在 stdout 打一行绿色 ✅ 提示
        print(
            f"\033[92m✅ Schema validation OK for layer={layer} "
            f"data={data_path} meta={meta_path} (version {sv.SCHEMA_VERSION_SUPPORTED})\033[0m"
        )
        return 0

    # 理论上不会到这里
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

