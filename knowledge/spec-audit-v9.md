# 规格 v9.0 差距审计（2026-11-05）

对照《智能演示文稿生成系统 — Skill Package 设计规格》（文件头标 v9.0 / 正文含 v5.0 表述，696 行）与当前包 **v8.9** 的逐条比对结果。
判定口径：**用户最新明确要求优先于规格原文**（冲突项单列在第三节）。

## 一、已对齐（无需动作）

| 规格要求 | 当前状态 | 结论 |
|---|---|---|
| references 12 篇（含 workflow / card-spec / page-plan-schema / design-brief / visual-system / layout-templates / cover-design / image-strategy / visual-effects / native-objects / source-ingestion / anti-patterns / evaluation-rubric） | 23 篇，规格列名 **全部存在** | ✅ 超集 |
| scripts 6 个（detect_layout / validate_plan / build_pptx / generate_images / generate_effects / search_photos / parse_source） | 11 个，规格列名全在（另加 analyze_reference / extract_style / find_style / find_asset / score_deck） | ✅ 超集 |
| 4 套视觉系统 + 配色 | `national-brown-gold` #8B0000/#D4AF37/#FFF8DC ✅、`tech-teal-green` #004D40/#00BCD4 ✅、`tech-deep-blue` #0D47A1/#FFC107 ✅、`medical-tech-white` #FFFFFF/#1565C0 ✅ | ✅ 主色一致（两处次色待校准，见 §二-4） |
| 4 种布局模板 | 6 个（sidebar-nav / four-grid / data-dashboard / cover-full-image 全在，另加 image-bleed / toc-number-grid） | ✅ 超集 |
| 图标库 50–100 个 | 64 个 | ✅ |
| 设计卡片 8–10 张 | 13 张，规格列出的 10 张**全部存在** | ✅ 超集 |
| examples 1 套 | `example_brief.md` / `example_check_report.md` / `example_from_pdf.pdf` / `example_generated_images/` / `example_page_plan.json` | ✅ 全含 |
| integrations 2 个（dsh-image / free-photos） | 3 个（另加 image-providers.md） | ✅ 超集 |
| knowledge/reference_library 6 个子目录 | visual-systems / layout-patterns / element-stacking / cover-styles / decoration-elements / sample-ppts | ✅ 全含 |
| template-library 4 套预置模板 | business-blue / humanities-warm / national-style / tech-dark 各 1 套 | ✅ 全含 |
| 红线 22 条 | 27 条，规格 1–22 **逐条覆盖** | ✅ 超集 |
| 验收标准 38 行 | 51 项，规格各行**逐条覆盖**（含"生图参考""样张确认""Q&A 预测""Bento 卡片"等） | ✅ 超集 |
| 密度模式硬指标（6–10 元素、≥1/3 超大元素、≥1 个大字号数据、1–2 张图、禁大面积纯白、装饰 ≤1/3） | 已落在 config.density_modes + 校验器 | ✅ |
| 字体层级 / 网格 / 页脚 / 图表配色 / 视觉焦点 / 图标风格统一 / 统一淡入转场 / 不用自定义动画 | 已落在 config + visual-system.md | ✅ |
| 封面（大图 + 大字 + 信息行 + 渐变蒙版 + 书法 PNG）/ 章节过渡页（五要素）/ 结尾页 / 数据卡片 | 已落在 cover-design.md + 校验器 | ✅ |
| 素材库调用规则（配色/字体/装饰/图标锁死，布局灵活） | 已落在 SKILL + visual-system.md；风格改为"按内容检索、不设默认"（用户要求） | ✅ 一致 |

## 二、缺口（需落地）

| # | 规格要求 | 当前状态 | 缺口 | 拟落地位置 | 成本 |
|---|---|---|---|---|---|
| 1 | **工作流十三步** | SKILL.md 工作流段**已含**第 8 步"样张确认"与 8a"生图前先搜网络参考图"；但详解文档 `workflow.md` 仍只有 **12 步**，未同步这两步（且 rubric 第 14 行指向"工作流第 8 步留痕"，正文里没有该步） | `workflow.md` 缺"第 8 步样张确认（含留存与最多 3 次）"与"8a 生图前搜参考图"两步详解 | `references/workflow.md` | 低 |
| 2 | **卡片精致度**（细金色/主题色边框 + 轻微投影 + 左上角序号带） | 20 套视觉系统里**仅 tech-gold-noir 有 `card_style`**，其余 19 套为 null | 19 套缺 card_style（首行序号带、投影、描边参数） | 各 `assets/visual-systems/*.json` 补 `card_style`（按明暗分别给默认值）+ `references/visual-system.md` 说明 | 中 |
| 3 | **背景不能纯白/纯平**（必须有渐变 / 纹理 / 淡纹样） | visual-system.md 无该强制项；config 无对应规则 | 缺"背景层要求"的口径与检查 | `config.json` 增 `background_rule`；`references/visual-system.md` 写做法（渐变底/淡纹样/网格纹理）；`validate_plan.py` 对"纯色平底"给提示 | 低 |
| 4 | 4 套规格视觉系统的**次色** | `tech-deep-blue.secondary = #08306E`（规格给 #2196F3）、`medical-tech-white.secondary = #0F314C`（规格给 #E3F2FD） | 次色与规格不一致 | 两套 json 的 secondary/accent 校准到规格值 | 低 |
| 5 | 版本号 **v9.0** | 当前 v8.9 | 版本号未升 | SKILL.md / README.md / 各处引用统一升 v9.0 | 低 |

