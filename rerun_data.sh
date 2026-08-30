#!/usr/bin/env bash
set -euo pipefail

# 统一从脚本所在目录作为项目根开始执行
cd "$(dirname "$0")"

# 1. 一键从 fetch → ETL（VO + PO）-----------------------------------
echo "== 统一入口：fetch + ETL (VO + PO) =="
# full 子命令的 --all / --vo / --po 互斥，这里用 --all 覆盖 VO+PO。
python -m alleschools.cli full --all

# 2. 发布门禁：独立校验最终 points + meta，失败立即终止构建
echo "== 发布门禁：校验 VO points + meta（generated/ 下） =="
python -m alleschools.cli validate \
  --layer vo \
  --data generated/schools_xy_coords.json \
  --meta generated/schools_xy_coords_meta.json

echo "== 发布门禁：校验 PO points + meta（generated/ 下） =="
python -m alleschools.cli validate \
  --layer po \
  --data generated/schools_xy_coords_po.json \
  --meta generated/schools_xy_coords_po_meta.json

echo "全部完成：generated/ 下的 CSV/JSON + run_report 已更新，可继续生成静态站点。"
