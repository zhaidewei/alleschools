# AlleSchools 网站 V2 设计与验收规范

状态：状态模型开发基线  
版本：1.1  
日期：2026-08-30

## 1. 目标

AlleSchools V2 是面向家长和学生的学校探索工具。页面首先帮助用户找到候选学校、理解它们在数据中的相对位置，再提供方法论和原始指标。

本次重设计保留现有数据流水线、points/meta 契约和指标计算，不重新定义学校质量，不生成综合排名。

成功标准：新用户能在一分钟内完成“选择学段 → 搜索地区或学校 → 理解图表 → 查看或分享候选学校”。

## 2. 设计原则

1. 任务优先：搜索和探索是首屏主任务，方法论退出首屏。
2. 一张主图：同一时间只显示一张核心散点图，VO profile 通过标签切换。
3. 普通语言：先解释用户看到什么，再展示公式。
4. 不制造排名：不使用“最佳”“精英”“评分”等结论性措辞。
5. 渐进披露：筛选、比较、方法论按使用时机出现。
6. 状态可分享：当前学段、搜索、地区、profile 和选择状态具有明确 URL 语义。
7. 移动优先：手机上保留完整任务，不缩放桌面布局。

## 3. 用户与核心任务

### 3.1 主要用户

正在形成或比较学校候选名单的家长与学生。需要深入理解数据的用户通过同一页面的方法论入口完成任务，不建立第二套产品路径。

### 3.2 核心任务

1. 按校名、缩写、BRIN 或邮编找到学校，并独立按市镇过滤。
2. 查看当前筛选下学校在二维指标中的分布。
3. 在 VO 的 NT、NG、EM、CM profile 之间切换。
4. 选择最多四所学校，查看紧凑比较摘要。
5. 复制可复现当前状态的链接。
6. 查看数据来源、方法论、限制和联系方式。

## 4. 信息架构

页面按以下顺序组织：

1. 顶部导航：品牌、Methodologie、Over de data、Contact、语言、主题。
2. Hero：一句价值主张、一句限制说明。
3. 主搜索：学校/缩写/BRIN/邮编实时搜索、独立市镇筛选；没有第二套执行按钮。
4. Explorer：
   - 学段切换：VO / PO。
   - 筛选：市镇、学校类型、profile。
   - 主图：一张散点图。
   - 选中学校摘要。
5. 比较区：仅在选择学校后出现，最多四所。
6. 方法论和免责声明：折叠内容。
7. Contact：标题指向 `https://zhaidewei.com/`，保留邮箱和 LinkedIn。
8. 支持与版权。

## 5. 页面与视觉规范

### 5.1 品牌表达

- 产品名显示为 `AlleSchools`，通过一个暖色强调 `Schools`。
- 气质：可信、温暖、克制；避免企业后台和排行榜视觉。
- 标题可使用具有编辑感的 serif 字体栈；正文使用本地 system sans 字体。
- 不加载第三方字体或运行时 CDN。

### 5.2 色彩

- 页面底色：暖灰白；深色模式为墨绿色黑。
- 主色：深森林绿，用于比较选中边框、编号和焦点。
- 强调色：陶土橙，用于品牌和搜索命中。
- 未命中、未选中的基础点统一使用中性色；市镇不再通过唯一颜色图例编码。
- 颜色不是唯一状态编码；选中、禁用和匹配还需边框、透明度或文本。

### 5.3 间距与表面

- 主内容最大宽度约 1100–1200px。
- 卡片圆角 12–16px，阴影轻量，只用于提升主搜索和浮层。
- 同级区域使用边框和留白分隔，避免每一块都成为卡片。
- 首屏不设置独立搜索执行按钮；搜索输入实时生效。

## 6. 组件行为

### 6.1 主搜索

- 一个输入框支持校名、缩写、BRIN 和邮编。
- 主搜索不匹配市镇；市镇仅由独立地区筛选负责，两者组合采用交集。
- 输入实时生效。移动键盘的“完成”只关闭键盘，不形成第二套搜索机制。
- 搜索结果在图中高亮，非匹配点降低透明度。
- 无匹配时显示明确空状态，不清除用户输入。

### 6.2 学段与 profile

- VO / PO 是一级切换，保持现有 `mode` URL 和本地状态兼容。
- PO 只显示主指标图。
- VO 默认显示 NT；NG、EM、CM 与 NT 以标签切换同一画布的数据和 Y 轴。
- 删除未定义的 overview。若未来需要 overview，必须先在 `docs/schema.md` 定义正式 points 和指标契约。
- profile 切换必须更新标题、轴、图例、方法说明和 URL。

### 6.3 筛选

- 桌面位于主图左侧；移动端位于 bottom sheet。
- 每个筛选显示当前值或数量。
- “清除筛选”恢复当前学段默认值。
- 显式空城市选择必须保留，不能被重渲染自动恢复。
- 不提供最低样本量筛选。发布准入阈值由 pipeline 决定，浏览器不能恢复被排除数据。

### 6.4 图表