## 三、与用户最新要求的冲突（按用户优先处理，已在包内标注）

| 规格原文 | 用户最新要求 | 处理方式 | 落点 |
|---|---|---|---|
| 4.2 / 红线 12："参考图里**几乎每页都有**导航栏""内页统一用母版导航栏" | "左边的侧边栏不要每页都有"；后又要求"导航做成制作期开关" | 取用户口径：`navigation_enabled` 总开关 + `navigation_scope` 默认 `sparse`（只画每章首个内容页）+ 逐页 `show_navigation` 覆盖；规范里把规格条目改写为"可用导航，默认稀疏" | SKILL 导航段、config.navigation、workflow、design-brief 第 8b 项 |
| 第 3 步硬指标："**禁止元素倾斜/穿插**：不能随便偏移、倾斜、**叠压**" | "每页至少 2 个元素前后叠压（不是平铺对齐）" | 取用户口径：**保留衬底式叠压**（背板在下、内容在上）；同时保留规格本意——**禁止随意倾斜与偏移**，倾斜仅限贴纸类手工装饰 ≤12°，正文/卡片/图片/图表/框架装饰/背板角度一律 0 | 红线 26/27、`references/composition.md` §二/§五 |
| 红线 7："**禁止自实现生图**，必须调用 dsh.image" | —（用户未反对，但本机 dsh.image 实测不可用） | 保留 dsh.image 为一等入口（`config.image.tool`），会话内生图技能作为已实测的降级路径，并在 `integrations/image-providers.md` 如实记录 | config.image、integrations |

## 四、后续落地清单（按成本排序）

1. workflow 补齐十三步（缺口 1，低）
2. 背景禁令与做法（缺口 3，低）
3. 两套视觉系统次色校准（缺口 4，低）
4. 版本升 v9.0 与文档同步（缺口 5，低）
5. 20 套视觉系统补 `card_style`（缺口 2，中）
6. 重打包技能包本体（不生成示例 PPT）

## 五、落地闭环记录（2026-11-05，v9.0）

| 缺口 | 落地结果 | 取证 |
|---|---|---|
| 1 工作流十三步 | `references/workflow.md` 已含第 1–13 步（第 8 步样张确认含留痕与 ≤3 次；生图前搜参考图标注为「8a / 9a，规格编号 8a」） | 步骤标题与第 8/9 步正文 |
| 2 卡片精致度 | 19 套视觉系统 **全部**含 `card_style`（细描边 + 轻微投影 + 左上角序号带参数） | 逐 json 核对：缺 `card_style` 0 套；构建日志「卡片精致度」行 |
| 3 背景禁令 | `config.json:background_rule` 已落（封面 / 章节 / 结尾页禁纯白纯平；`allowed_when` 仅生图与图库都不可用）；`visual-system.md` 写明渐变底 / 淡纹样 / 网格纹理做法 | config 段 + 规范章节 |
| 4 视觉系统次色 | `tech-deep-blue.secondary = #2196F3`、`medical-tech-white.secondary = #E3F2FD` 已按规格校准 | 逐 json 核对 |
| 5 版本 v9.0 | SKILL 标题 / README / 统计口径统一 v9.0；验收 51 → **54 项**（新增背景禁令、每页配图数量、顶部标签栏）；红线 **27 条** | 本轮回归 |
| 冲突 §三-1 导航 | `SKILL.md` 红线 12 已由「必须有章节导航，内页统一用母版导航栏」改写为「可用且可关（制作期总开关 + 默认稀疏 + 逐页覆盖）」；`evaluation-rubric.md` 第 27 项同步修订 | 本轮补丁 + 构建日志 |
| 冲突 §三-2 叠压 | 保留用户口径（每页 ≥2 个元素前后叠压），红线 26 明示「错落感不启用」 | SKILL 红线 26/27、`composition.md` §五 |
| 冲突 §三-3 dsh.image | 保留 dsh.image 为一等入口，实测不可用时降级到会话内生图技能并留痕 | `integrations/image-providers.md` |

**导航总开关（用户 2026-11-05 追加要求）**：`design_brief.navigation_enabled` 为制作期总开关，`false` 时全篇不画导航且**母版侧栏底板一并撤除**（`build_pptx.js` 的 `defineMasters` 现按计划级开关判定）；优先级 逐页 `show_navigation` > 总开关 > `navigation_scope` > 包级 `config.navigation.enabled`。取证：同一计划开 / 关两版构建，关闭版 `slideLayouts` 侧栏底板 2 处与导航条 18 处均归零，其余全高元素两版完全一致；构建日志「带栏 3/12 → 0/12」，校验 0 error。**2026-11-05 追加：开关默认值改为关闭**——包级 `config.navigation.enabled = false`，计划级缺省即关闭、要开必须显式写 `true`；示例计划 `output/plan_national.json` 已显式声明 `true` 以保留示例稿导航。同时修复同源缺陷：计划级开关现写回 `nav.enabled`，保证**母版侧栏底板与导航条目判定同源**——改默认前 `drawNavigation` 只读包级值，默认关闭后即使显式开启也只剩空底板。取证：未声明版 侧栏底板 0 / 导航条 0；显式开启版 底板 2 / 导航条 18；`validate_plan.py` 对未声明开关给 info 提示；回归 validate 0 error、detect 0 error、score 92.5。