# 数据来源思路与逻辑

本文档记录如何从 AlleCijfers 的「Aantal leerlingen per gekozen profiel」需求，追溯到 DUO 开放数据并完成提取的完整思路。

---

## 1. 目标

- **需求**：获取 Amstelveen 四所中学「按所选 profiel 的学生/考生数」（Aantal leerlingen per gekozen profiel）。
- **参考页面**：AlleCijfers 各学校页，例如  
  https://allecijfers.nl/middelbare-school/keizer-karel-college/

---

## 2. 第一步：尝试从 AlleCijfers 直接抓取

- 用 HTTP 请求抓取学校页面的 HTML。
- **发现**：页面上该区块显示「de opleidingsgegevens worden geladen」（数据正在加载），**具体数字不在初始 HTML 里**，而是由前端 **JavaScript 异步加载** 后填入。
- **结论**：仅靠抓取静态 HTML 拿不到「per gekozen profiel」的表格数据，需要另找数据源。

---

## 3. 第二步：推断数据来自开放数据

- AlleCijfers 在页面上注明数据来自 **DUO（Dienst Uitvoering Onderwijs）** 等官方来源。
- 「按学校、按 opleiding/profiel、按学年」的考生/学生数，属于教育统计，通常由 **DUO 开放教育数据** 发布。
- **推断**：若能找到 DUO 中「按学校 + 按 opleiding/profiel」的开放数据集，即可绕过 AlleCijfers 的前端，直接得到「per gekozen profiel」的数字。

---

## 4. 第三步：在 DUO 官网定位数据集

- 搜索并打开 **DUO Open Onderwijsdata**：  
  https://duo.nl/open_onderwijsdata/
- 进入 **Voortgezet onderwijs → Examens**，找到「Examens vmbo, havo en vwo」说明页：  
  https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/examens/examens-vmbo-havo-vwo.jsp
- 该页列出的数据集中，**「Examenkandidaten en geslaagden」**（考试人数与通过人数）提供按学年、按 instelling、按 opleiding 的统计，并配有 **CSV/Excel** 下载。
- **选定**：用「Examenkandidaten en geslaagden」的 CSV 作为「per gekozen profiel」的数据源。

---

## 5. 第四步：验证 CSV 结构是否包含「profiel」和「per school」

- 用 `curl` 只下载 CSV 的**前几千字节**（避免下载整个大文件），查看表头与首几行。
- **表头关键列**：
  - `INSTELLINGSCODE`、`VESTIGINGSCODE` → 可组成 **BRIN**，对应学校；
  - **`OPLEIDINGSNAAM`** → 对应 HAVO - N&T、VWO - E&M、VMBO T - economie 等，即「gekozen profiel」；
  - 各学年列如 **「EXAMENKANDIDATEN SCHOOLJAAR 2019-2020 - TOTAAL」** 等 → 该 profiel 在该学年的考生数。
- **结论**：该 CSV 即「按学校（BRIN）、按 gekozen profiel（OPLEIDINGSNAAM）、按学年」的考生数数据源。

---

## 6. 第五步：用 BRIN 筛出目标学校并写入 JSON

- 学校在 DUO 中由 **BRIN** 标识（instellingscode + vestigingscode，如 02QZ00）。
- 从 `0_school_list` 与 AlleCijfers 页面已知四所学校的 BRIN：
  - Keizer Karel College: **02QZ00**
  - Hermann Wesselink College: **02TE00**
  - Amstelveen College: **19XY00**
  - Futuris: **00WD00**
- **操作**：
  1. 下载完整 CSV（或流式读取），用 `grep` 按上述 BRIN 筛选出四所学校的行；
  2. 解析每行：`OPLEIDINGSNAAM` = profiel，各学年「EXAMENKANDIDATEN ... TOTAAL」列 = 该 profiel 的考生数；
  3. 按学校、学年、profiel 汇总，写入各校的 `*_profielen.json` 中 `aantal_leerlingen_per_gekozen_profiel.profielen_per_examenjaar`。

---

## 7. 总结

| 步骤 | 做法 |
|------|------|
| 1 | 尝试从 AlleCijfers 抓取 → 发现数据由 JS 加载，静态 HTML 无数字 |
| 2 | 根据站点说明推断数据来自 DUO 开放数据 |
| 3 | 在 DUO 官网 Voortgezet onderwijs → Examens 下找到「Examenkandidaten en geslaagden」CSV |
| 4 | 用 CSV 表头确认存在「学校 + opleiding/profiel + 按学年考生数」 |
| 5 | 用四校 BRIN 过滤 CSV，解析并写入 `*_profielen.json` |

**数据源**：  
DUO Open Onderwijsdata → [Examens vmbo, havo en vwo](https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/examens/examens-vmbo-havo-vwo.jsp) → **Examenkandidaten en geslaagden**（CSV 2019-2024）。

**相关文件**：  
- `fetch_profielen.py`：从 DUO CSV 解析并更新各校 JSON；  
- `duo_examen_raw.csv`：仅含四校的 DUO 原始行（可选，供复现）；  
- `*_profielen.json`：每校的「Aantal leerlingen per gekozen profiel」结果。
