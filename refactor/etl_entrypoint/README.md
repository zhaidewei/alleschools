## 统一 ETL 入口（CLI）功能说明

本功能只做需求与约束描述，具体实现由后续开发 Agent 完成。

---

### 1. 背景与目标

当前数据链路有多支独立脚本：

- 原始数据抓取：
  - `fetch_duo_examen_all.py`（VO 考试）
  - `download_duo_vestigingen_vo.py`（VO 校区列表 + postcode，用于 BRIN → postcode 映射）
  - `fetch_duo_schooladviezen.py`（PO 升学建议）
  - `fetch_cbs_woz_postcode.py`（CBS WOZ per PC4）
- 聚合与导出：
  - `python -m alleschools.cli vo`
  - `python -m alleschools.cli po`

问题：

- 使用者需要记多个脚本名和顺序，易错；
- 在 CI / Vercel 上希望有**单一入口**可以完成「从原始数据抓取 → 聚合 → 校验 → 前端数据就绪」。

**本功能目标**：在 `alleschools/` 下提供一个统一的 ETL 入口（通过 `python -m alleschools.cli ...`），在保持现有 CLI 兼容的前提下：

- 可一键触发 **fetch + pipeline**；
- 可只跑 fetch 或只跑 pipeline；
- 对 Vercel / 本地 / CI 行为有清晰、可配置的约束。

---

### 2. 功能范围（Scope）

#### 2.1 影响模块

- `alleschools/cli.py`：扩展/重构为真正的多子命令 CLI。
- （可选）新建 `alleschools/etl.py`：封装「fetch + pipeline」高阶逻辑。
- 将当前散落在仓库根目录下的原始数据下载脚本**收口到 CLI 内部调用**，例如：
  - `fetch_duo_examen_all.py`
  - `download_duo_vestigingen_vo.py`
  - `fetch_duo_schooladviezen.py`
  - `fetch_cbs_woz_postcode.py`
- 要求：日常使用场景下，用户**不再需要直接记住或调用这些单文件脚本**，而是统一通过 `python -m alleschools.cli fetch|full ...` 触发；脚本本身可以保留为薄封装或迁移到 `alleschools.*` 内部模块。

#### 2.2 新增 CLI 子命令（建议）

以 `python -m alleschools.cli <subcommand> [options]` 形式暴露：

1. `fetch`
   - 用途：**只拉取 / 更新原始数据**，不做任何聚合计算。
   - 选项示例：
     - `--vo`：拉取 VO 考试数据（调用 `fetch_duo_examen_all.py`）。
     - `--po`：拉取 PO schooladviezen（调用 `fetch_duo_schooladviezen.py`）。
     - `--cbs-woz`：拉取 CBS WOZ per PC4（调用 `fetch_cbs_woz_postcode.py`）。
     - `--all`：相当于 `--vo --po --cbs-woz`。
   - 默认 data_root：从 `config.yaml` 读取（沿用现有配置体系）。

2. `etl`
   - 用途：**只基于已有原始 CSV 跑聚合流水线**（不主动下载/更新外部数据）。
   - 选项示例：
     - `--vo`：调用 `run_vo_pipeline`。
     - `--po`：调用 `run_po_pipeline`。
     - `--all`：同时跑 VO + PO。
   - 行为：
     - 复用现有 `config.build_effective_config`；
     - 正常写出 `schools_xy_coords*.csv`、points JSON、meta JSON、GeoJSON、长表及 `run_report_*.json`。

3. `full`
   - 用途：一键从「原始拉取 → 聚合 → 校验」。
   - 典型用法：
     - `python -m alleschools.cli full --vo --po`。
   - 推荐执行顺序（伪代码）：
     1. 调 `fetch`（受 `--vo/--po/--cbs-woz/--all` 控制）：
        - `--vo` 时应同时下载 VO 考试数据 **和** `duo_vestigingen_vo.csv`（调用 `download_duo_vestigingen_vo.py`），保证 BRIN→postcode 映射可用。
     2. 调 `etl`（VO/PO）。
     3. （可选）调用 schema validator：
        - VO：`schema_validator` 校验 `schools_xy_coords.json` + `schools_xy_coords_meta.json`。
        - PO：同理。
     4. 将 schema 校验结果合并进 `run_report_*.json.summary.errors`（沿用已有逻辑）。

