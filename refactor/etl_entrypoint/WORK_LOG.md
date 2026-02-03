## 统一 ETL 入口开发工作笔记

- 2026-02-10  第 1 批次修改
  - **内容**：
    - 新增 `alleschools/etl.py`，封装 fetch（VO 考试、VO vestigingen、PO schooladviezen、CBS WOZ）与 etl 调用逻辑，统一基于 `data_root` 读写。
    - 扩展 `alleschools/cli.py`，增加 `fetch` / `etl` / `full` 三个子命令，并保留原有 `po` / `vo` 行为不变。
    - `full` 子命令顺序为：`fetch`（自动附带 CBS WOZ）→ `etl`，schema 校验仍通过现有 `schema_validation` 配置控制。
  - **测试**：
    - 已运行：`bash run_tests.sh`
    - 结果：Python 测试 1 个用例失败，其余通过。失败用例为 `test_build_effective_config_uses_defaults_and_profile`，与 `build_effective_config` 默认 profile 选择逻辑有关，是与本次 CLI/ETL 变更无关的旧配置行为（现实现为优先使用函数参数指定 profile，其次 YAML 中 profile 字段，默认 "default"），暂不在本批次修改中调整。

- 2026-02-10  第 2 批次修改
  - **内容**：
    - 调整 `alleschools.pipeline.run_po_pipeline` / `run_vo_pipeline` 中输出路径的拼接方式，统一基于 `po.output.csv` / `vo.output.csv` 的相对路径所在目录：
      - 默认情况下，`csv` 与 `excluded_json`、GeoJSON（`*_geo.json`）、长表（`*_long.csv`）、points JSON（`*.json`）、meta JSON（`*_meta.json`）全部写入 `generated/` 目录下。
      - `run_report_*.json.outputs.*` 中对应的 `csv_path` / `excluded_path` / `geojson_path` / `long_table_path` / `points_path` / `meta_path` 字段，统一使用带有 `generated/` 前缀的相对路径。
    - 保持现有文件名（如 `schools_xy_coords_po_geo.json`、`schools_xy_coords_po_long.csv`）不变，仅改变默认目录。
  - **测试**：
    - 已再次运行：`bash run_tests.sh`。
    - 结果：除已知的 `test_build_effective_config_uses_defaults_and_profile` 仍失败外，其余测试均通过；与路径调整直接相关的测试（包括 GeoJSON、长表与 points JSON 生成，以及 run_report_* 验证）全部通过，说明默认输出目录改为 `generated/` 后行为与测试预期兼容。

---

### 2026-02-10  第 3 批次修改（待办 1、2 完成）

- **验收 4 - 错误处理与退出码**：
  - `run_vo_pipeline` / `run_po_pipeline` 在返回的 `stats` 中增加 `summary_status`（取自 `run_report["summary"]["status"]`）；VO 输入缺失时的 early return 也写入 `stats["summary_status"] = "error"`。
  - `run_etl_vo` / `run_etl_po` 改为返回 `stats`；`run_etl_from_cli_args` 返回 `bool`（是否有任一 layer 的 `summary_status == "error"`）。
  - CLI 的 `etl` 与 `full`：根据 `run_etl_from_cli_args` 的返回值，若有错误则 `return 1`，否则 `return 0`。
- **PO 输入缺失时的 status=error**：
  - 在 `run_po_pipeline` 中，若 `load_schooladviezen_po` 返回空（无任何 PO 数据），则写出 `run_report_po.json`（`summary.status = "error"`，`errors = ["No PO schooladviezen data found"]`）并提前返回，行为与 VO 一致。
- **测试**：`test_run_po_pipeline_standalone_quality_report` 改为使用 `pipeline_data_root`（有 PO 输入时 pipeline 才会跑到底并写出 standalone report），无 PO 数据时 skip。

---

### 其它（已关闭的待办）

1. ~~**验收 4 - 错误处理与退出码**~~ → 第 3 批次已完成。
2. ~~**PO 输入缺失时的 status=error**~~ → 第 3 批次已完成。

3. **其它**
   - 其余验收项（CLI 行为、路径正确性、兼容性、schema 校验合并进 run_report）已实现或由现有 pipeline/配置覆盖。
   - `rerun_data.sh` 已改为使用 `python -m alleschools.cli full --all`，README 中「未来可简化」已落地。


