---
name: smart-ppt-designer
description: 从简报、参考稿、PDF/DOCX 或已有 PPT 出发，生成达到国赛/创赛水平的高密度、强视觉冲击力、原生可编辑 PPTX：风格从素材库按内容检索选定（不设默认）、母版内置章节导航、原生图表与表格、讲者备注、封面级背景图，并在使用中持续学习改进。凡用户提到做 PPT、生成演示文稿、做汇报/路演/答辩/竞赛材料、把文档或大纲变成幻灯片、页面布局与版式设计、PPT 配图与封面设计、演示稿质量检查、给已有 PPT 提取风格、建立参考素材库时应使用本技能；即使没有出现"PPT"字样（如"帮我把这份材料做成能讲的 20 页演示稿""这套内容怎么做成幻灯片"）也应触发。仅在用户只想讨论演示稿的文字内容、或只需要推荐现成模板、或只需要做纯图片海报时才不使用本技能。
---

# 智能演示文稿生成（smart-ppt-designer v9.0.8）

> ## G0 基线完整性闸门（最高优先级 · 2026-11-12 血泪教训）
>
> **凡用户说「在 / 给我的 X 上套 / 加 / 适配 Y」——操作对象就是那个 X，交付物必须逐项等于它。**
> 内容一页不删、一字不改；加的只有 Y。不是「换一份稿子」，更不是「以参考件为骨架重新填内容」。
>
> **交付前必须跑**（不跑 = 禁止交付）：
> ```
> python scripts/baseline_gate.py <用户原稿.pptx> <待交付产物.pptx>
> ```
> 退出码 1 = 拦截（页数 / 逐页文字 sha / 文字字符数 / 备注 / 原生图表 / 媒体 任一不等即拦）。
> **G0 不过，不许谈效果、不许谈「能打开」、不许 present。**
>
> **正确实现范式**：`scripts/overlay_anim_on_original.py` —— 逐字节复制原稿全部 parts，
> 只对 `slideN.xml`「只增不删」追加 morph 转场（插在 `clrMapOvr` 前）+ 同名跨页
> `morph_ribbon` 进度带（纯色 `p:sp`，不引 image rels）；脚本内 assert 每页文字改写前后一致。
> 实测：20 页 / 4125 字逐页 sha 全一致 / 备注 20 / 图表 1 / 媒体 5，G0 通过；
> 原稿与产物主体区像素差异 0.000%（只有底部进度带与转场不同）。
>
> 本项目真实教训：用户《生涯发展报告》20 页 / 4125 字 / 20 备注 / 1 图表，
> 助手用上游参考件（5 页）当骨架交付了 5 页 / 179 字 / 0 备注的产物，
> 却拿「CRC OK、COM 真开、渲染成功」当完成。**结构验收 ≠ 内容保真**。


把"简报 / 参考稿 / PDF / DOCX / 已有 PPT"变成一套**原生可编辑**的 `.pptx`：风格从素材库选定（不设默认）、母版内置章节导航、高密度多模块布局、原生图表与表格、封面级背景图、每页讲者备注，并且在迭代中通过素材库与知识库越用越准。

本文件是主入口。**只按需读 `references/`**，不要把 26 篇文档一次性塞进上下文。

## 1. 六大核心能力

1. **灵活调用**：不写死主题，靠"沟通目的 + 信息关系"自动检索匹配设计卡片与布局模板；**风格同样按内容检索或从参考稿提取后再用，不设默认**（见第 4 步与 `assets/templates/README.md`）。
2. **参考素材库**：用户给的参考稿（`.pptx/.pdf`）原文件入库保留，并逐份提取出可调用的风格（`ref-*.json` + 风格卡片 + 风格索引），新参考稿可随时再提取入库。
3. **学习记忆**：评审结论回写 `knowledge/`，失败案例成为后续反例。
4. **原生深度**：母版、原生形状、数据驱动图表、原生表格、可编辑公式、讲者备注。
5. **国赛级视觉**：高密度多模块布局、章节导航、统一视觉系统、封面级背景图、装饰特效层、**多图层堆叠（背景→装饰→内容→标题）**、装饰组提密度与组件跨页复用（均落地为真实 `<p:grpSp>` 组）、封面/章节页超大字号层级。
6. **多源输入 + 多渠道配图**：PDF/DOCX/HTML/已有 PPT 都能进；缺图时**先补图**（优先复用本稿既有封面/章节图，无则 AI 按本页主题生成且必须融入本稿风格），再退"免费图库 → 纯色背景"兜底。判据见 `references/image-strategy.md` §一。

## 2. 诚实的能力边界

**能做到国金参考图的 70–80%**：高密度内页布局、章节导航、视觉系统统一、封面大图 + 大标题、原生图表与数据卡片、全对象可编辑。v8.7 起**结构密度与视觉手法已对齐素材库区间**（形/页 ≥55、组/页 ≥3、封面章节页最大字号 ≥187pt、字号跨度 ≥5.7×），差距落在实拍级大图、定制插画与设计师级细节。

**混合策略**：PptxGenJS 做不了的质感（烫金书法标题、辉光装饰、传统纹样、科技粒子）用生图 PNG 作**装饰层**嵌入；**核心内容（正文、数据、图表、表格）必须原生可编辑**。

**唯一的硬上限**：设计师级"高级感"（整体审美、细节打磨）需要人工终审微调。视觉效果层面约能到 85–90%，最后 10–15% 的"金奖级惊艳感"靠人。

## 3. 硬边界（红线，违反即返工）