> 说明：现有 `python -m alleschools.cli vo|po` 的行为可以视作 `etl --vo/--po` 的语法糖，需保持向后兼容。

---

### 3. 配置与路径约定

1. **data_root 统一来源**：  
   - 继续使用 `config.yaml` 中的 `data_root`，CLI 不硬编码绝对路径。
   - `fetch_*` 脚本被调用时，目标输出路径一律基于 `data_root`。

2. **ETL 输出默认目录：`generated/`**  
   - 所有**中间 / 纯计算产物**（CSV、points JSON、meta JSON、GeoJSON、long table 等）默认写入：
     - `generated/schools_xy_coords.csv`
     - `generated/schools_xy_coords_po.csv`
     - `generated/schools_xy_coords.json` / `generated/schools_xy_coords_po.json`
     - `generated/schools_xy_coords_meta.json` / `generated/schools_xy_coords_po_meta.json`
     - `generated/schools_xy_coords_geo.json` / `generated/schools_xy_coords_po_geo.json`
     - `generated/schools_xy_coords_long.csv` / `generated/schools_xy_coords_po_long.csv`
   - 这些路径应通过 `config.yaml` 的 `vo.output.*` / `po.output.*` 配置，默认带有 `generated/` 前缀；
   - `.gitignore` 中已忽略 `generated/`，因此：
     - 这些 ETL 产物不会进入 Git；
     - 但在本地/CI/Vercel build 时，通过 CLI/ETL 入口总是会被重新生成。

3. **运行报告中的路径**：
   - 已有约定：`run_report_po.json` / `run_report_vo.json` 的 `outputs.*.csv_path` 等字段使用**相对于 `data_root` 的相对路径**（例如 `"generated/schools_xy_coords_po.csv"`），而不是绝对路径。
   - 新增 CLI 逻辑不得引入新的绝对路径字段。

4. **与 Vercel 的关系**：
   - Vercel 的 `buildCommand` 当前为：  
     `bash rerun_data.sh && python3 view_xy_server.py --static`
   - 未来可以将 `rerun_data.sh` 简化为在 `generated/` 下重跑 ETL 的 CLI 调用，例如：
     - `python -m alleschools.cli full --vo --po`
     - 再调用 `view_xy_server.py --static` 读取 `generated/` 中的 ETL 结果并写出最终静态 HTML。

---

### 4. 非目标（Out of Scope）

- 不改动各 fetch 脚本的内部下载/解析逻辑。
- 不在本功能中改写前端或 `view_xy_server.py` 注入逻辑。
- 不在本功能中引入调度系统（如 cron/CI 配置），只提供 CLI 能力。

---

### 5. 验收标准（供开发 Agent 参考）

1. **CLI 行为**
   - `python -m alleschools.cli fetch --all` 在 data_root 下写出：
     - VO：`duo_examen_raw_all.csv`；
     - PO：`duo_schooladviezen_YYYY_YYYY.csv` 若干；
     - CBS：`cbs_woz_per_postcode_year.csv`。
   - `python -m alleschools.cli etl --all` 在 data_root 下写出：
     - `schools_xy_coords.csv`、`schools_xy_coords_po.csv`；
     - 对应的 points JSON、meta JSON、GeoJSON、长表；
     - `run_report_vo.json` / `run_report_po.json`。

2. **路径正确性**
   - `run_report_*.json.outputs.*.csv_path` / `...excluded_path` / `...geojson_path` / `...points_path` / `...meta_path` 仍为相对路径，且与实际生成文件一致。

3. **兼容性**
   - 现有命令 `python -m alleschools.cli vo` / `python -m alleschools.cli po` 仍然可用，行为等价于调用新的 `etl` 对应子命令。

4. **错误处理**
   - 当必要的原始 CSV 缺失时：
     - `etl` 子命令应在 `run_report_*` 中写入 `summary.status = "error"` 与错误信息。
     - 退出码非 0，便于 CI 捕获失败。

