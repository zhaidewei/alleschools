# 怎样从一个 gemeente 名字得到该市镇的所有中学？

两种做法：用 **AlleCijfers 网页** 或 **DUO 开放数据 CSV**。

---

## 方法一：AlleCijfers 网页（适合人工查看）

按 gemeente 的**中学列表页**地址格式为：

```
https://allecijfers.nl/middelbare-scholen-overzicht/{gemeente-slug}/
```

- **gemeente-slug**：一般为 gemeente 名称**小写**，空格换成**连字符 `-`**。  
  例：Amstelveen → `amstelveen`，'s-Gravenhage → `s-gravenhage`。

**示例**：  
- Amstelveen：https://allecijfers.nl/middelbare-scholen-overzicht/amstelveen/  
- Amsterdam：https://allecijfers.nl/middelbare-scholen-overzicht/amsterdam/  
- Utrecht：https://allecijfers.nl/middelbare-scholen-overzicht/utrecht/

页面上会列出「本 gemeente 内的中学」以及「本 gemeente 学生去读的其他中学」（至少 5 人）。

---

## 方法二：DUO CSV（适合批量 / 程序）

DUO 的 **Alle vestigingen VO** 里包含全国所有中学 vestigingen，其中有 **GEMEENTENAAM**（市镇名）。  
用 gemeente 名字筛选该列即可得到「该 gemeente 内的所有中学」。

### 1. 下载 CSV

| 项目 | 链接 |
|------|------|
| 说明页 | https://duo.nl/open_onderwijsdata/voortgezet-onderwijs/adressen/vestigingen.jsp |
| CSV 下载 | https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv |

### 2. 表头中的关键列（分号分隔）

- **GEMEENTENAAM**：市镇名（DUO 里多为大写，如 AMSTELVEEN、ASSEN）
- **INSTELLINGSCODE** + **VESTIGINGSCODE**：组成 BRIN（如 02QZ + 00 → 02QZ00）
- **VESTIGINGSNAAM**：校名
- **STRAATNAAM**、**HUISNUMMER-TOEVOEGING**、**POSTCODE**、**PLAATSNAAM**：地址
- **DENOMINATIE**： denominatie（如 Openbaar、Bijzonder）
- **ONDERWIJSSTRUCTUUR**：类型（如 HAVO/VWO、VBO/MAVO、PRO）

### 3. 按 gemeente 筛选（命令行示例）

gemeente 名在 CSV 里通常是大写，筛选时建议**统一转成大写**再比较。

```bash
# 下载 CSV，按 GEMEENTENAAM 筛选（例：Amstelveen）
curl -sL "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv" | \
  awk -F';' 'NR==1 {print; next} $11=="AMSTELVEEN" {print}' 
```

说明：表头第 11 列（从 1 数）是 **GEMEENTENAAM**；把 `AMSTELVEEN` 换成你要的市镇名（大写）即可。

若要保存为文件：

```bash
curl -sL "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv" -o vestigingen_vo.csv
awk -F';' 'NR==1 {print; next} toupper($11)==toupper("Amstelveen") {print}' vestigingen_vo.csv > amstelveen_vo.csv
```

这样 **amstelveen_vo.csv** 里就是该 gemeente 的所有中学 vestigingen（含 BRIN、校名、地址等）。

---

## 小结

| 需求 | 做法 |
|------|------|
| 人工看某 gemeente 的中学 | 打开 `https://allecijfers.nl/middelbare-scholen-overzicht/{gemeente-slug}/` |
| 批量 / 程序：从 gemeente 名得到中学列表 | 下载 DUO「Alle vestigingen VO」CSV，按列 **GEMEENTENAAM** 筛选 |

**注意**：DUO 里「vestiging」= 一个校区/地址；一所学校可以有多个 vestigingen，同一 gemeente 内可能有多行（多个 BRIN 或同一 BRIN 不同 vestigingscode）。