| # | 红线 |
|---|---|
| 1 | ❌ 禁止 HTML 转 PPTX，只用 PptxGenJS 原生对象 |
| 2 | ❌ 禁止图表用图片贴，必须原生 Chart 且带数据源（可编辑数据） |
| 3 | ❌ 禁止表格用形状拼，必须原生 Table |
| 4 | ❌ 禁止用 PowerPoint COM 自动修复排版（只检测、只报告） |
| 5 | ❌ 禁止模型自由选字体/配色，必须取自视觉系统 |
| 6 | ❌ 禁止每页都生图，生图 3–5 张/份 |
| 7 | ❌ 禁止自实现生图，必须调用 DSH 已挂载的生图插件 |
| 8 | ❌ 禁止引入云知识库/向量库，全部本机文件 |
| 9 | ❌ 禁止用 PptxGenJS 硬做烫金/发光/渐变文字，统一用生图 PNG |
| 10 | ✅ 核心内容必须原生可编辑（正文、图表、表格） |
| 11 | ✅ 多图层堆叠：每页元素必须声明 `z_index`，按背景→装饰→内容→标题四层绘制，装饰不得遮挡文字 |
| 12 | ✅ 章节导航可用且可关（用户口径，v9.0）：制作前先问"要不要章节导航"——`design_brief.navigation_enabled` 布尔总开关，**包级默认 `false`（关闭）、计划级缺省即关闭，要开必须显式写 `true`**；`false` 即全篇不画（含母版侧栏底板）；要画按 `navigation_scope`（`full` / `sparse` **默认**：只画每章首个内容页 / `none`），逐页 `slides[].show_navigation` 优先级最高；章节过渡页不画（左侧留给 `section-rail` 装饰轨道） |
| 13 | ✅ 必须基于统一视觉系统，整份配色/字体/装饰一致 |
| 14 | ✅ 每页必须有讲者备注 |
| 15 | ✅ 缺图补齐（用户 2026-11-08 指定）：**先复用本稿既有图 → 再 AI 按本页主题补图（须符合主题、融入风格、不突兀）→ 免费图库 → 纯色背景兜底**；补图后须与相邻页并排目检，交付说明留痕。不阻塞流程，但"缺图→纯色"不再是默认答案 |
| 16 | ✅ 字体层级统一：整份字号梯度严格按 H1–H4 / Body / Caption / Metric 规范，不能随意变 |
| 17 | ✅ 每页一个视觉焦点：核心主张/核心数据最突出，其他元素作辅助 |
| 18 | ✅ 图标风格统一：整份只用一种图标风格（本包为面性），不得线性/面性混搭，尺寸一致、颜色取辅助色 |
| 19 | ❌ 高级耀眼版禁止"素"：禁止大面积白/灰背景、禁止低饱和度色、禁止每页元素少于 6 个（简洁/极简版不受此约束） |
| 20 | ❌ 高级耀眼版禁止"极简"：不能因为模型偏好就自动简化，必须按硬指标填满元素（简洁/极简版是用户主动选择，不受此约束） |
| 21 | ❌ 禁止短剧式标题：标题不得文学化、情绪化（如“我最怕的不是计划不够漂亮”），必须是正式、结论式的汇报表达；党建/政务类项目的正式政治表达（如「凝心聚力促振兴」）属规范表达，不算短剧金句；判据与正反例见 `references/narrative.md` |
| 22 | ❌ 正文禁止「AI 味」：正文不得像小红书文案 / 小说 / 短剧台词（断句太碎、口语化、每段结尾升华），要正式、朴实、像正经的项目汇报；「赋能 / 打造 / 构建 / 引领」在党建 / 政务 / 乡村振兴类项目中属正式政治语言，可正常使用，科技 / 商业类项目避免空泛使用；党建 / 政务 / 乡村振兴类项目的正常结尾升华属规范表达，商业 / 科技类才判为空泛升华；判据与正反例见 `references/narrative.md` |

**用户既有要求（不在规格红线编号内，同等约束）**：**风格不设默认**——必须按内容检索或从参考稿提取后选定，并在计划里写明 `style_rationale`；脚本不得回落默认风格，判断不出时先问用户。

| 23 | ✅ 装饰组只做版面框架：只占页边距、包成真实 `<p:grpSp>` 组、`z_index` 锁 10–19、内容页 2–3 组且不进内容安全区；装饰组不计入点缀型装饰占比口径（红线 19/20） |
| 24 | ✅ 组件复用必须定义在计划级 `components` 并跨页引用，落地为真实 `<p:grpSp>` 组；关键结构（卡片区、编号块、图例条）不得逐页重画 |
| 25 | ✅ 超大字号层级：封面 / 目录 / 章节过渡 / 结尾页标题走 `fonts.display_size`（120–287pt，耀眼版 ≥187pt），整份字号跨度 ≥5.7×；内页标题仍守 20–24pt 不放宽 |

