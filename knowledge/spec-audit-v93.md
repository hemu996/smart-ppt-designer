# 规格 v9.3 差距审计（2026-11-06）

对照《智能演示文稿生成系统 — 技能包设计规格》（文件头标 **v9.3 / 2026-11-06**，706 行）与当前包 **v9.0.1** 的逐条比对结果。
判定口径：**用户最新明确要求优先于规格原文**（冲突项分列第三节、第四节）。
本轮目标版本号：**v9.0.2**（用户指定）。

## 一、已对齐（无需动作）

| 规格要求（行号） | 当前状态 | 结论 |
|---|---|---|
| references 13 篇（L113–126） | 23 篇，规格列名全部存在 | ✅ 超集 |
| scripts 7 个（L128–135） | 12 个，规格列名全在 | ✅ 超集 |
| assets 资源（L137–161） | `config.json` / `page-plan-template.json` / `image-styles.json` / `pptxgenjs-config.js` / `visual-systems`（19 套）/ `template-library`（4 套）/ `effect-templates`（4 个 prompt：gold-calligraphy、glow-decor、pattern-border、tech-particles）/ `layout-templates`（sidebar-nav、four-grid、data-dashboard、cover-full-image）/ `icon-library`（64 个） | ✅ 全含 |
| knowledge/cards 10 张（L164–175） | 13 张，规格列名全含（含 layout-sidebar-nav / layout-four-grid / layout-data-dash / cover-title） | ✅ 超集 |
| reference_library 6 子目录（L283–296） | visual-systems / layout-patterns / element-stacking / cover-styles / decoration-elements / sample-ppts 全含 | ✅ |
| integrations 2 个（L181–183） | 3 个（另加 image-providers.md） | ✅ 超集 |
| examples 1 套（L185–190） | 5 项全含 | ✅ |
| 4 套规格视觉系统配色（L232–237） | 国潮红金 #8B0000/#D4AF37/#FFF8DC、科技深青 #004D40/#00BCD4、科技深蓝 #0D47A1/#2196F3/#FFC107、医疗科技白 #FFFFFF/#E3F2FD/#1565C0 | ✅ 与规格一致 |
| 图片蒙版效果（L461–464） | `visual-effects.md` L71：几何形状裁成圆形 / 竖条 / 波浪，遮罩法 + 与文字并排 | ✅ |
| 文字填充效果（L466–469） | `visual-effects.md` L72：生图产"带纹理 / 烫金文字 PNG"作 L4 标题层 | ✅ |
| 卡片动效（静态，L471–474） | 轻度投影 + 渐变边框，`card_style` 19/19 套齐备 | ✅ |
| 开场动画（可选，L476–485） | `visual-effects.md` L74/78–85：24 片扇形 + 起始帧清单 + 人机协作 4 步 + 未走完不计交付 | ✅ |
| 结尾页规范（L434–455） | `cover-design.md` §五：全屏背景图 + 左深右浅渐变蒙版 + 飞白书法 PNG + 标配 4 项 + ≥5 元素 | ✅ |
| 高级章节过渡页（L487–502） | 五要素齐备（全屏背景图 / 超大半透明编号 / 章节标题 / 一句话说明 / 装饰线）+ 4 条约束 | ✅ |
| 转场统一淡入、章节页可推进（L340–343 / L501） | `visual-system.md` L113、`visual-effects.md` L78、`cover-design.md` L61、`build_pptx.js` L75 四处一致 | ✅ |
| 12 列网格 + 间距 0.3cm 整数倍（L313–316） | `config.grid`：columns 12 / margin_cols 1 / unit_cm 0.3 | ✅ |
| 页脚规范（L318–321） | `config.footer`：左下项目名 / 右下页码，10–11pt 浅灰，位置固定 | ✅ |
| 视觉焦点 / 图标风格统一（L329–338） | 红线 17/18 + `visual-system.md` | ✅ |
| 数据卡片大字号（L504–512） | `metric-highlight` 卡片 + 密度模式 `min_metric_pt` | ✅ |
| 密度模式硬指标（L527–556） | `config.density_modes.vivid`：6–10 元素、≥2 层装饰、`images_per_content_page [1,2]`、`require_top_nav_label`、`forbid_flat_background`、`forbid_low_saturation`、`card_style` | ✅ |
| 红线 1–22（L609–643） | 已扩至 27 条，规格 1–22 逐条覆盖；红线 9（烫金改生图 PNG）、26（构图两硬约束）、27（去 AI 感与对齐纪律） | ✅ 超集 |
| 验收 38 行（L649–688） | 已扩至 54 项，规格各行逐条覆盖 | ✅ 超集 |
| 工作流十三步（L516–603） | `workflow.md` 第 1–13 步（含第 8 步样张确认 ≤3 次、生图前搜参考图） | ✅ |
| 书法 5 型（L420–426） | 飞白默认在 `effect-templates/gold-calligraphy.json`，五型齐备 | ✅ |
| 模板套用 ≥70% 替换（L382–389） | `evaluation-rubric.md` 第 13 项 + `template-library/_README.md` | ✅ |
| 三级降级（L631） | 红线 15 + `image-strategy.md` | ✅ |