- 图表是 Explorer 的视觉中心。基础点使用中性色，搜索命中使用陶土橙，比较选择使用森林绿边框和编号。
- 点大小继续使用样本量的平方根映射，并限定最小/最大半径。
- Hover、键盘聚焦和触屏点击使用同一信息模型。
- Tooltip 显示：学校、市镇、邮编、X、Y、样本量。
- 点击点可加入/移出比较列表。
- Canvas 提供可访问名称和等价文本摘要。

### 6.5 学校比较

- 最多选择四所学校。
- 比较区显示名称、市镇、X、Y、样本量；不计算总分或名次。
- 第五所选择应被阻止，并给出非阻塞提示。
- 用户可以逐项移除或全部清除。
- 稳定身份为 `layer + school-id`；当前数据的 `school-id` 优先使用 vestiging/points id，缺失时使用 BRIN。
- profile 是视图状态，不进入学校身份。切换 profile 时保留同层学校，并刷新当前 profile 指标。
- 切换 VO/PO 时清空不兼容的比较项。
- 缺少当前 profile X 或 Y 的学校不进入当前比较列表。

### 6.6 分享

- 分享 URL 保留：语言、学段、搜索、市镇、profile 和最多四个比较身份。
- 复制链接、X、Facebook 使用同一个状态序列化函数。
- 非法枚举在读取边界归一化，不写入 storage 或分享 URL。

Canonical URL 参数固定为：

```text
lang=en|zh|nl
mode=vo|po
q=<search text>
gemeente=all|<empty>|<csv>
profile=nt|ng|em|cm
compare=<layer:school-id csv>
include_sbo=1  # 仅 PO 且用户主动包含纯 Sbo 学校时写出
```

- 状态优先级：URL > localStorage > default。
- 默认值可从写出 URL 省略，但解析后必须得到确定默认值；VO profile 默认 `nt`。
- `gemeente=all` 表示当前 layer 的全部可用市镇；`gemeente=` 表示显式全不选；仅部分选择时写入 CSV，禁止把默认全选展开成长列表。
- 用户修改搜索、市镇、mode、profile、语言或比较状态后，地址栏立即写回同一个 canonical serializer；地址栏、分享链接和 localStorage 不得分裂。
- 读取兼容旧 `city` 键，写出只使用 `gemeente`；读取其他未知键但不传播。
- 参数写出顺序固定为 `lang, mode, q, gemeente, profile, compare, include_sbo`；`include_sbo` 默认关闭时省略。

## 7. 响应式规则

### 桌面（≥ 768px）

- 筛选栏与图表采用约 220px / 自适应双栏。
- 搜索采用学校输入和地区输入两列。
- 图表高度不低于 420px。

### 移动（< 768px）

- 导航简化但保留语言和主题。
- 搜索纵向排列。
- 图表单列且保持可读纵横比。
- 筛选通过底部按钮打开 modal bottom sheet，支持焦点约束、Escape、关闭后焦点归还。
- profile 标签允许水平滚动，不压缩字号。
- 比较区使用纵向列表。

## 8. 多语言与内容

- 支持英文、中文、荷兰文，英文为默认语言。
- 切换语言同步 `document.documentElement.lang`。
- 所有新增用户可见文案进入统一 i18n 字典。
- 荷兰文不得混入中文或占位文案。
- Contact 标题链接到 `https://zhaidewei.com/`。
- 用户可见文案不得出现无正式数据契约支持的排名暗示：`best`、`elite`、`strength`、`最佳`、`精英`、`更强` 及对应荷兰文判断性表达。

## 9. 技术约束

- 保持静态站点，可由 `view_xy_server.py --static` 构建到 `public/`。
- 保持 `docs/schema.md` 的数据契约。
- `view_xy_logic.js` 是可测试纯逻辑的 canonical home；HTML 不复制同名逻辑。
- 浏览器资产必须锁版本并本地托管。
- 数据注入必须保持脚本上下文安全编码。
- 本地服务只能绑定回环地址并只服务 `public/`。

## 10. 验收方案

### 10.1 自动化门禁

每次交付必须通过：

```bash
git diff --check
uv run --python 3.13 --with-requirements requirements-dev.txt pytest -q
node --test tests/view_xy_logic.test.js
npm audit --audit-level=high
npm run build:css
uv run --python 3.13 --with-requirements requirements.txt \
  python view_xy_server.py --demo --static
```

自动化至少覆盖：

- 搜索解析和匹配。
- profile、mode、language 的枚举归一化。
- 分享状态序列化和回放。
- 显式空城市选择。
- 比较列表上限、去重、移除。
- XSS 注入回归。
- points/meta/GeoJSON/long-table 契约。
- canonical URL 参数、固定排序、旧 `city` 迁移和 URL 优先级。
- `layer + school-id` 身份、切层清空和切 profile 保留。
- 用户可见静态文案的无排名暗示扫描。

### 10.2 功能验收矩阵

