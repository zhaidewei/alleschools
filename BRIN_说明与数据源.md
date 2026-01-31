# BRIN 说明与数据源

## 什么是 BRIN

**BRIN** 是荷兰教育系统里用来**唯一标识一所学校（或学校所在地点）**的编号。

- **全称**：**B**asis**R**egister **I**nstellingen（机构基础登记号），有时也理解为 **B**asis**R**egister **I**nstellingen en **N**amen。
- **组成**：由 **4 位 instellingscode（机构代码）** + **2 位 vestigingscode（地点代码）** 组成，共 **6 位**，例如 `02QZ00`。
  - 前 4 位：学校/机构；
  - 后 2 位：该机构下的具体地点（vestiging），`00` 通常表示主校区。
- **谁在用**：DUO（Dienst Uitvoering Onderwijs）、AlleCijfers、教育统计和开放数据里都用 BRIN 来指代「哪一所学校/哪个校区」。
- **在本项目中**：用 BRIN 在 DUO 的 CSV 里筛出 Amstelveen 四所学校：
  - Keizer Karel College → `02QZ00`
  - Hermann Wesselink College → `02TE00`
  - Amstelveen College → `19XY00`
  - Futuris → `00WD00`

---

## 哪里有全部的 BRIN 数据？

完整 BRIN / 学校列表可从 **DUO 官方开放数据** 获取，主要有两个入口：

### 1. 基础教育数据（所有教育类型，含 BRIN 全量）

**Basisgegevens instellingen**（机构基础数据）

| 项目 | 链接 |
|------|------|
| 说明页 | https://duo.nl/open_onderwijsdata/onderwijs-algemeen/basisgegevens/basisgegevens-instellingen.jsp |
| 下载（zip） | https://duo.nl/open_onderwijsdata/images/basisgegevens-instellingen.zip |

- **内容**：zip 内含 3 个文件  
  - **Organisaties**：所有教育相关机构（学校、vestiging、bestuur 等）的地址与标识，含 BRIN/vestigingsnummer  
  - Relaties：机构、bestuur、samenwerkingsverbanden 等之间的关系  
  - Overgangen：合并、重组等变更  
- **更新**：每周更新；是 BRIN 全量 + 机构/vestiging 列表的权威来源。

### 2. 仅「中等教育」全部 vestigingen（含 BRIN + 地址）

**Adressen alle vestigingen VO**（所有 VO 校址）

| 项目 | 链接 |
|------|------|
| 说明页 | https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/adressen/vestigingen.jsp |
| 下载（Excel） | https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.xlsx |
| 下载（CSV） | https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv |

- **内容**：全国所有 **voortgezet onderwijs（中学）vestigingen** 的 BRIN、vestigingsnummer、校名、地址、denominatie、bestuur、区域划分等。  
- **更新**：每月更新；只查「全部中学的 BRIN」时用这个最直接。

---

## 小结

- 要**所有教育类型的 BRIN 全量** → 用 **Basisgegevens instellingen** 的 zip 里的 Organisaties。
- 只要**中学（VO）的 BRIN + 地址** → 用 **Alle vestigingen VO** 的 CSV 或 Excel 即可。

**DUO 开放数据首页**：https://duo.nl/open_onderwijsdata/