## 二、真实缺口（本轮落地，共 6 项）

| # | 规格要求（行号） | 当前状态 | 缺口 | 落地点 |
|---|---|---|---|---|
| 1 | **视觉母题规则**（L258–266）：初始化选 3–5 种装饰性母题，1 主 + 2–4 次；只约束装饰元素、不约束内容元素；不同页可用不同组合；母题面积 ≤ 页面 1/5 | 无此规范（`gsl-alignment.md` L57 的"一页一母题"指封面信息构成，非母题体系） | 缺规范、缺 config 段、缺校验 | 新建 `references/visual-motifs.md` + `config.visual_motifs` + `validate_plan.py` 校验 + SKILL/design-brief 引用 |
| 2 | **模板校验兜底**（L663）：AI 自由生成布局 → 自动校验是否接近素材库 10 份 PPT（150+ 页）提炼的 30–50 种常见布局 → 太奇怪/太乱则退回最接近的布局 | 无布局合理性校验，也无"常见布局特征库" | 缺布局特征库 + 缺校验与退回机制 | 新建 `assets/layout-patterns/`（或扩充 `knowledge/reference_library/layout-patterns/`）+ `scripts/check_layout_similarity.py` + validate/SKILL/workflow 接入 |
| 3 | **评分重写口径与审核维度**（L668）：低于 75 分重写最弱 **1–2 页**、最多 2 轮；审核维度 = 视觉 AI 味 / 内容 AI 味 / 布局混乱 / 元素太少 | `config.scoring.rewrite_weakest_n = 3`；四维度未作为显式审核维度输出 | 口径不符 + 缺四维度 | `config.scoring` + `scripts/score_deck.py` + `evaluation-rubric.md` 第 18 项 |
| 4 | **烫金字实现细则**（L619–625）：适用场景（仅封面大标题、章节过渡页大标题）/ 禁止场景（正文、图表标注、页脚）/ 金箔要求（细腻不强反光、一套用同一张）/ 搭配要求（仅深色背景）/ 字体要求（粗体或书法体优先） | `visual-effects.md` 有"特效只作装饰层""gold-calligraphy 用于封面/章节页 ≤1"，但上述 5 条细则未成文 | 缺 5 条细则 | `references/visual-effects.md` |
| 5 | **素材库调用规则二分**（L253–256）：❌ 必须锁死 = 配色 / 字体 / 装饰元素风格 / 图标风格；✅ 可灵活 = 页面布局 / 元素堆叠方式 / 信息层级 | SKILL 有"风格不设默认""不设默认"，缺这条明确的锁死/灵活二分 | 缺明确表述 | `SKILL.md`（素材库调用总表附近） |
| 6 | **字号区间**（L305–311）：H1 36–44 / H2 28–32 / H3 20–24 / H4 16–18 / Body **12–14** / Caption **10–11** / Metric **36–60** | `config.fonts`：`body_pt 16`、`caption_pt 12`；Metric 40–60 | 三处区间不一致（Body / Caption / Metric 下限） | `config.fonts` + `evaluation-rubric.md` 第 3 项 + `validate_plan.py` 下限 |

## 三、规格自身内部冲突（取用依据已标注）

| 冲突 | 规格两处原文 | 取用 |
|---|---|---|
| 重写页数 | 五、工作流第 11 步（L577）："重写最弱的 **3** 个页面" ↔ 七、验收表（L668）："重写最弱的 **1–2** 页" | **取验收表口径（1–2 页，默认 2）**：验收表更明确且为更新表述；保留 `config.scoring` 可配置，正文冲突写进本审计 |
| scripts 数量 | 三、目录结构列 **7** 个（L128–135） ↔ 八、交付物清单写"**6** 个 scripts"（L697） | 包内 12 个为超集，两处均可覆盖，不阻塞 |
| 工作流编号重复 | L516–585 十三步（含第 7–12 步）↔ L586–603 再次出现第 7–11 步（8a–8d 细分） | 按"十三步为主线、素材生成细分为 8a–8d"合并理解；包内 `workflow.md` 第 9 步已含 8a/9a 标注 |
| 4.4.x 编号重复 | L434「4.4.1 结尾页」↔ L487「4.4.1 高级章节过渡页」 | 编号笔误，两节内容均落地，不影响 |

## 四、与用户既有口径的冲突（用户优先）