| 编号 | 类型 | 场景 | 通过标准 | 证据 |
|---|---|---|---|---|
| F01 | manual | 首次打开 | 默认英文、VO NT、有图且无 console error | acceptance receipt + screenshot |
| F02 | automated + manual | 搜索学校 | 仅校名/缩写/BRIN/邮编命中；点高亮，其他点弱化，计数正确 | Node test + receipt |
| F03 | manual | 搜索无结果 | 显示空状态，输入和市镇筛选保留 | receipt + screenshot |
| F04 | manual | 切换 PO | 标题、轴、数据、方法说明同步更新，比较清空 | receipt |
| F05 | automated + manual | 切换 VO profile | 单一画布更新对应数据，URL profile 同步，比较学校身份保留并刷新指标 | Node test + receipt |
| F06 | automated + manual | 城市全不选 | 图表为空且状态不会被下一次渲染重置 | Node test + receipt |
| F07 | automated + manual | 分享链接回放 | 新窗口还原语言、mode、搜索、城市、profile 和 compare | Node test + receipt |
| F08 | automated + manual | 选择比较 | 使用 `layer + school-id`；可添加、移除、清空，最多四所且无排名 | Node test + receipt |
| F09 | manual | 语言切换 | 所有新增文案和 `html.lang` 同步 | 三语言 receipt |
| F10 | automated + manual | Contact | 标题打开 `https://zhaidewei.com/`，邮箱和 LinkedIn 可用 | DOM assertion + receipt |
| F11 | automated + manual | 无排名暗示 | 三语言静态文案和可见页面无未授权判断性表达 | text scan + receipt |

### 10.3 可访问性验收

- 所有交互可仅用键盘完成。
- 可见焦点不被移除。
- bottom sheet 打开后焦点进入，Tab 不离开，Escape 关闭并归还焦点。
- profile 标签使用正确的 tab/pressed 语义。
- Canvas 具有可访问名称和文本替代。
- 文本与背景达到 WCAG AA 对比度。
- 颜色不是匹配、选中或错误的唯一提示。

### 10.4 视觉验收

在浅色和深色下分别检查：

- 桌面：1440×900、1024×768。
- 移动：390×844、360×800。

每个尺寸必须确认：

- 首屏层级清晰，主搜索和主图没有竞争。
- 无水平页面滚动、裁切或重叠。
- 图表坐标轴、tooltip 和 profile 标签可读。
- 选中、hover、focus、empty、loading 状态视觉一致。
- 中英荷三种语言不会破坏布局。

### 10.5 人工验收 receipt

人工验收必须写入 `artifacts/acceptance/<commit>/acceptance.json`。`<commit>` 是被验收的精确 Git commit；未提交工作树只能生成 draft receipt，不能作为 Goal 完成证据。

每条记录至少包含：

```json
{
  "commit": "<full sha>",
  "browser": "<name and version>",
  "viewport": {"width": 1440, "height": 900},
  "language": "en",
  "theme": "light",
  "check": "F01",
  "result": "pass",
  "screenshot": "screenshots/F01-en-light-1440x900.png",
  "notes": ""
}
```

- 每个 manual 项必须给出 viewport、操作步骤、预期结果、实际结果和截图路径。
- 浅色/深色、1440×900、1024×768、390×844、360×800 与三种语言按验收矩阵覆盖，不以单张截图代替。
- receipt、截图和页面必须绑定同一个 exact commit。

### 10.6 发布验收

1. 精确 commit 通过全部本地门禁。
2. push `main` 后等待 Vercel 构建完成。
3. 线上页面返回 200，CSS/JS 本地资产均返回 200。
4. 线上 HTML 包含本次版本特征且不包含 CDN 引用。
5. 桌面和移动各执行一次 F01、F05、F07、F10，并在 exact-commit receipt 中可回读。

## 11. 开发切片

1. 页面骨架、视觉 token、导航、Hero、主搜索。
2. Explorer 双栏布局和单图 profile 切换。
3. 筛选状态统一与 URL 回放。
4. 比较列表和图表选择交互。
5. 多语言、响应式和可访问性。
6. 自动化、视觉验收、发布回读。

只有 automated 门禁通过，且 exact-commit manual receipt 覆盖所有人工项后，Goal 才能标记完成。

## 12. 决策记录

| 决策 | 冻结值 |
|---|---|
| VO 默认 profile | `nt`，删除未定义 overview |
| 主搜索字段 | 校名、缩写、BRIN、邮编 |
| 市镇职责 | 仅由 `gemeente` 筛选负责；与主搜索取交集 |
| 搜索触发 | 实时，无独立执行机制 |
| 最低样本量筛选 | 删除；准入由 pipeline 管理 |
| 比较身份 | `layer + school-id` |
| 比较生命周期 | profile 切换保留并刷新；layer 切换清空 |
| 比较上限与分享 | 最多 4 个，写入 `compare` |
| URL 优先级 | URL > localStorage > default；地址栏实时写出 canonical 参数；市镇全选使用 `gemeente=all` |
| 颜色语义 | 中性基础、橙色命中、绿色比较选择 |
| 验收证据 | automated test 或 exact-commit manual receipt |

本表与正文、`docs/schema.md` 和自动化测试共同构成状态模型的开发门禁；出现冲突时先修订本设计，不在实现中自行选择新语义。