| 26 | ✅ 页面构图两硬约束（用户指定）：每页至少 1 个非装饰元素面积 ≥ 页面 1/3；每页至少 2 个元素前后叠压（z_index 不同且几何重叠 >0.15in²）。第 3 条「错落感」经确认不启用 |
| 27 | ✅ 去 AI 感与对齐纪律：手工感装饰（手绘线条/印章/便签/纸胶带/手绘箭头，一份稿 ≤4 处）+ 卡片差异化（同页 ≥2 种形态、大小分级、左上角序号）+ 标题可用 `runs` 放大 1–2 个关键字（≥1.4×）；**倾斜仅限贴纸类装饰 ≤12°**，正文/卡片/图片/图表/框架装饰/背板一律水平垂直对齐，破局感靠"1 个元素超出卡片边框 0.1–0.3in"实现 |
| 28 | ✅ **封面强制 AI 书法体**（用户 2026-11-08 指定，不可关闭、不可降级）：封面主标必须且只能是 **AI 生成的书法 PNG**（透明底），不得用系统字体文本框冒充；仅该主标为图片，封面其余文字仍须原生可编辑。配置 `config.cover_title.enforced=true` / `allow_fallback_to_text=false`；缺图或仍有系统字主标时 `validate_plan.py` 报 **error**、`build_pptx.js` **抛错退出**，不产出残稿。提示词见 `assets/calligraphy-prompt.md`，**亮底禁用金色**（WCAG 1.38），改用深靛蓝 #1A3A5C 或墨褐 #1F1B16。 |
| 29 | ✅ **AI 生图前置质检（用户 2026-11-13 指定，开工前必跑，跳过即返工）**：任何 AI 生图前，先调一次 `image_generate` 验证能力可用（能调用、返回真实绝对路径、确认尺寸/参考图参数）；不可用就先向用户反馈，退回模板原生元素或用户实拍，不硬造。**禁止先写提示词**——先读原元素（是什么部件、在哪个 part、坐标尺寸、周围底色/装饰/光效/材质/装饰母题），把主色 hex、材质、构图、`no text/no letters/no watermark` 写进提示词，尺寸匹配原元素比例。生成后必须肉眼质检（同色系、材质协调、无乱码、留白够、缩放清晰、插入不盖导航等不可动元素），任一条不过就重生成，不许将就。禁止用 PIL 画文字条冒充设计。完整流程见 `references/ai-image-gate.md` |

某条在当前环境真做不到（如生图插件不可用），**先向用户反馈再调整，不要自行换路线**。

## 4. 素材库与风格库（v8.2）

| 位置 | 内容 |
|---|---|
| `assets/templates/references/` | 参考稿**原文件**逐份保留（不修改），索引见 `assets/templates/README.md` |
| `assets/style-index.json` | 风格库总索引：名称、标签、关键词、明暗模式、配色、来源文件、置信度 |
| `assets/visual-systems/` | 可直接调用的视觉系统：内置 9 套 + 参考稿提取 `ref-*.json` |
| `assets/style-cards/` | 每套提取风格的人可读卡片（来源、配色、字体、版式信号、置信度） |
| `assets/personal-styles/` | 个人风格库（v8.2）：满意的风格保存到这里即可被检索、校验与构建脚本识别，见其 `_README.md` |
| `knowledge/reference_analysis/` | 参考稿实测库：手法台账 + 逐页明细 + 卡片映射（`scripts/analyze_reference.py` 生成） |
| `assets/decoration-sets/` | 装饰组库（v8.7）：9 组固定几何，按 `set_id` 引用，构建时包成真实 `<p:grpSp>` 组（规范见 `references/decoration-sets.md`） |
| `assets/target-cases/` | 国金成品观感基准（v8.7）：用户提供的 8 张案例图 + 10 条共性逐图拆解 |

**素材库调用规则（锁死 / 灵活，规格 v9.3 §4.1）**：❌ **必须锁死**（整套统一、不能混）——配色、字体、装饰元素风格、图标风格；✅ **可以灵活**（每页从素材库选最合适的）——页面布局、元素堆叠方式、信息层级。一句话：**颜色字体装饰一套到底，布局每页可以不一样**。

### 素材调用总表（v9.0）

> 自检与全量清单：`python scripts/find_asset.py --list`；跨类关键词检索：`python scripts/find_asset.py <关键词…>`；内容类型 → 组合候选：`python scripts/find_asset.py --recipes`。

| 素材 | 何时用 | 怎么检索 | 计划里怎么写 |
|---|---|---|---|
| 视觉系统（20 套） | 定风格（**不设默认**） | `find_asset.py <内容关键词>`（或 `find_style.py`） | `design_brief.visual_system` + 必写 `style_rationale` |
| 设计卡片（13 张） | 按信息关系选页型 | `find_asset.py --kind card <关系词>` | `slides[].card_used` |
| 版式模板（6 个） | 按页内容结构定布局 | `find_asset.py --kind layout <内容词>` | `slides[].layout_template` |
| 装饰组（9 组） | 提密度、立版面框架 | `find_asset.py --kind decoration_set` | `elements[] = {type:"decoration_set", set_id, z_index:10–19}` |
| 图标（64 个） | 语义图标（原生形状，非图片） | `find_asset.py --kind icon <分类词>` | `elements[] = {type:"icon", icon:"<id>", color:"accent"}` |
| 计划级组件 | 跨页复用的结构块 | 见 `references/components.md` | `plan.components` + `elements[] = {type:"component", component_id}` |
| 参考素材（案例 8 / 样本 9 / 参考稿 13） | 对标、观感自检、风格提取 | `find_asset.py --kind reference`；提取用 `extract_style.py` | 非计划字段（人工参考 + `analyze_reference.py` 量测） |
| 手工感装饰组（5 组，v8.9 去 AI 感） | 降低"AI 感"：手绘线条 / 印章 / 便签 / 纸胶带 / 手绘箭头 | `find_asset.py --kind decoration_set` | `elements[] = {type:"decoration_set", set_id:"hand-drawn-lines", z_index:10–19}` |
| 视觉母题（v9.0.2） | 统一但不单调：整份选定 3–5 种装饰性母题（1 主 + 2–4 次），只约束装饰元素、面积 ≤ 页面 1/5 | `design_brief.visual_motifs`（规范见 `references/visual-motifs.md`） | `elements[] = {..., "motif":"茶芽", "role":"decoration", "z_index":10–19}` |

- 素材 id 一律**先检索再写**：写错会被校验器拦下（风格、版式、卡片、装饰组、组件、图标均会列出可选值）；
- 检索无命中时：换关键词 → 读参考稿推导 → 或先问用户，**不要回落默认值**。

