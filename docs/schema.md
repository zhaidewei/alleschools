# AlleSchools 导出契约

本文档是前端、BI 消费者与数据流水线的 canonical schema 说明。当文档与实现冲突时，以 `alleschools/schema_validator.py` 和 exporter 在当前 schema 版本下的可执行约束为准，并同步修正本文档。

## 版本

当前支持版本：`1.0.0`。Meta 的 `version` 必须与它相等，`layer` 必须是 `po` 或 `vo`。破坏性字段、类型或语义变更需要新 schema 版本。

## Points JSON

顶层是 JSON array。每个 point 必须包含：

| 字段 | 类型 | 语义 |
|---|---|---|
| `id` | string | 稳定 point ID，当前为 BRIN |
| `layer` | string | `po` 或 `vo` |
| `brin` | string | 学校/校区标识 |
| `name` | string | 学校名称 |
| `municipality` | string | 市镇 |
| `postcode` / `pc4` | string | 邮编及前四位 |
| `school_type` | string | 学校类型 |
| `x_linear` / `y_linear` | number | 水平/垂直轴指标 |
| `size` | number | 视觉大小指标 |
| `years_covered` | string[] | 包含的学年 |
| `flags` | object | 质量、覆盖和隐私标志 |

PO 中 `x_linear` 是 VWO 等价建议占比，`y_linear` 是 PC4 WOZ，`size` 是学生数。VO 中三者分别是 VWO 通过占比、理科通过占比和考生数。

## Meta JSON

Meta 必须包含 `version`、`layer`、`axes`、`fields` 和 `i18n`。`axes` 必须定义 `x`、`y` 和 `size`；轴的 `field` 必须指向 points 字段。消费者应从 meta 读取轴、字段和 i18n 信息。

## GeoJSON

顶层必须是 `FeatureCollection`。每个 feature 的 `properties` 至少包含 `BRIN`、`X_linear` 和 `Y_linear`。`geometry` 可为 `null`；存在时必须是数值 `[longitude, latitude]` 坐标的 `Point`。

## Long-table CSV

每行至少包含 `BRIN`、`year`、`X_linear` 和 `Y_linear`。PO 额外要求 `pupils_total`，VO 额外要求 `candidates_total`。非空数值列必须可解析为 number。

## Demo 发现

`demo/datasets_index.json` 是 demo 数据集索引。它为每层指向 points 和 meta。Demo 用于稳定前端开发和演示，不是生产最新数据证据。
