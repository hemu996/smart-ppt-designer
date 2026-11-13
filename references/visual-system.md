# 视觉系统规范

**一份 PPT = 一套视觉系统**。配色、字体、装饰、间距、图表配色全部从这一套里取值，任何一处临时改色或自选字号都会破坏"整份统一"这条验收标准（红线第 5、13 条）。

## 一、文件与字段

位置 `assets/visual-systems/<system_name>.json`。**不设默认风格**：整份稿必须先按内容检索或选定一套、并写明 `style_rationale`；脚本不做兜底回落——未指定或名字不存在时直接报错（v5.6）。

内置 5 套（人工校订）：

| 文件 | 名称 | 模式 | 适用 |
|---|---|---|---|
| `business-blue.json` | 商务科技蓝 | light | 路演、汇报、技术方案 |
| `tech-dark.json` | 科技深青 | dark | 技术类竞赛、平台/装备 |
| `national-style.json` | 国潮棕金 | light | 中医药、非遗、文旅 |
| `humanities-warm.json` | 人文暖色 | light | 社会服务、教育、公益 |
| `red-gold.json` | 国奖红金（亮底稳重） | light | 竞赛答辩、政务路演、乡村振兴 |

参考稿提取的 9 套（`ref-*.json`，来源原文件见 `assets/templates/references/`，逐套卡片见 `assets/style-cards/`）：

| 系统名 | 标签 | 模式 | 来源参考稿 |
|---|---|---|---|
| `ref-award-red-gold` | 国奖红金·暗底烫金 | light | 16页-国奖水准红金风格PPT-康帅制作.pptx |
| `ref-redtour-red` | 红旅赛道·正红亮金 | light | 红旅赛道PPT模板.pptx |
| `ref-heritage-earth` | 国风非遗·棕金暗调 | light | 红色国风非遗文化.pptx |
| `ref-blackgold-tech` | 黑金科技·挑战杯通用 | dark | 【黑金版】编号0012科技风互联网加挑战杯通用PPT模板.pptx |
| `ref-medical-blue` | 医疗器械·蓝白专业 | dark | 蓝白色医疗器械.pptx |
| `ref-chip-industrial` | 芯片工科·黑金工业 | dark | 黑色-芯片工科模板.pptx |
| `ref-tea-green` | 茶产业·茶绿清雅 | light | 茶产业振兴.pptx |
| `ref-airflow-medical-blue` | 医疗产品路演·深蓝 | dark | Airflow·艾弗洛…（pdf/pptx 为同一设计） |
| `ref-typo-closing` | 大字结尾页·书法金句 | dark | 23. PPT结尾-弄潮起舞 踏浪前行.pptx |

索引与关键词见 `assets/style-index.json`；检索用 `python scripts/find_style.py <关键词>`，新参考稿用 `scripts/extract_style.py` 提取入库。

字段：`colors`（primary/secondary/accent/background/text/text_light）、`fonts`（title/body + 字号区间）、`decorations`（title_bar/card_border/section_divider）、`navigation`（active/inactive 色）、`chart_palette`、`density`。

## 二、配色规则

1. **只允许 6 个色 + 图表调色板**。需要新的深浅变化时，用同色的透明度（`transparency`）实现，不要新增色值。
2. `accent` 是强调色，**单页占比 ≤ 5%**：用于关键指标数字、当前章节高亮、图表第 4 系列、最大流失标注。
   - 首轮视觉校验结论：大面积橙色块（如整条漏斗层）会与"商务克制"基调冲突，已改为小面积强调。
3. 文字与底色对比度 **≥ 4.5:1**（正文）/ ≥ 3:1（≥ 24pt 的标题）。深色系统与"白字压图"场景必须实测：
   - 白字压图时，蒙版透明度 55–70（`overlay_alpha`），不够就加深到 70–80，不要靠加粗救；
   - 浅色系统下正文用 `text`，辅助信息用 `text_light`，不要用纯黑 `000000`。
4. `background` 为页面基础色；深色系统要同时确认页码、辅助线用色可读。

## 三、字体规则

1. 只用 `fonts.title` / `fonts.body`（本包统一为"微软雅黑"），**禁止模型自选字体**；字体白名单校验在 `scripts/detect_layout.py`。
2. 字号必须落在视觉系统给的区间内。**v5.5 起整份 PPT 使用统一字号梯度（H1–H4 / Body / Caption / Metric），不允许随意改**（红线第 16 条）：

| 层级 | 用途 | 字号区间 | 字重 | `role` |
|---|---|---|---|---|
| H1 | 封面主标题 | **36–44pt** | 粗体 | `title`（封面页） |
| H2 | 章节页标题 | **28–32pt** | 粗体 | `title`（章节页） |
| H3 | 页面主标题 | **20–24pt** | 粗体 | `title`（内页） |
| H4 | 区块小标题 | **16–18pt** | 半粗 | `module_title` / `subtitle` / `label` |
| Body | 正文 | **12–14pt** | 常规 | `body` |
| Caption | 注释/来源/数据标签 | **10–11pt** | 常规 | `caption` |
| Metric | 核心数据大字号 | **36–60pt** | 粗/强调色 | `metric` |