**视觉母题（v9.0.2）**：初始化选定 **3–5 种装饰性母题**（1 主母题 + 2–4 次母题）写入 `design_brief.visual_motifs`，整份复用；**只约束装饰元素**（`role:"decoration"` 或 `z_index` 10–19），内容元素不受限；不同页可用不同组合，不必每页堆满；**同页母题面积 ≤ 页面 1/5**（`validate_plan.py` error 级）。规则与正反例见 `references/visual-motifs.md`。

**模板校验兜底（v9.0.2）**：页面计划生成后跑 `python scripts/check_layout_similarity.py --plan output/plan.json --candidate A`，判定每页布局与素材库常见布局库（`assets/layout-patterns/common-layouts.json`，35 条，由 10 份样本 153 页提炼）的接近度——命中 / 样本未覆盖但包内合法（可接受）/ 偏离；偏离页给出「退回最接近布局」的建议，`--fix` 可直接改判 `card_used` / `layout_template`（输出新计划，不覆盖原文件）。`validate_plan.py` 对元素量极端偏离同时给 warn。

**导航开关与范围（v9.0）**：制作前先问"要不要章节导航"——计划里用 `design_brief.navigation_enabled`（布尔，**默认关闭**：包级 `config.navigation.enabled = false`，计划级缺省即关闭、要开必须显式写 `true`；`false` = 全篇不画，含母版侧栏底板）；要画时再选范围 `config.navigation.scope` 三档——`full`（非封面页都画）/ `sparse`（**默认**：只画每章的首个内容页）/ `none`（都不画）；
逐页可用 `slides[].show_navigation`（布尔）显式覆盖，显式值优先。取舍原则：封面 / 目录 / 章节过渡 / 结尾页**不画**导航；章节页左侧留给 `section-rail` 装饰轨道，画导航会与之重叠（检测器会报 error）；内容页按"每章首次出现"画一次即可。

选风格的动作顺序（**不设默认**）：

1. 检索：`python scripts/find_style.py <内容关键词>`（可加 `--mode dark|light`）；
2. 命中 → 取 `system_name` 写进 `design_brief.visual_system`，并在 `style_rationale` 写明选择理由；
3. **无命中不要回落默认**：改为读参考稿自行推导，或先问用户一句；
4. 新参考稿随时入库：`python scripts/extract_style.py <参考文件> --name ref-xxx`（批量用 `--batch <目录>`）。

提取出的风格是**调用起点，不是成品**；标签与适用场景建议对照原稿校订后再用。

### 动画素材库与模板生成模式（v9.0.6 合入官方 v9.9 前置功能）

**动画素材库**：制作前先问「要不要加动画」——`design_brief.animation_mode` 三档：`none`（全静态）/ `basic`（默认，基础进场）/ `advanced`（开放素材库按内容选）。动画是可检索的素材（`assets/animations/animations.json`，**43 种**：进场 13 / 强调 12 / 出场 13 / 路径 5），计划里写 `elements[].animation = "anim-<key>"`，检索用 `python scripts/find_asset.py --kind animation <关键词>`。**本机适配**（用户明确要求）：每页 ≤5 个动画元素、同页风格统一、禁用夸张效果；**不要逐元素排队淡入**（用户嫌"一个个顺序出现太久、太繁琐"），优先整页一次性或只点结论；与 `animation_library`（ppt-effects 15 条动效配方、overlay/route 双模式）是两套东西，互不冲突。底层用 PptxGenJS 动画版 fork **`@bapunhansdah/pptxgenjs`（v9.0.6 已随包安装，`node -e require(...)` 实测加载 OK）**；端到端实跑：`animation_mode=advanced` + `elements[].animation="anim-zoom"` → 产物 slide1.xml 含 `<p:timing>`/`presetID`，`build_pptx.js` 报告「引擎 @bapunhansdah/pptxgenjs｜库 43 种｜带元素 2 个」，PowerPoint COM 真开通过。

**模板生成模式**：生成前先问「用**自由生成**还是**模板填充**」——`free`（默认）按素材库检索风格自由设计；`fill` 照搬 `assets/user-templates/index.json` 里用户选定的模板，**只替换文字/数据/图片、版式不动**。选 fill 时先读索引挑 2–3 份候选给用户定 → 问封面字体「保持原样 / 升级书法烫金」→ 只读这一份 → 填充 → 素材补充 → 风格锁定。**本机适配**：选「升级书法烫金」走 `assets/calligraphy-prompt.md` + 红线 28；选「保持原样」沿用模板封面，但**红线 28（封面强制 AI 书法）不可关闭**，不得用系统字体冒充。规范见 `references/user-templates.md`。

**素材体检**：`python scripts/check_assets.py`（只读、只提醒不阻断）列出缺失的模板原文件/字体/参考素材；`INSTALL.md` 说明装哪个包。完整包与精简包代码相同，只差参考素材。

### 内置子技能：ppt-effects（动效配方库，v9.0.3 纳入 / v9.0.4 双模式 / v9.0.5 十条全通）

