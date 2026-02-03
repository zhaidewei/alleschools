# AlleSchools（alleschools.nl）— 荷兰学校比较

本仓库从 **DUO Open Onderwijsdata** 抓取全部中学的考试人数数据，计算每所学校的「VWO 通过人数占比 × 理科占比」坐标，并提供本地可视化服务。站点品牌：**AlleSchools**（[alleschools.nl](https://alleschools.nl)）。

---

## 1. 数据流水线概览

| 步骤 | 输入 | 脚本/操作 | 输出 |
|------|------|-----------|------|
| 抓取 | DUO CSV URL | `python3 fetch_duo_examen_all.py` | `duo_examen_raw_all.csv` |
| 计算 | `duo_examen_raw_all.csv` | `python3 calc_xy_coords.py` | `schools_xy_coords.csv`、`excluded_schools.json` |
| 服务 | `schools_xy_coords.csv` + `view_xy.html` | `python3 view_xy_server.py` | 浏览器打开 http://localhost:8082 |

---

## 2. 第一步：从 DUO 抓取全部中学数据

- **数据源**：DUO Open Onderwijsdata → [Examens vmbo, havo en vwo](https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/examens/examens-vmbo-havo-vwo.jsp) → **Examenkandidaten en geslaagden**（CSV 2019–2024）。
- **抓取脚本**：`fetch_duo_examen_all.py` 下载完整 CSV，保存为 `duo_examen_raw_all.csv`。

```bash
python3 fetch_duo_examen_all.py
```

- **保留**：`duo_examen_raw_all.csv` 为全量中学考试人数原始数据，供下一步计算使用。

---

## 3. 第二步：从 duo_examen_raw_all 到 schools_xy_coords

- **脚本**：`calc_xy_coords.py`
- **输入**：`duo_examen_raw_all.csv`（若不存在则退化为 `duo_examen_raw.csv`）
- **输出**：
  - `schools_xy_coords.csv`：每所学校的 BRIN、校名、gemeente、**postcode（邮编）**、类型（HAVO/VWO 或 VMBO）、X_linear、Y_linear、X_log、Y_log
  - `excluded_schools.json`：因 HAVO/VWO 考生数过少（低于阈值）而排除的学校列表

**中学邮编来源**：考试数据 `duo_examen_raw_all.csv` 本身不含邮编。`calc_xy_coords.py` 会读取 DUO 的 **Alle vestigingen VO**（[CSV](https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv)），按 **VESTIGINGSCODE** 与考试数据中的校址代码匹配，将 **POSTCODE** 写入 `schools_xy_coords.csv`。若未放置 `duo_vestigingen_vo.csv`，可先运行 `download_duo_vestigingen_vo.py` 下载。

**坐标含义**：

- **X（横轴）**：VWO 通过人数占比（0–100%）= VWO 通过人数 / 全校考生总数（HAVO+VWO+VMBO 等所有类型）。
- **Y（纵轴）**：理科通过人数 / 全校考生总数（0–100%）。HAVO/VWO 学校为 N&T、N&G、N&T/N&G 通过人数占全校考生比；VMBO 学校为 techniek 占比，且 X=0。
- **权重**：近年权重大，逐年递减（2019–2020 到 2023–2024）。
- **最小样本**：HAVO/VWO 总考生数（5 年合计）低于 20 的学校不写入 CSV，避免极端点（见下文「数据异常说明」）。

```bash
python3 calc_xy_coords.py
```

---

## 4. Serving：本地可视化服务

- **服务脚本**：`view_xy_server.py` 读取 `schools_xy_coords.csv` 和 `excluded_schools.json`，生成带散点图的 HTML，并启动 HTTP 服务（默认端口 8082）。
- **前端**：`view_xy.html` 展示横轴 VWO 通过人数占比、纵轴理科占比；可切换中学/小学模式、线性/对数坐标；按 gemeente（市政厅）筛选、勾选城市；悬停圆点显示校名与邮编。
  - **学校搜索**：支持多词搜索，用逗号分隔（如 `mae,zand,nov,maar`）。每个词**部分匹配**校名、BRIN、城市或邮编即可，匹配的圆点会高亮、未匹配的会变灰；**仅当搜索框有内容时**，匹配到的学校名称会显示在对应圆点上方（带底色与匹配词高亮）。图例中的城市颜色始终显示本色，不受搜索高亮影响，便于对照圆点所属城市。
  - **URL 参数与分享**：打开页面时可通过 URL 传入 `q`（学校搜索）和 `gemeente`（市政厅过滤），例如 `?q=mae,zand&gemeente=gra,zoe,voor`，会预填搜索框、市政厅过滤框并勾选匹配的城市。分享到 X / Facebook 时，分享链接会带上当前的 `q` 与 `gemeente`，他人打开即可复现相同筛选状态。
- **排除名单**：`excluded_schools.json` 中学校在页面底部列出，不参与散点图。

```bash
python3 view_xy_server.py
# 浏览器打开 http://localhost:8082
```

**仅生成静态 HTML（不启动服务，用于 Vercel 等静态托管）：**

```bash
python3 view_xy_server.py --static
# 输出到 public/index.html
```

---

## 4.1 部署到 Vercel（静态托管）

本项目已配置为用 **Vercel 静态托管** 部署：

1. 将仓库推送到 GitHub/GitLab/Bitbucket，或在 Vercel 导入该仓库。
2. Vercel 会读取根目录的 `vercel.json`：
   - **Build Command**：`python3 view_xy_server.py --static`（生成 `public/index.html`）
   - **Output Directory**：`public`
3. 部署前请确保仓库内已有 `schools_xy_coords.csv` 和 `excluded_schools.json`（先本地运行 `calc_xy_coords.py` 并提交，或使用 CI 生成）。

**本地预览静态构建：**

```bash
python3 view_xy_server.py --static
# 用任意静态服务器打开 public/，例如：
# python3 -m http.server 8082 --directory public
```

---

## 5. 数据源与 BRIN 说明

### 什么是 BRIN

- **BRIN**：荷兰教育系统内唯一标识一所学校（或校区）的编号。**B**asis**R**egister **I**nstellingen（机构基础登记号）。
- **组成**：4 位 instellingscode + 2 位 vestigingscode，共 6 位（如 `02QZ00`）。DUO、AlleCijfers 等均用 BRIN 指代学校/校区。

### 哪里获取全部 BRIN / 中学列表

- **Basisgegevens instellingen**（机构基础数据）：[说明页](https://duo.nl/open_onderwijsdata/onderwijs-algemeen/basisgegevens/basisgegevens-instellingen.jsp)，zip 内含 Organisaties 等，为 BRIN 全量来源。
- **Alle vestigingen VO**（所有中学 vestigingen）：[说明页](https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/adressen/vestigingen.jsp)，[CSV](https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv)，含全国中学 BRIN、校名、地址、GEMEENTENAAM 等。

**DUO 开放数据首页**：https://duo.nl/open_onderwijsdata/

---

## 6. 数据来源思路（从需求到 DUO CSV）

- **需求**：按学校、按 opleiding/profiel、按学年的考生数（examenkandidaten）。
- **尝试**：从 AlleCijfers 抓取学校页 HTML → 发现「per gekozen profiel」数据由前端 JavaScript 加载，静态 HTML 无数字。
- **结论**：改用 DUO 开放数据。在 DUO → Voortgezet onderwijs → Examens 下找到「Examenkandidaten en geslaagden」CSV，表头含 INSTELLINGSCODE、VESTIGINGSCODE（BRIN）、OPLEIDINGSNAAM（profiel）、各学年 EXAMENKANDIDATEN TOTAAL 等，满足「学校 + profiel + 学年考生数」需求。
- **本仓库**：用该 CSV 全量下载为 `duo_examen_raw_all.csv`，再由 `calc_xy_coords.py` 按 BRIN 聚合 HAVO/VWO 与 VMBO，计算 X/Y 坐标。

---

## 7. 精英指数与坐标系建议

### 精英指数（可选的三种方式）

| 维度 | 含义 | 可用数据 |
|------|------|----------|
| 学历层次 | 偏 VWO 还是 HAVO | VWO 占比 = VWO/(HAVO+VWO) |
| 学科取向 | 偏理科（N&T、N&G） | 理科占比，现有 CSV 可算 |
| 毕业质量 | 通过率 | DUO 同一 CSV 有 GESLAAGDEN，可算 |

- **方案 1**：精英指数 = VWO 占比 或 理科占比（单一维度）。
- **方案 2（推荐）**：精英指数 = 0.6×VWO占比 + 0.4×理科占比。
- **方案 3**：加入通过率，如 0.4×VWO + 0.3×理科 + 0.3×通过率（归一化）。

本仓库的 **X = VWO 通过人数占比、Y = 理科通过人数占比** 即采用「学历层次 × 学科取向」二维（用通过人数替代考生数，便于区分纯 VWO 校），与方案 2 一致。

### 坐标系说明（当前实现）

- **X 轴**：VWO 通过人数占比（0–100%）= VWO 通过人数 / 全校考生总数（所有类型）。
- **Y 轴**：理科通过人数 / 全校考生总数（0–100%）。理科 = N&T + N&G + N&T/N&G（HAVO/VWO）；VMBO 为 techniek 占比。
- 只算 HAVO/VWO 参与 X/Y；VMBO 学校 X=0，Y 为 VMBO 内 techniek 占比。
- **组合 profiel**：N&T/N&G、E&M/C&M 等按 DUO OPLEIDINGSNAAM 归类；`<5` 按 2 计。

---

## 8. 按 gemeente 查中学

- **网页**：`https://allecijfers.nl/middelbare-scholen-overzicht/{gemeente-slug}/`（如 amstelveen、amsterdam）。
- **批量/程序**：下载 DUO「Alle vestigingen VO」CSV，按列 **GEMEENTENAAM** 筛选。示例（表头第 11 列为 GEMEENTENAAM）：

```bash
curl -sL "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv" -o vestigingen_vo.csv
awk -F';' 'NR==1 {print; next} toupper($11)==toupper("Amstelveen") {print}' vestigingen_vo.csv > amstelveen_vo.csv
```

---

## 9. 数据异常与检查说明

### IJburg College (100, 100)

- **现象**：`schools_xy_coords.csv` 中 28DH01 IJburg College 曾出现 X_linear=100, Y_linear=100。
- **原因**：在 `duo_examen_raw_all.csv` 中该校仅有一行「VWO - N&G」，且各年考生数多为 `<5`。计算得 VWO 占比=100%、理科占比=100%，并非算错，而是样本极少。
- **处理**：在 `calc_xy_coords.py` 中设置 `MIN_HAVO_VWO_TOTAL = 20`，HAVO/VWO 总考生数（5 年合计）低于 20 的学校不写入 CSV，改为写入 `excluded_schools.json`。

### X=100 的 HAVO/VWO 学校

- **结论**：不是数据处理错误。X_linear=100 表示该校在 DUO 数据中**只有 VWO 通过、没有 HAVO 通过**（如 St. Ignatiusgymnasium、Het Amsterdams Lyceum、Stedelijk Gymnasium Haarlem 等），VWO 通过人数占比=100% 与原始数据一致。

### X=0、Y=100% 的点（多为 VMBO）

- **现象**：散点图中有不少点落在 X=0、Y=100%（或接近 100%）位置。
- **结论**：**不是数据错误**。这些点几乎都是 **VMBO 学校**：
  - **X=0**：VMBO 学校横轴固定为 0（不参与 VWO 占比计算）。
  - **Y=100%**：Y = VMBO 内 techniek 占比；100% 表示该校**只开 techniek（技术/职业）方向**，没有「zorg en welzijn」「economie」等。
- **典型学校**：Maritieme Academie Harlingen（海事）、Mediacollege Amsterdam（传媒）、Grafisch Lyceum Rotterdam（平面）、STC（航运）、SiNTLUCAS（设计）等，均为单一技术/职业类 VMBO 校区，原始数据中仅有 VMBO B/K/G/T - techniek 行，故 techniek/总考生 = 100%。

---

## 10. 文件一览（清理后保留）

| 文件 | 说明 |
|------|------|
| `fetch_duo_examen_all.py` | 从 DUO 下载全量考试人数 CSV → `duo_examen_raw_all.csv` |
| `duo_examen_raw_all.csv` | DUO 原始数据（全量中学） |
| `calc_xy_coords.py` | 从 duo_examen_raw_all 计算 X/Y → `schools_xy_coords.csv` |
| `schools_xy_coords.csv` | 学校坐标（BRIN、校名、gemeente、postcode、type、X_linear、Y_linear、X_log、Y_log） |
| `excluded_schools.json` | 样本过少被排除的学校列表（由 calc_xy_coords 生成） |
| `view_xy_server.py` | 本地 HTTP 服务 / 静态构建（`--static` → `public/index.html`） |
| `view_xy.html` | 散点图前端模板（本地开发时生成） |
| `vercel.json` | Vercel 静态托管配置（buildCommand + outputDirectory） |
| `README.md` | 本文档（合并原有多份 Markdown） |