对应视觉系统字段：`title_size` / `section_size` / `page_title_size` / `module_size` / `body_size` / `caption_size` / `metric_size`；`validate_plan.py` 会按元素 `role` 与页面类型核对区间。

3. 加粗只用于标题与关键数字，正文不加粗；同一页字号层级不超过 4 级。

## 四、装饰规则

| 装饰 | 取值 | 实现 |
|---|---|---|
| 标题条 | `left_accent_bar` | 原生细矩形（宽 0.06–0.1in）贴标题左侧 |
| 卡片边框 | `rounded_light` | 原生 roundRect + 浅色描边（不填实色） |
| 章节分隔 | `thin_line` | 原生细横线，宽不超内容区 |
| 印章/纹样 | 国潮系统专用 | 走 `assets/effect-templates/pattern-border.json` |

装饰元素**不承载信息**，且不得与文字重叠（`detect_layout.py` 的遮挡规则会报出）。

## 五、间距与网格

1. 画布 13.333×7.5in，安全边距：左右 0.8in、上下 0.5in（导航式布局左边界为导航栏右缘 + 0.2in）。
2. 同页模块间距统一（默认 0.3in）；模块内标题与正文间隙 ≥ 0.1in。
3. 同类页面的标题位置必须完全一致（同一个 y 值），跨页漂移会被视觉校验判为不一致。
4. 底部留白控制在 15–25%。**首轮视觉校验**发现"内容止于页面中上部、底部空白 30–44%"是最常见的观感问题 → 内容块整体垂直居中，或适当放大模块高度补足。

### 五·1、12 列网格（v5.5）

| 规则 | 取值 |
|---|---|
| 列数 | 12 列，左右边距各占 1 列 |
| 内容区 | x 1.38–12.83in（导航式内页），列宽 ≈ 0.954in |
| 间距单位 | 0.3cm 的整数倍（≈ 0.1181in） |
| 基线对齐 | 同页的标题基线、正文基线、图表基线用同一组 y 值 |

- `assets/config.json` 的 `grid` 段给出列数、单位与容差；`assets/layout-templates/*.json` 的 zone 坐标已按网格给出。
- 校验器对显著偏离网格的元素给出 warning（容差 0.02in），不影响其它检查。
- 网格的作用是"看起来齐"，不是"数字必须精确到小数点后四位"；容差内的偏差不要反复微调。

### 五·2、页脚规范（v5.5）

| 位置 | 内容 | 字号 | 颜色 |
|---|---|---|---|
| 左下 | 项目名 / 团队名（取 `brief_intent.deck_title`） | 10–11pt | `text_light` 浅灰 |
| 右下 | 页码 | 10–11pt | `text_light` 浅灰 |

- **位置固定，不随内容变化**：内页、章节页、结尾页都放；封面用"参赛信息行"替代页脚。
- 由 `build_pptx.js` 统一写入（`config.footer` 控制开关与字号），页面计划里不要重复写页脚元素。
- 页脚不得与内容重叠：内容区下边界留在 6.6in 以上（口径/结论行），页脚固定在 7.05in。

### 五·3、视觉焦点与图标风格（v5.5）

- **每页只有一个视觉焦点**（红线第 17 条）：焦点元素字号最大、颜色最突出、位置最显眼；其余元素字号更小、颜色更浅、作辅助。评委一眼看过去，先看到的应当是你想让他看到的那一个。校验器会检查"同页多个 metric""最大字号并列""最大字号不足 H3 下限"三种情形。
- **图标风格统一**（红线第 18 条）：整份 PPT 只用一种图标风格（本包图标库为面性 `solid`），同层级图标尺寸一致，颜色取辅助色（`secondary` 或 `accent`），不得线性/面性混搭。视觉系统里的 `icon_style` 字段即整份图标风格。
- **图表配色**：同一系列用同一颜色；对比系列用主色 vs 强调色；**要突出的那一个数据点用强调色，其余用中性灰**（页面计划里用 `chart.highlight_index` 指定）。
- **转场**：整份统一"淡入"（`transition: "fade"`），不使用自定义动画；章节页可用简单推进。

## 六、切换视觉系统（v5.6：不设默认）

1. 每份计划都必须在 `design_brief.visual_system` 显式写系统名，并在 `style_rationale` 写明选择依据；`config.json` 已不再提供默认风格，脚本也不做兜底回落（未指定或名字不存在直接报错）。
2. 选法：`python scripts/find_style.py <内容关键词>` 检索 → 命中就取 `system_name`；无命中就读参考稿推导，或先问用户一句。
3. 用户在对话里指定了风格时以用户指定优先，并把来源写进 `style_rationale`。
4. **不要在一份 PPT 中途换系统**，也不要混搭两套的颜色。