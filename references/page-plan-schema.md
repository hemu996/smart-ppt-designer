# 页面计划 JSON Schema（v5.1）

页面计划是**构思与构建之间的唯一契约**：上一步是"想"，下一步是"做"。写之前读本文；模板见 `assets/page-plan-template.json`；校验用 `scripts/validate_plan.py`。

## 一、顶层

```json
{ "brief_intent": {...}, "design_brief": {...}, "meta": {...}, "candidates": [ {...}, {...} ] }
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `brief_intent` | ✅ | 沟通目的 + 信息关系 + 受众 + 风格偏好 |
| `design_brief` | ✅ | 视觉系统、导航方式、章节列表、页数与预算（v5.1 新增） |
| `meta` | ⬜ | `generated_by` / `image_budget` / `slide_count` |
| `candidates` | ✅ | **恰好 2 套**（`A` / `B`），且两套结构不同 |

以 `_` 开头的键是说明字段，校验脚本忽略。

## 二、`brief_intent`

| 字段 | 枚举 |
|---|---|
| `communication_goal` | `告知` / `说服` / `汇报` / `推广` / `教学` |
| `relation_type` | `比较` / `流程` / `层级` / `因果` / `时间` / `并列` |
| `audience` | 自由文本 |
| `style_preference` | `business` / `tech` / `humanities` / `minimal`（对应 `assets/image-styles.json`） |
| `deck_title` | 演示稿标题 |

## 三、`design_brief`（v5.1 新增，必填）

| 字段 | 必填 | 约束 |
|---|---|---|
| `visual_system` | ✅ | **不设默认**，必须显式给出 `assets/visual-systems/` 下的系统名（内置 5 套 / 参考稿提取 `ref-*` / 自定义 `custom-*`）；用 `scripts/find_style.py` 按内容关键词检索 |
| `style_rationale` | ✅ | ≥ 12 字，写清"为什么选这套风格"（内容依据或参考稿来源）；判断不出时先问用户，不要回落默认 |
| `navigation_mode` | ✅ | `sidebar`（默认）或 `top` |
| `navigation_scope` | ⬜ | v8.9：`full` / `sparse`（默认，只画每章首个内容页）/ `none`；逐页 `slides[].show_navigation`（布尔）可覆盖 |
| `navigation_enabled` | ⬜ | v8.9 总开关：`false` = 全篇不画章节导航；缺省按包级 `config.navigation.enabled`。优先级：逐页 `show_navigation` > 本开关 > `navigation_scope` |
| `sections` | ✅ | 章节名数组，2–6 项；内页 `section_name` 必须取自这里 |
| `page_count_target` | ⬜ | 目标页数；与实际相差 >30% 需在 `rationale` 说明 |
| `image_budget` | ⬜ | 默认 3–5 |
| `effect_budget` | ⬜ | 默认 ≤ 3 |
| `animation_mode` | ⬜ | v9.0.6 页内元素动画素材库开关：`none` / `basic`（默认）/ `advanced`；`none` 时元素不得写 animation |
| `template_mode` | ⬜ | v9.0.6 模板生成模式：`free`（默认）/ `fill` |
| `user_template` | 条件必填 | `template_mode=fill` 时必填，值为 `assets/user-templates/index.json` 的 id / 名称 / path |

## 四、`candidates[]`

| 字段 | 必填 | 约束 |
|---|---|---|
| `candidate_id` | ✅ | `A` / `B` |
| `rationale` | ✅ | ≥ 30 字，写清"适合什么场合 + 代价" |
| `slides` | ✅ | ≥ 3 页；两套方案的 `(slide_type, layout_template, card_used)` 序列不得完全相同 |

## 五、`slides[]`

| 字段 | 必填 | 约束 |
|---|---|---|
| `slide_id` | ✅ | 正整数、候选内唯一且升序 |
| `slide_type` | ✅ | `cover` / `section_divider` / `content` / `concept` / `data_chart` / `closing` |
| `section_name` | 条件必填 | 内页（content/concept/data_chart）必填，且必须 ∈ `design_brief.sections`；封面/章节/结尾页可为空 |
| `layout_template` | ✅ | ∈ `sidebar-nav` / `four-grid` / `data-dashboard` / `cover-full-image` |
| `card_used` | ✅ | 必须是 `knowledge/cards/` 中存在的卡片 id |
| `claim` | ✅ | 一句话主张，≤ 40 字 |
| `notes` | ✅ | **讲者备注，非空**；建议四段：主张 / 选中卡片与理由 / 背景素材说明 / 讲述提示 |
| `image_required` | ✅ | 布尔 |
| `image_type` | 条件必填 | `image_required: true` 时必填：`cover_visual` / `section_background` / `concept_illustration` / `closing_background` |
| `image_prompt` | 条件必填 | `image_required: true` 时必填（脚本按视觉系统拼；手写易漂） |
| `image_path` | ⬜ | 生图/图库回填；空 → 构建时按三级降级处理 |
| `photo_source` | ⬜ | 图库图必填：`{provider, page_url, author, license}` |
| `effects[]` | ⬜ | 特效装饰层：`{template, x_in, y_in, w_in, h_in, prompt_args, effect_path, on_fail}` |
| `elements[]` | ✅ | 数组，可为空（空数组时按 `claim` 自动生成标题） |

`slide_type` 与配图、导航的关系：

| slide_type | 配图 | 导航 |
|---|---|---|
| `cover` | ✅ 必生（`cover_visual`） | ❌ 不加 |
| `section_divider` | ✅ 必生（`section_background`） | ❌ 不加 |
| `concept` | ✅ 选生（≤2 页，`concept_illustration`） | ✅ |
| `data_chart` | ❌ 不生（用原生图表） | ✅ |
| `content` | ❌ 不生 | ✅ |
| `closing` | ⬜ 选生（`closing_background`） | ❌ 不加 |

## 六、`elements[]`

共有字段：

| 字段 | 必填 | 约束 |
|---|---|---|
| `type` | ✅ | `text` / `shape` / `chart` / `table` / `icon` / `image` / `formula` |
| `role` | ⬜ | `title` / `subtitle` / `module_title` / `body` / `caption` / `label` / `metric` / `decoration` |
| `x_in` `y_in` `w_in` `h_in` | ✅ | 英寸；`w_in>0`、`h_in>0`，且不越出画布与所在布局模板 zone（容差 0.02in） |
| `z_index` | ✅ | 整数 ≥ 0，声明绘制层级；数字越大越靠上（v5.2 多图层堆叠，见本节末） |

- **`text`**：必需 `text`、`font_pt`；可选 `font`（白名单）、`color`、`bold`、`align`、`valign`。字号必须落在视觉系统区间：正文 13–15、标题 24–28、模块标题 16–18、指标数字 40–60、辅助 10–12。
- **`shape`**：必需 `shape_type`（`rect` / `roundRect` / `ellipse` / `line` / `chevron` / `triangle` / `pentagon` / `diamond`）；可选 `fill`（视觉系统色或 token）、`line_color`、`fill_transparency`。
- **`chart`**：必需 `chart` 对象：`{chart_type, labels, series:[{name, values}], show_legend, show_value}`；`chart_type` ∈ `column` / `bar` / `line` / `pie` / `doughnut`。**分类必须写业务名，不允许 1/2/3 占位**；`labels` 与每个 `values` 长度必须相等。
- **`table`**：必需 `table` 对象：`{rows: [[...]], header_row: true, col_widths_in: [...]}`；行 ≤ 6、列 ≤ 5；必须原生表格渲染。
- **`icon`**：必需 `icon`（`assets/icon-library/icons.json` 中的 `icons` 键名）；可选 `color`（token）。单页 ≤ 4 个。
- **`image`**：必需 `image_path`；用于概念页半版插图等需要精确坐标的场景。
- **`formula`**：必需 `text`（Unicode 数学字符写法）；复杂排版公式在页面上标注位置后由人工在 PowerPoint 公式编辑器替换（`style: "omml_todo"`）。

### 多图层堆叠（z_index，v5.2 硬要求）

一页 PPT 不是扁平的，而是**四层从下到上堆叠**：背景层 → 装饰层 → 内容层 → 标题层。页面计划里用 `z_index` 显式声明每个元素的层级，构建脚本按 `z_index` 升序绘制。

| 层 | 名称 | `z_index` 区间 | 放什么 | 写给谁 |
|---|---|---|---|---|
| L1 | 背景层 | `0` | 整页背景图 + 蒙版 / 纯色底（由 `image_path` 与母版处理，**不写成元素**） | 母版与构建脚本 |
| L2 | 装饰层 | `10–19` | 纹样边框、发光元素、粒子、色带、装饰线、`effects[]` 素材 | 装饰，不承载信息 |
| L3 | 内容层 | `20–29` | 正文、标签、说明、图表、表格、图标、内容插图、公式 | 承载信息、必须可编辑 |
| L4 | 标题层 | `30–39` | 页面主标题、副标题、封面大标题 | 一句话主张 |

**硬约束（违反即返工）**：

1. 每个元素都必须有 `z_index`；缺失即不通过校验。
2. **装饰层不得高于内容层**：`max(装饰 z_index) < min(内容 z_index)`（校验脚本会报 error）。装饰图压住文字＝文字不可读。
3. 背景层交给母版与 `image_path`，不要用 `z_index: 0` 的元素去模拟背景。
4. 标题层在内容层之上（`≥ 30`）；标题直接压图时必须先有 L1.5 蒙版（封面/章节页由构建脚本自动加，透明度按视觉系统）。
5. `effects[]`（烫金/发光/纹样/粒子）默认 `z_index: 12`，属于 L2；它们不占生图预算但仍受风格统一约束。

**z_index 参考值**：装饰形状 10、辅助装饰线 11、`effects` 素材 12、正文/标签 20–21、说明与口径 22、图标 23、图表/表格 24、内容插图 25、模块小标题 26、页面标题 30、副标题 31、封面大标题 32。

## 七、校验规则速览（`validate_plan.py`）

**error**：必填缺失/类型错误/枚举越界；坐标越界或越出模板 zone；`candidates` 不是 2 套或结构完全相同；`slides` < 3；`slide_id` 重复或非升序；`card_used` 不存在；`section_name` 不在 `design_brief.sections`；`notes` 为空；`layout_template` 不存在；`icon` 不在图标库；`table` 行列超限；`chart.labels` 与 `values` 长度不等且出现纯数字占位；**元素缺 `z_index`、`z_index` 为负、装饰层 z_index ≥ 内容层 z_index**；生图超预算（>5 张或占比 >1/3）；特效超预算；`data_chart` 页仍配图。

**warning**：`claim` 超 40 字；生图少于 3 张；字号越出视觉系统区间；卡片 `relation_type` 与主关系不同（正常跨类型套用，提示复核）；元素坐标落在布局模板 zone 之外但未越画布；**装饰元素 `z_index` 不在 10–19、标题元素 `z_index` < 30**；`effects[]` 未声明 `on_fail`。

**info**：正文页配图；元素为空按 claim 自动标题；卡片库自身的结构提示。