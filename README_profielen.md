# 按所选 profiel 的学生数（Amstelveen 中学）

每所学校对应一个 JSON 文件，存放 **「Aantal leerlingen per gekozen profiel」**（按所选 opleidingsprofiel 的学生/考生数）的数据结构，与 [AlleCijfers.nl](https://allecijfers.nl/middelbare-scholen-overzicht/amstelveen/) 上各校页面展示的内容一致（例如 [Keizer Karel College](https://allecijfers.nl/middelbare-school/keizer-karel-college/)）。

## 文件一览

| 学校 | JSON 文件 |
|------|------------|
| Keizer Karel College | `keizer-karel-college_profielen.json` |
| Hermann Wesselink College | `hermann-wesselink-college_profielen.json` |
| Amstelveen College | `amstelveen-college_profielen.json` |
| Futuris | `futuris_profielen.json` |

## 数据从哪来？

本目录中的数字来自 **DUO Open Onderwijsdata**（见 `DATA_SOURCE_LOGIC.md`）。AlleCijfers 上的「按所选 profiel 的学生数」是页面用 JavaScript 动态加载的，静态 HTML 里没有，无法直接抓取，因此改用 DUO 的「Examenkandidaten en geslaagden」CSV 按学校 BRIN 筛选后解析填入。

## 如何更新数据？

1. **手动**：打开该校在 AlleCijfers 的页面，从柱状图/图例中抄写数字。
2. **用 DUO 开放数据**：下载「Examenkandidaten en geslaagden」或「Examenkandidaten havo/vwo/vmbo en examencijfers per instelling」，按 BRIN 筛选：
   - [DUO – Examens vmbo, havo en vwo](https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/examens/examens-vmbo-havo-vwo.jsp)

各校的 BRIN 写在对应 JSON 的 `school.brin` 里。

也可用本目录的脚本一键更新（先下载 DUO CSV 并筛选出四校行，再运行）：

```bash
curl -sL "https://duo.nl/open_onderwijsdata/images/examenkandidaten-en-geslaagden-2019-2024.csv" | grep -E '"02QZ"|"02TE"|"19XY"|"00WD"' > duo_examen_raw.csv
python3 fetch_profielen.py
```

## JSON 中 `profielen_per_examenjaar` 的结构

HAVO/VWO 学校（Keizer Karel、HWC、Amstelveen College）的 profiel 包括：

- Natuur & Techniek（自然与技术）
- Natuur & Gezondheid（自然与健康）
- Economie & Maatschappij（经济与社会）
- Cultuur & Maatschappij（文化与社会）

示例（数字仅为示意）：

```json
"profielen_per_examenjaar": {
  "2023-2024": {
    "HAVO - N&T": 5,
    "HAVO - N&G": 11,
    "HAVO - E&M": 48,
    "VWO - N&T": 27,
    "VWO - E&M": 46
  }
}
```

VMBO/MAVO 学校（Futuris）使用 DUO 中的 sectoren/opleidingsrichtingen（如 VMBO B/K/T - techniek, zorg en welzijn, economie）。

数值若为 `"<5"` 表示 DUO 因隐私统计规则未公布具体人数（小于 5 人）。
