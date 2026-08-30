# AlleSchools

AlleSchools 将 DUO 开放教育数据与可选的 CBS PC4 WOZ 数据转换为荷兰学校对比数据集，并提供本地可视化和静态站点构建。

- VO：VWO 通过占比 × 理科通过占比。
- PO：VWO 等价建议占比 × 邮编区域平均 WOZ。

站点：[alleschools.nl](https://alleschools.nl)

## 环境

本项目使用 `uv` 和 Python 3.13。Node.js 用于前端测试和生成版本化静态资产。

```bash
uv venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-dev.txt
npm install
npm run build:css
```

## 数据流水线

`config.yaml` 是配置的单一来源。原始输入默认写入 `raw_data/`，生成物默认写入 `generated/`；两者都是运行时产物。

```bash
# 拉取并构建 VO + PO
uv run --python 3.13 --with-requirements requirements.txt \
  python -m alleschools.cli full --all

# 仅使用已有原始数据运行 ETL
uv run --python 3.13 --with-requirements requirements.txt \
  python -m alleschools.cli etl --all

# 分层运行
uv run --python 3.13 --with-requirements requirements.txt python -m alleschools.cli po
uv run --python 3.13 --with-requirements requirements.txt python -m alleschools.cli vo
```

`--data-root` 和 `--output-root` 可改写输入、输出根目录。完整参数以 CLI 帮助为准：

```bash
uv run --python 3.13 --with-requirements requirements.txt python -m alleschools.cli --help
```

## Schema 与 demo

[`docs/schema.md`](docs/schema.md) 是 points、meta、GeoJSON 和 long-table 导出契约的 canonical 文档。`demo/datasets_index.json` 是受版本控制的 demo 数据发现入口；demo 用于前端开发，不代表最新生产数据。

```bash
uv run --python 3.13 --with-requirements requirements.txt \
  python -m alleschools.cli validate --layer po \
  --data generated/schools_xy_coords_po.json \
  --meta generated/schools_xy_coords_po_meta.json
```

## 可视化

`view_xy_server.py` 读取流水线输出并注入 `view_xy.html`。

```bash
# http://127.0.0.1:8082/
uv run --python 3.13 --with-requirements requirements.txt python view_xy_server.py

# 输出 public/index.html
uv run --python 3.13 --with-requirements requirements.txt python view_xy_server.py --static
```

Vercel 构建入口定义在 `vercel.json`。部署构建会刷新数据，需要网络和对应数据源可用。
浏览器只加载 `assets/` 下的固定版本 CSS/JS，不依赖运行时 CDN。更新前端依赖后需提交 `package-lock.json`、重新生成 `assets/site.css`，并同步对应的 vendored JS。

## 测试

Pipeline 集成测试使用 `tests/fixtures/input/` 的最小脱敏数据，clean checkout 不需要 `raw_data/` 或 `generated/`。Schema 集成测试在 pytest 临时目录中现场生成导出物。

```bash
uv run --python 3.13 --with-requirements requirements-dev.txt pytest tests/ -v
node --test tests/view_xy_logic.test.js
```

## 仓库结构

| 路径 | 用途 |
|---|---|
| `alleschools/` | CLI、loader、计算、质量检查、exporter 和 validator |
| `config.yaml` | 默认配置和 profile |
| `demo/` | 受版本控制的前端 demo 数据 |
| `docs/schema.md` | canonical 数据契约 |
| `tests/fixtures/input/` | clean-checkout 测试 fixture |
| `view_xy.html` / `view_xy_logic.js` | 前端模板与逻辑 |
| `assets/` / `package-lock.json` | 本地化、锁版本的浏览器资产 |
| `view_xy_server.py` | 本地服务与静态构建 |

数据源：[DUO Open Onderwijsdata](https://duo.nl/open_onderwijsdata/) 和 [CBS PC4 地理数据](https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/gegevens-per-postcode)。