| # | 规格原文 | 用户口径 | 取用与现状 |
|---|---|---|---|
| 1 | 红线 12："✅ 必须有章节导航，内页统一用母版导航栏"（L628）；4.2"参考图里几乎每页都有"（L347） | "左边的侧边栏不要每页都有"；"导航做成制作期开关"；"默认值改成关闭" | **取用户口径**：`navigation_enabled` 总开关（默认关闭）+ `sparse` 稀疏 + 逐页覆盖；SKILL 红线 12 已改写 |
| 2 | L541–543"禁止元素倾斜/穿插；所有元素必须水平/垂直对齐" | "每页 ≥2 个元素前后叠压（z_index 不同且几何重叠）" | **两者可共存**：水平/垂直对齐约束的是"倾斜与乱摆"，与 z 序叠压不是同一维度；包内红线 26（叠压）+ 27（禁止倾斜，贴纸类装饰 ≤12°）已调和 |
| 3 | 红线 7："必须调用 DSH 内置 `dsh.image`"（L615） | 实测本会话 `dsh.image` 不可用 | **保留 dsh.image 为一等入口**；不可用时降级到会话内生图技能，并在构建与计划中留痕（`integrations/image-providers.md`） |

## 五、本轮落地顺序（对应 Todo 57–61）

1. 视觉母题规则（缺口 1）
2. 模板校验兜底（缺口 2）
3. 评分重写口径与四审核维度（缺口 3）
4. 烫金字细则 + 素材库调用规则二分 + 字号区间对齐（缺口 4/5/6）
5. 版本升 **v9.0.2**、回归、重打包、同步安装目录并交付

## 六、落地闭环记录（2026-11-06，v9.0.2）

| 缺口 | 落地结果 | 取证 |
|---|---|---|
| 1 视觉母题规则 | 新建 `references/visual-motifs.md`；`config.visual_motifs`（3–5 种、1 主 + 2–4 次、面积 ≤ 1/5、只约束装饰元素）；`validate_plan.py` 结构/名单/面积三级校验（未声明给 info）；SKILL 素材总表与专段、design-brief 第 10 项、workflow 第 2 步同步 | 合规计划 error 0；数量越界 / 主母题非 1 / 未登记母题 / 面积超 1/5 四类违规均按预期报 error |
| 2 模板校验兜底 | 新建 `assets/layout-patterns/common-layouts.json`（35 条：样本提炼 25 + 包内补 10）与 `scripts/build_layout_library.py`（可复现刷新）、`scripts/check_layout_similarity.py`（命中 / 样本未覆盖但包内合法 / 偏离 + 退回建议 + `--fix` 自动改判）；`config.layout_fallback`；validate 对元素量极端偏离给 warn；SKILL 与 workflow 第 7b 步写明 | 示例稿 A/B 偏离 0.0%（零误报）；构造「AI 自创布局」与「200 元素过密」两类页面均被判偏离并由 `--fix` 退回；validate 对过密页给出兜底 warn |
| 3 评分重写口径与四维度 | `config.scoring.rewrite_weakest_n` 3 → **2**（验收表口径，正文冲突已在 §三 标注）；`score_deck.py` 新增 `review_dimensions` 四维度（视觉 AI 味 / 内容 AI 味 / 布局混乱 / 元素太少）；rubric 第 18 项、SKILL 流程图第 11 步与脚本注释同步 | 评分输出含四维度；最弱页按 2 页输出；回归 score 92.4–92.5 达标 |
| 4 烫金字实现细则 | `references/visual-effects.md` §九：适用场景仅封面 / 章节大标题、禁止正文 / 图表标注 / 页脚、金箔细腻不强反光且全份同一张、仅深色背景、粗体或书法体优先 + 5 项自检 | 规范文本已落地并复核 |
| 5 素材库调用规则二分 | SKILL 增「锁死（配色 / 字体 / 装饰风格 / 图标风格）vs 灵活（布局 / 堆叠 / 层级）」段 | SKILL 文本已落地 |
| 6 字号区间 | 19 套视觉系统 `body_size` [13,15]→[12,14]、`metric_size` [40,60]→[36,60]（caption 已是 [10,11]）；`config.fonts` body_pt 16→14、caption_pt 12→11；rubric 第 3 项、示例计划越界字号 18 处同步 | 19/19 套区间与规格一致；回归 validate error 0 |

**版本**：包升 **v9.0.2**（SKILL 标题 / README / 目录统计同步：references 24 篇、scripts 14 个、验收 56 项）。
**回归**：`validate_plan` error 0 / `build_pptx` rc=0 / `detect_layout` error 0 / `score_deck` 92.5 达标。
**冲突处理**：§三（规格内部冲突）与 §四（与用户口径冲突）均按标注的取用依据执行；导航按用户口径（默认关闭 + 稀疏 + 可关）。