`subskills/ppt-effects/` 是从 GitHub 纳入的 **PPT 动效配方库**（[HY-hue113/ppt-effects](https://github.com/HY-hue113/ppt-effects)，MIT，上游 v1.1.0 / commit dd00562，15 个效果），用途是「给素材出同款动画」，不必每次重新理解做法。**v9.0.4 起双模式，v9.0.5 起 10 条全部有归属，v9.0.7 合入上游 v1.1.0 新增 011–015，现 15 条全部有归属**（不再有"不能叠加"的排除项）：默认 `overlay` 叠加模式——本包 `build_pptx.js` 照常出稿，出稿后跑 `scripts/apply_motion.py` 把配方的**动画内核**（转场层 L1 + 延续对象层 L2）叠上去，**不换链、不加页、不改版式、不要求 25/33 页**；只有用户明确要整套固定版式（L3）时才 `route` 换链走 ppt-master。各 `recipe.md` 里的页数是原参考稿内容长度，不是动画门槛——动画参数已解耦到 `assets/motion-recipes.json`。

- **先看目录**：`subskills/ppt-effects/index.md`（15 行：代号 / 名称 / 素材要求 / 动画要点 / 切换）。用户没说具体哪个效果时，**先给总览表再问**，不要直接开工。
- **问「效果N 是啥」/ 要预览**：读该效果 `spec.json` 的 `summary` 与 `preview`（图在 `docs/preview/效果N_*.png`），**必须直接答复**，不要现做预览图。
- **取用**：读 `effects/<三位序号>_<短名>/recipe.md`（人读的意图与坑）与 `spec.json`（机器读的精确参数：位置 / 时长 / 阴影 / 切换），以 `svg/` 为骨架替换素材与文案。
- **先校验素材再动手**：`python subskills/ppt-effects/tools/check_materials.py 效果9 ./素材文件夹/`；`--list` 看全部要求。**退出码 1 = 阻断，不许硬套**；退出码 0 但带 `[!]` 的先跟用户说明。
- **生成与导出**走 ppt-master 管线（命令见各 `recipe.md` 的「制作管线」），定稿后用 `tools/patch_effect.py` 做精确校正，再渲染核对。
- **硬约束**：文本框数量 / 文案 / 字体 / 字号**必须先问用户**（库内字号只作建议默认）；素材随任务传入，**库内不含用户照片**；字体优先开源可商用（霞鹜文楷 / 思源黑体、宋体 / HarmonyOS Sans / MiSans / EB Garamond），商业字库须自行取得授权。
- **许可**：MIT，版权声明原文保留在 `subskills/ppt-effects/LICENSE`。

**启用方式（每次做 PPT 必做，v9.0.4 修订）**：**不要等用户点名**——第 2 步「设计规范确认」时，先跑 `python scripts/list_effects.py` 生成 15 行菜单（代号 / 名称 / 页数(仅参考) / 叠加方式 / 动画最少页数），把菜单**原样摆给用户自己任选一条**（菜单按「高级感/复杂度」排序并标星级，目标是增加高级感、优先复杂且单次形变到位；但**星级只是参考，不是默认值，绝不替用户选**），并明确给出第 11 个选项「不用，走常规构建」。用户选完才写计划：选「不用」→ `animation_library_enabled: false`（默认）；选某条 → `true` + `motion_mode: "overlay"` + `motion_recipe: "<代号>"`（同时保留 `animation_effect` 兼容 v9.0.3）。

**overlay 叠加流程**：主链 `build_pptx.js` 正常出稿（本包版式/母版/导航/备注/封面 AI 书法强制全部照常生效）→ `python scripts/apply_motion.py --in 出稿.pptx --out 定稿.pptx --recipe <代号>`（幂等、自动备份 `.bak_motion`、可 `--restore` 回退）→ `PowerPoint COM 真开一次` + `--verify` 核对转场分布 → 交付说明留痕。`validate_plan.py` 会拒绝「overlay + L3 整套版式」，conditional 配方给 info 提示适用条件。菜单最后一列标了每条能否叠加；`references/animation-library.md` §六列了融入约束（浅亮底上玻璃/扇形物理失效、单页无 morph、克隆页须去 notesSlide 关系等 2026-11-08 实测教训）。

**route 换链流程**（仅 L3）：按 `index.md → recipe.md / spec.json → check_materials.py 校验素材 → ppt-master 生成 → patch_effect.py 校正 → 渲染核对` 取用；本包视觉体系不参与该稿。包级 `config.animation_library.enabled = false`；要开必须显式写 `design_brief.animation_library_enabled: true`。**不开时主链完全不受影响**。规则与适配边界见 `references/animation-library.md`。

## 5. 依赖与前置检查

| 依赖 | 用途 | 检查 |
|---|---|---|
| Node.js ≥ 18 + PptxGenJS ^3.12 | `build_pptx.js` 等 | `node -v`；缺依赖时在包目录 `npm install` |
| Python 3.9+ | 校验与检测脚本 | `python -V`；`parse_source.py` 的 PDF/DOCX 分支按需装 `pypdf` / `python-docx`，缺库时脚本会给出安装提示 |
| DSH 生图插件 | 配图与特效素材 | 见 `integrations/dsh-image.md`；工具名须与 `config.json` 的 `image.tool` 一致（当前 `dsh.image`） |
| 免费图库 Key（可选） | 二级降级 | 见 `integrations/free-photos.md`；无 Key 时跳过该级 |
| DeepSeek 云 API Key | 意图识别与页面构思 | DSH 侧提供，本包不读取、不落盘 |

## 6. 十三步工作流（规格 v8.6）

```
输入：文本 / PDF / DOCX / 网页 / 已有 PPT
 1. 材料解析        → 提炼核心论点 + 关键数据（含口径）
 2. 叙事结构规划    → 金字塔：结论先行 → 3–5 个理由 → 证据；每页 45–60 秒
 3. 设计规范确认    → 视觉系统 / 密度模式（简洁版 或 高级耀眼版）/ 时长 / 受众 / 导航方式与开关（要不要） / 预算
 4. 确定视觉系统    → find_style.py 按内容检索选定（不设默认）；无命中读参考稿推导或先问用户，写明 style_rationale
 5. 检索布局模板 + 设计卡片 + 图表类型（按数据语义匹配，含反例核对）
 6. 生成双候选页面计划（每页布局、配图、导航高亮章节、元素 z_index 分层、行动标题、装饰组与组件引用）
 7. validate_plan.py 校验
 8. 样张确认        → 先只出 1 页封面样张交用户确认（不满意最多调 3 次），确认后才批量生成
 9. 素材生成        → **先跑 AI 生图前置质检（红线 29：能力可用？读原元素再写提示词？生成后肉眼质检？插入前算叠压？）**；封面/章节生图、特效素材、内容插图/图标
10. build_pptx.js 构建（母版 + 导航 + 原生对象 + 视觉系统 + 备注 + 按 z_index 分层绘制）
11. detect_layout.py 检测 + score_deck.py 自我评分（<75 分重写最弱 1–2 页（默认 2），最多 2 轮；另出评委审核四维度）
12. 人工终审（严重错误→写 fail_case 回第 6 步；配图不满意→单独重生成；微调→经验回写卡片）
13. 回写知识库（fail_cases / 卡片 / 个人风格库）
```

细节见 `references/workflow.md`。第 6 步必须给 **A/B 两套**结构不同的方案与选型理由。

## 7. 按需读取指引

| 何时 | 读哪个 |
|---|---|
| 执行任意一次生成流程 | `references/workflow.md` |
| 生成前的规范确认 | `references/design-brief.md` |
| 选/改视觉系统、风格不设默认 | `references/visual-system.md` |
| 素材库与风格库（原文件、风格卡片、索引） | `assets/templates/README.md` |
| 选复杂布局 | `references/layout-templates.md` |
| 做封面/章节页 | `references/cover-design.md` |
| 写页面计划前 | `references/page-plan-schema.md` |
| 配图与降级 | `references/image-strategy.md` |
| 特效素材（烫金/发光/纹样/粒子） | `references/visual-effects.md` |
| 母版/图表/表格/公式/备注 | `references/native-objects.md` |
| 解析 PDF/DOCX/HTML/PPT | `references/source-ingestion.md` |
| 新建或改设计卡片 | `references/card-spec.md` |
| 生成前扫坑 | `references/anti-patterns.md` |
| 生成后自检 | `references/evaluation-rubric.md` |
| 用户给了参考稿/模板要借鉴，或要讨论改本包规范 | `references/reference-craft.md` |
| 查参考稿实测数据、手法台账与卡片映射 | `knowledge/reference_analysis/_README.md` |
| 查样本布局模式/封面风格/装饰元素 | `knowledge/reference_library/_README.md` |
| 叙事结构、行动标题、正文语气（禁 AI 味）、时长驱动页数、Q&A 预测、样张确认 | `references/narrative.md` |
| 国赛对齐口径与目标值（形/页、组/页、字号跨度、配图） | `references/gsl-alignment.md` |
| 国金成品观感基准（10 条共性 + 逐图拆解） | `assets/target-cases/_README.md` |
| 生图 / 抠图 provider 顺序与实测记录 | `integrations/image-providers.md` |
| 目录页版式与编号卡规范 | `references/toc-page.md` |
| 版式四原则、网格与黄金分割、留白率、图表化简等高级口径 | `references/advanced-design.md` |
| 跨客户端（WPS / Office / Mac）兼容规避与交付提示 | `references/compatibility.md` |
| 页面构图两硬约束（大小对比 / 叠压关系）的做法与阈值 | `references/composition.md` |
| 创意度开关（off / conservative / balanced / expressive） | `assets/config.json` 的 `creative_level`；档位说明见 `references/design-brief.md` |
| 用装饰组提内页密度（组数、占比口径、组合建议） | `references/decoration-sets.md` |
| 组件复用（计划级 components 与跨页整组复用） | `references/components.md` |
| 形状／轮廓语言（圆角·切角·弧形该不该用；防加装饰凑精致） | `references/shape-language.md` |
| 要不要用 ppt-effects 动效配方、开关怎么开、两条构建链的边界 | `references/animation-library.md` |
| 模板填充模式 / 用户模板库 / 素材体检 | `references/user-templates.md` + `INSTALL.md` + `python scripts/check_assets.py` |
| 模板封面人物形象不对（不是我们的人）怎么换 | `references/cover-persona-swap.md` 五步法：读图→拆描述→归类→类别文案生成→保同级效果 |
| 工作区素材怎么按类别/人物线索/视觉级别检索 | `assets/ppt-assets-catalog.json` + `python scripts/find_asset.py --kind ppt_asset <关键词>` |
| 页内元素动画素材库（43 种） | `assets/animations/animations.json` + `python scripts/find_asset.py --kind animation` |
| 封面/目录/章节/结尾页的超大字号层级 | `references/cover-design.md` §七 |
| 生成前扫失败模式、两种密度模式、图表类型匹配、Bento 卡片 | `references/failure-modes.md` |
| 想套用预置整套模板（须替换 70% 以上内容） | `assets/template-library/_README.md` |

## 8. 脚本与标准命令

在技能包根目录执行。

```bash
# 1. 解析输入材料
python scripts/parse_source.py --input 材料.pdf --out output/source.md

# 4. 素材：统一检索（风格/卡片/版式/装饰组/图标/参考素材；--list 自检、--recipes 组合推荐）
python scripts/find_asset.py <关键词…>
# 4b. 风格：检索（不设默认，先查再说）→ 需要时从参考稿提取
python scripts/find_style.py 红金 乡村振兴          # 或 --list / --mode dark
python scripts/extract_style.py assets/templates/references/xxx.pptx --name ref-xxx
#    参考稿手法实测（素材库分析）：逐份拆解 + 逐页映射到设计卡片，产出 knowledge/reference_analysis/data
python scripts/analyze_reference.py

# 6b. 【必做】列出动效配方菜单交用户自己任选一条（含「不用」），选完再写 design_brief
python scripts/list_effects.py                 # 人读 15 行表
python scripts/list_effects.py --json         # 机读，侧边栏用
python scripts/list_effects.py --id 效果9     # 单条详情
### v9.0.7 · 上游 ppt-effects v1.1.0 合入（2026-11-12）
上游 [HY-hue113/ppt-effects](https://github.com/HY-hue113/ppt-effects) 从 `e64d3e9` 推进到 `dd00562`（**v1.1.0**，2026-11-11），本包同步：
- **新增 011 中式滑转 / 012 六边形旋转 / 013 模糊遮罩 / 014 立体图片轮播 / 015 枫叶飘动** 5 个效果（spec.json + recipe.md + tools/），`effects/` 现共 **15 个**；
- `assets/motion-recipes.json` 补 5 条内核（15 条），按 A/B/C/D 归类，原 10 条**数值不变**；
- `scripts/list_effects.py` 的 TIER 补 5 条，菜单自动列出 15 行，**星级仅排序、绝不替用户选**；
- 上游 v1.0.1 的性能修复（预览图 jpg、`--brief`、`SKILL.md` 读取纪律）已吸收进 `references/visual-effects.md`；
- 按 v1.0.1 读取纪律，**不下载大体积参考 pptx**（40MB→10.5MB 那批），只同步文本元数据；需要整套版式时走 `route` 换链。
- 用户规矩不变：**做 PPT 时把 15 行菜单原样摆给用户自己挑**，第 16 个选项「不用，走常规构建」，不默认套用、不自动选。

#### v9.0.8 · 回到原版效果（2026-11-12，用户指正后换方案）
**用户口径（必须遵守）**：「除了我有特别说明、就是限制多少页以内，其他这些你都可以按照他原本那样来」——
即**不要为了「不换链/不加页/不改版式」把动效削成只剩转场或占位形状**。v9.0.4 自定的 overlay 约束是内部规则，
用户要原版效果时让位于效果。

- **补齐参考件**：011–015 的 6 份基准件 pptx 全部装入 `subskills/ppt-effects/effects/*/reference/`。
  原版效果全靠 `template-clone`：复制基准件 → 按角色换图 → 换字 → 调色；
  **造型、层级、morph、页内 timing 一律不动**（015 实测含 animMotion/animRot/animScale/animEffect 5 类）。
- **新增 `scripts/adapt_effect_template.py`**：以 013 参考件为骨架做样板，换《生涯发展报告》的 5 张图 +
  真实文案，并把色调统一到该稿的宣纸米黄 `#DDD5C4` / 墨褐 `#23201A` / 朱砂 `#B7372A` / 金 `#C9A227`。
  产物 5 页、morph 4 页保留、CRC OK、COM 真开、逐页渲染通过（均亮 155~190、无纯黑页）。
- `assets/motion-recipes.json` 把 011–015 标为 `route: template-clone`；
  `apply_effect_unit.py` 对这 5 条明确报错指路，不再用 v9.0.7 那两个简化注入器。
- **教训**：结构验收（能打开/CRC/备注保留）≠ 效果验收。自写占位形状能骗过结构检查，
  但用户一眼看出「加了没效果」。同一类错误在药安管家 PPT 已犯过一次。

#### v9.0.7 执行层适配（2026-11-12，补上「列得出 → 用得上」）
上一版只把 15 条列进菜单，新增 5 条在执行脚本里没有落点。本版补齐：
- `scripts/apply_motion.py`：15 条全给明确落点——`conditional`（11/13）打印素材条件、
  `unit_kind=B/C`（12/14/15）提示还需 `apply_effect_unit.py` 注入动画单元、
  `equivalent`/`False` 明确报错；`effect=none` 的配方跳过转场写入。
- `scripts/apply_effect_unit.py`：分发逻辑从**硬编码 4 个 id** 改为读 `assets/motion-recipes.json`
  **数据驱动**；新增 `unit_B_spec`（从 `spec.json` 的 `hexagon.p1/p2` 读几何，注入 2 态 morph 页）
  与 `unit_C_spec`（从 `spec.animation.motion.path` 读 `animMotion`，注入单页路径动画），
  新 12/14/15 全部有可执行落点；`--list` 列出 15 条全落点。
- **真跑验证**（`C:/Temp/dsh_ascii`，纯 ASCII 路径逐个隔离 COM）：
  `apply_motion` 效果11/12/13/14/15 产物 15 页真开通过；
  新注入器 效果12/14 产物 17 页、效果15 产物 16 页真开通过，备注/图表/媒体/CRC 全部保留。
- **修掉一个真 bug**：两个脚本原先把 `p:transition` 追加到 `</p:sld>` 前，
  违反 OOXML 顺序（`cSld → clrMapOvr → transition → timing`），会让 PowerPoint 拒绝打开。
  现统一插到 `<p:clrMapOvr>` 之前。
- **验证纪律（踩过的坑）**：PowerPoint COM **打不开含中文文件名的路径**，
  报 `-2147024894`（文件未找到），极易误判成「产物损坏」。COM 真开必须先用
  **纯 ASCII 文件名、逐个隔离新进程**；`Slide.Export` 另需可写目录，失败不代表文件坏。

# 6c. 【v9.0.4】主链出稿后叠加动效内核（overlay 模式；不换链/不加页）
python scripts/apply_motion.py --in output/deck.pptx --out output/final.pptx --recipe 效果5
python scripts/apply_motion.py --in output/final.pptx --verify
python scripts/apply_motion.py --in output/deck.pptx --restore   # 回退
# 6d. 【v9.0.5 / v9.0.7】效果 2/4/6/7：注入动画单元（形变对象 / 页内 timing），15 条全部可用
python scripts/apply_effect_unit.py --list
python scripts/apply_effect_unit.py --in output/deck.pptx --out output/final.pptx --effect 效果7
# 6e. 【v9.0.6】素材体检 / 动画素材库 / 用户模板索引
python scripts/check_assets.py
python scripts/build_animation_library.py
python scripts/index_user_templates.py
python scripts/build_layout_library.py            # 生成常见布局特征库
python scripts/check_layout_similarity.py --plan output/plan.json --candidate A --strict
# 6f. 【v9.0.6】工作区素材按类别/人物线索检索（封面人物替换法第 3、4 步用）
python scripts/find_asset.py --kind ppt_asset 传承人
python scripts/find_asset.py --kind ppt_asset 乡村振兴

# 7. 校验页面计划（字段/坐标/卡片/图标/模板/预算/导航/备注/风格理由/动效代号）
python scripts/validate_plan.py output/plan.json --knowledge knowledge

# 8. 素材：配图（一级生图 → 二级图库 → 三级纯色）
node scripts/generate_images.js --plan output/plan.json --candidate A --emit output/image_requests.json
node scripts/generate_images.js --plan output/plan.json --candidate A --fill output/images
#    视觉特效素材
node scripts/generate_effects.js --plan output/plan.json --candidate A --emit output/effect_requests.json
node scripts/generate_effects.js --plan output/plan.json --candidate A --fill output/effects
#    免费图库（生图失败时的二级降级）
node scripts/search_photos.js --plan output/plan.json --candidate A --fill output/photos

# 9. 构建 PPTX（母版 + 章节导航 + 原生对象 + 备注）
node scripts/build_pptx.js --plan output/plan.json --candidate A --out output/deck.pptx

# 11. 排版静态检测（不启动 PowerPoint、不调 COM）+ 自我评分
python scripts/detect_layout.py output/deck.pptx --config assets/config.json --out output/check_report.md
python scripts/score_deck.py --plan output/plan.json --candidate A --deck output/deck.pptx
#    <75 分 → 按 rewrite_weakest_n 重写最弱页，最多 max_rewrite_rounds 轮
```

- `parse_source.py`：只抽取结构与文字，不做总结；扫描件走图像识读并标注校对状态。
- `find_style.py`：按内容关键词/明暗偏好检索风格库，输出候选与配色摘要；**无命中时明确提示"不要回落默认"**。
- `extract_style.py`：从 `.pptx/.pdf` 提取配色、字体、字号与版式信号，生成可调用的视觉系统 JSON + 风格卡片；支持 `--batch` 批量入库。
- `validate_plan.py`：字段/枚举/坐标/卡片与图标存在性/布局模板 zone/生图与特效预算/导航章节对应/备注要求/**视觉系统与 style_rationale 必填**。
- `generate_images.js`：筛 `image_required` 页，按视觉系统拼 prompt；`--emit` 出清单，`--fill` 回填 `image_path`；生图失败自动尝试图库，再退纯色。
- `generate_effects.js`：按 `assets/effect-templates/` 生成装饰素材清单并回填 `effect_path`。
- `search_photos.js`：调用免费图库，写入来源与授权记录。
- `build_pptx.js`：母版 + 导航 + 原生形状/图表/表格/图标；**视觉系统缺失或不存在直接报错退出（不回落默认）**；图片或特效缺失时降级，不中断。
- `detect_layout.py`：静态解析 `.pptx` XML，检测越界/溢出/遮挡/字体白名单/字号/备注缺失/图片降级，输出 Markdown 报告。
- `score_deck.py`：生成后自我评分（0–100）与最弱页定位，分项含结构完整(15)/原生深度(15)/排版质量(15)/视觉层级(10)/叙事与正文(10)/密度模式(10)/参考依据(5)/**国赛对齐度(20)**；国赛对齐度按 `config.json:gsl_alignment.targets` 量产物并逐项输出差距（形/页、组/页、图/页、色数/页、封面章节页最大字号、字号跨度）；低于 `config.json:scoring.pass_score`（默认 75）时给出重写清单（默认重写 3 页、最多 2 轮）。
- `analyze_reference.py`：参考稿逐份拆解（页面结构、元素与图层、配色字号）并映射到设计卡片，产出 `knowledge/reference_library/`；支持 `--ref-dir assets/sample-ppts`。

## 9. 目录速览

```
smart-ppt-designer/
├── SKILL.md                      ├── references/（26 篇）        ├── scripts/（11 个）
├── assets/                       │   ├── visual-systems/（10 内置 + 9 提取）
│   ├── layout-templates/（6 套）  ├── decoration-sets/（9 组）    ├── target-cases/（8 图 + 10 条共性）
│   ├── style-cards/（15 张）      ├── icon-library/（64 图标）     ├── template-library/（4 套）
│   ├── personal-styles/          ├── effect-templates/（4 套）   ├── sample-ppts/ + templates/references/
│   └── config.json / page-plan-template.json / pptxgenjs-config.js / image-styles.json / style-index.json
├── knowledge/（卡片 13 张 / 失效案例 / 品牌模板 / 参考稿实测库 / 目标案例）
├── examples/  ├── integrations/（3）  └── output/（运行时产物）
```

## 10. 交付与自检

交付给用户：`.pptx`（原生可编辑，含母版、导航、备注）+ `check_report.md` + A/B 两套页面计划与理由 + **风格来源说明（检索/提取/用户指定 + `style_rationale`）** + 素材来源与降级说明 + **国赛对齐度自评（`score_deck.py` 的 `gsl_detail` 逐项差距）**。生成后按 `references/evaluation-rubric.md` 逐项自检，明确告知：风格怎么来的、哪些页配了图、是否降级、特效是否生效、检测出的问题与需要人工终审的点。**不要**声称已自动修复排版，也不要声称做出了"设计师级惊艳感"。