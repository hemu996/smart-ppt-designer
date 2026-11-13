# 示例简报（example_brief.md）

> 用途：演示"从材料出发"的完整输入形态。配套产物：`example_from_pdf.pdf`（输入材料样本）、`example_page_plan.json`（A/B 两套页面计划）、`example_check_report.md`（排版检测报告）、`example_generated_images/`（复用与共享的示例配图）。

---

## 一、输入形态（v5.1 多源输入）

本示例演示"PDF 材料 + 口头要求"的组合：

| 输入 | 文件 | 说明 |
|---|---|---|
| PDF 材料 | `example_from_pdf.pdf` | 申报材料节选（背景、试点做法、试点数据、对比结论、下一步） |
| 口头补充 | 见下"要交付什么" | 受众、时长、风格偏好、语气要求 |

解析方式：`python scripts/parse_source.py --input examples/example_from_pdf.pdf --out output/source.md`（本示例实测抽取 684 个有效字符）。

---

## 二、要交付什么

**项目名称**：银龄中医药社区服务方案

**交付物**：一份给竞赛评委做 10 分钟路演的 PPT，需能讲清楚。

**受众**：中医药领域竞赛评委（5 人，熟悉行业，会追问数据口径和落地可行性）。

**期望效果**：让评委相信"以社区为支点做中医健康服务"**可行、可量化、能复制**，支持进入复赛。所以沟通目的是**说服**，不是罗列工作。

**已知约束**：

- 不要"互联网术语"，评委更看中医服务本身的机制；
- 数据必须注明口径（时间、样本量、来源）；
- 风格偏商务、克制，不要太花哨；希望封面有一点"分量感"（允许使用一处金色书法标题装饰）。

---

## 三、第 2 步：设计规范确认的结果

| 项目 | 取值 | 依据 |
|---|---|---|
| 沟通目的 | **说服** | 简报明确"要说服评委可行性" |
| 主信息关系 | **比较** | 主体内容是"3 类服务路径对比 + 试点数据对照" |
| 受众 | 竞赛评委（5 人，熟悉行业） | 简报写明 |
| 视觉系统 | `business-blue`（商务科技蓝） | 简报要求"商务、克制"；竞赛路演默认 |
| 导航方式 | `sidebar`（侧边栏章节导航） | 页数 13–15，章节 3 个，评委需要随时知道进度 |
| 章节 | 背景与缺口 / 方案设计 / 试点与落地（A）；背景与缺口 / 方案与选择 / 验证与复制（B） | 内容分段 |
| 页数 | A 15 页 / B 13 页（10 分钟路演 ≈ 1.5–2 分钟/页） | 时长换算 |
| 生图预算 | 4 张/3 张（3–5 张红线内） | 封面必 1 张，章节页复用同一张背景，概念页 1 张 |
| 特效预算 | A 1 处（金色书法标题） | 简报要求"封面有一点分量感"；其余保持克制 |

> 注意：`relation_type = 比较` 是本份演示稿的**主导关系**，但单份 PPT 内不同页面会按各自内容套用不同结构的卡片（痛点→方案页用因果类、落地节奏用时间类），这是正常的跨类型套用，校验脚本会以 `info` 提示复核。

---

## 四、第 5 步：卡片与布局模板的选择（示例）

| 页（方案 A） | 布局模板 | 卡片 | 选择理由 |
|---|---|---|---|
| 1 封面 | `cover-full-image` | `cover-title` | 四要素封面 + 一处金色书法装饰 |
| 2 现状→方案 | `sidebar-nav` | `problem-solution` | 因果主张，上下对照 |
| 3 三类需求 | `data-dashboard` | `comparison-matrix` | **3 个对象：严禁双栏**，用矩阵/图表 |
| 4 61% 痛点 | `data-dashboard` | `metric-highlight` | 一页只钉一个数字 |
| 6 服务闭环 | `sidebar-nav` | `problem-solution` | 断点 → 闭环，配概念插图 |
| 7 双轨服务 | `sidebar-nav` | `layout-two-column` | **恰好两个**平级对象 |
| 8 三级网络 | `sidebar-nav` | `hierarchy-tree` | 上下级包含关系 |
| 9 转化漏斗 | `data-dashboard` | `funnel-conversion` | 逐级收窄且每级有量化 |
| 10 路径对比 | `sidebar-nav` | `comparison-matrix` | 原生表格，三对象 × 三维度 |
| 12 试点成效 | `data-dashboard` | `layout-data-dash` | 指标 + 图表 + 表格同屏 |
| 13 落地节奏 | `sidebar-nav` | `timeline-horizontal` | 3 个有真实先后的节点 |

方案 B 的结构差异（同样命中卡片与模板，但顺序与骨架不同）：**数据先行**——61% 痛点在开篇、三类路径对比表提到第 6 页、方案总览用三模块侧边栏页；「调研方法与口径」用 `four-grid` 四宫格，主动交代样本量与局限。

---

## 五、示例配图的素材说明

| 文件 | 用途 | 说明 |
|---|---|---|
| `slide_1_cover_visual.png` | A/B 封面背景 | 商务蓝抽象配图（生图，1920×1072） |
| `section_background.png` | A 第 5、11 页 / B 第 5、9 页章节背景 | **四个章节页复用同一张背景图**，保证同类页观感一致 |
| `slide_6_concept_illustration.png` | A 第 6 页概念插图 | 半版插图（生图，944×704） |
| `effect_gold_calligraphy.png` | A 第 1 页封面装饰层 | 金色书法 PNG（**透明底**，由生图 + 抠图两步得到），仅作装饰层，标题文字仍是原生文本框 |

> 素材侧说明：生图接口对宽高有整除/像素区间约束，会把 1920×1080 归一为 1920×1072、800×600 归一为 944×704，属接口侧正常归一化，不影响嵌版比例。

---

## 六、下一步

1. 校验：`python scripts/validate_plan.py examples/example_page_plan.json --knowledge knowledge`
2. 拆解：`node scripts/build_pptx.js --plan … --candidate A --out output/example_deck_A.pptx`
3. 检测：`python scripts/detect_layout.py output/example_deck_A.pptx --out examples/example_check_report.md`
4. 终审：按 `references/evaluation-rubric.md` 的 14 项验收 + 8 个视觉维度逐页复核