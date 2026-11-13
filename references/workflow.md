# 完整工作流（十一步）

`SKILL.md` 第 5 节的展开版。**不要跳步**：每一步都有明确产出，产出不合格就停在那一步修，带着缺陷往下走会成倍返工。

## 第 1 步：材料解析

```bash
python scripts/parse_source.py --input 材料.pdf --out output/source.md
```

- 输入可以是文本/PDF/DOCX/HTML/已有 PPT；解析只做抽取，不做总结；
- 产出三样：核心论点 3–5 条、关键数据表（带口径）、素材缺口清单；
- 口径缺失的数据不许进 PPT（详见 `source-ingestion.md`）。

## 第 2 步：设计规范确认

按 `design-brief.md` 的 **13 项**确认：沟通目的、信息关系、受众与场合、视觉系统、导航方式、页数区间、生图/特效预算、创意度档位、**章节导航开关（要不要）**、**视觉母题（3–5 种，1 主 + 2–4 次）**、**动效配方任选一条**、**模板生成模式（自由生成 / 模板填充，默认 free）**、**动画开关（none / basic 默认 / advanced）**。



产出写入页面计划的 `design_brief` 段。**章节列表 `sections` 必须与内页的 `section_name` 一一对应**——导航高亮就靠这个对齐。

## 第 3 步：意图识别

```json
"brief_intent": {
  "communication_goal": "说服",
  "relation_type": "比较",
  "audience": "竞赛评委（5 人，熟悉行业）",
  "style_preference": "business"
}
```

`relation_type` 是选卡片的唯一依据，判断不了就问用户，不要默认"并列"。

## 第 4 步：确定视觉系统

从 `assets/visual-systems/` 选一套（商务蓝 / 科技深青 / 国潮棕金 / 人文暖色），或按 `design-brief.md` 第四节从参考稿提取一套自定义系统。

选定后：整份 PPT 的配色、字体、字号区间、装饰形式、图表调色板**全部从这一套取值**（红线第 5、13 条）。

## 第 5 步：检索布局模板 + 设计卡片

1. 先读 `knowledge/fail_cases/`（除 `_README.md`），把相近案例当本轮反例；
2. 按页面用途选布局模板（`layout-templates.md` 的四个模板）；
3. 按 `relation_type` 与页面用途挑 **3–5 张**卡片（不是全读）；
4. 逐张核对卡片"反例（禁止使用）"段，命中就不许用。

产出：本轮布局模板 + 卡片清单，各附一句选择理由。

## 第 6 步：生成双候选页面计划

每套方案给出：

- 每页 `slide_id` / `slide_type` / `section_name` / `layout_template` / `card_used` / `claim`；
- 需要配图的页：`image_required` / `image_type` / `image_prompt`；
- 需要特效的页：`effects[]`（模板名 + 位置 + prompt 参数）；
- 每页 `notes`（讲者备注四段式，不得为空）；
- 每页 `elements[]`（文本/形状/图表/表格/图标/图片/公式）；
- 每套方案开头 `rationale`：适合什么场合、代价是什么；
- 计划里写明 `design_brief.creative_level`（创意度档位，v8.9）：默认 `off` 与既有行为一致；`balanced` / `expressive` 会放宽装饰组上限并加大卡片圆角，构建日志打印实际档位，`validate_plan.py` 按档位判定装饰组上下限。
- 每页必须满足构图两硬约束（`references/composition.md`，v8.9，校验器 error 级）：① 每页 ≥1 个占比 ≥1/3 的超大元素 ② 每页 ≥2 个元素前后叠压（≥1 对，z_index 不同且几何重叠 >0.15in²）。第 3 条「错落感」经确认不启用；
- 导航开关与范围（v9.0）：**先问用户"要不要章节导航"**。**默认关闭**——包级 `config.navigation.enabled = false`，计划里不写 `navigation_enabled` 即关闭；**要开必须显式写 `design_brief.navigation_enabled: true`**，再选 `navigation_scope` = `full` / `sparse`（默认，只画每章首个内容页）/ `none`；逐页 `slides[].show_navigation`（布尔）优先级最高。章节过渡页**不画**导航（左侧留给 section-rail 装饰轨道，画了会重叠报错），封面 / 目录 / 结尾页同样不画。

**两套方案的差异必须落在结构上**（布局与顺序），只改配色措辞不算两套。字段定义见 `page-plan-schema.md`。

## 第 7 步：校验页面计划

```bash
python scripts/validate_plan.py output/plan.json --knowledge knowledge
```

校验：必填字段、枚举、坐标、卡片与图标存在性、布局模板 zone、生图与特效预算、导航章节对应、备注非空、A/B 两套结构不同。**有 error 必须改，不要绕过校验去构建**；warning 逐条说明后可保留。

**7b 模板校验兜底（v9.0.2）**：

```bash
python scripts/check_layout_similarity.py --plan output/plan.json --candidate A
python scripts/check_layout_similarity.py --plan output/plan.json --candidate A --fix --out output/plan_fallback.json
```

- 命中常见布局 → 通过；「样本未覆盖但包内合法」→ 可接受（仅提示）；
- 「偏离」→ 按建议退回最接近布局（`--fix` 自动改判 `card_used` / `layout_template`），改判后重跑第 7 步校验；
- 布局库由 `python scripts/build_layout_library.py` 从素材库样本刷新，新增样本后应重建。


## 第 8 步：样张确认（封面先出 1 页）

先只生成 **第 1 页封面**（含背景大图 + 大标题 + 信息行）交用户确认风格 / 配色 / 布局：

- 用户确认 → 进入第 9 步批量生成素材；
- 用户不满意 → 调视觉系统 / 布局后**重新出样张，最多 3 次**；
- 留痕：样张文件与确认结论写进 `output/sample_confirm.md`，作为验收第 14 项的取证。

## 第 9 步：素材生成

**8a / 9a（生图前先搜参考图；规格编号 8a）**：按主题关键词用 `scripts/search_photos.js` 搜 Pexels / Pixabay，把命中图的风格结论（色调 / 构图 / 光位）写进生图 prompt 后再调用生图——依据见 `integrations/dsh-image.md`。

```bash
# 配图（一级生图 → 二级图库 → 三级纯色）
node scripts/generate_images.js --plan output/plan.json --candidate A --emit output/image_requests.json
node scripts/generate_images.js --plan output/plan.json --candidate A --fill output/images
node scripts/search_photos.js  --plan output/plan.json --candidate A --fill output/photos
# 视觉特效素材（烫金标题/发光装饰/纹样边框/粒子背景）
node scripts/generate_effects.js --plan output/plan.json --candidate A --emit output/effect_requests.json
node scripts/generate_effects.js --plan output/plan.json --candidate A --fill output/effects
```

- 生图预算 3–5 张；特效预算 ≤ 3（单页 ≤ 1）；
- 生图失败：重试 2 次 → 图库 → 纯色背景，**不中断**；
- 特效透明底生成失败按失败处理，改用原生降级实现。

## 第 10 步：构建 PPTX

```bash
node scripts/build_pptx.js --plan output/plan.json --candidate A --out output/deck.pptx
```

构建要求（详见 `native-objects.md`）：

- 用 `defineSlideMaster` 定义 COVER / SECTION / CONTENT_NAV / DATA / CLOSING 五个母版；
- 内页从 `CONTENT_NAV`/`DATA` 版式生成，**章节导航内置于母版**，当前章高亮；
- 图表 `addChart`（原生、带数据源）、表格 `addTable`、图标用形状组合、公式用 Unicode 原生文本；
- **每页写讲者备注**；
- 图片/特效缺失时降级为纯色/原生装饰，不中断。

## 第 10.5 步：出稿后叠加（可选，用户选了才做）

**这一步不换链、不加页、不改版式**，只把用户第 2 步选定的能力叠到 `output/deck.pptx` 上，产出 `output/final.pptx`。顺序固定，**没选就整步跳过**。

| 用户第 2 步选了 | 动作 | 命令 |
|---|---|---|
| 效果 8（纯矢量） | 本包淡入 + Morph 已等价覆盖 | 无需额外脚本，交付说明写清 |

配套调用时机（不单列成步）：
- **素材检索**：第 5 步「检索布局模板」与第 9 步「素材生成」之前，先跑 `python scripts/find_asset.py --kind ppt_asset <关键词>`，在 `assets/ppt-assets-catalog.json` 找同类别同级别的现成素材，找不到才生成。
- **封面人物形象不对**（模板封面里的人不是我们的人）：第 8 步样张确认时按 `references/cover-persona-swap.md` 五步法处理（读图 → 拆描述 → 归类 → 类别文案生成 → 保同级效果），**不直接改 prompt 换人**。
- **模板填充 `template_mode=fill`**：按 `references/user-templates.md` 六步流程由模型执行（官方 `build_pptx.js` 不做自动填充），不在本步注入脚本。

> 硬规矩：以上全部**由用户自己选**，默认「不用」；★ 星级只是挑选参考，不是默认值，不许替用户挑、不许跳过问询。

## 第 11 步：排版检测

```bash
python scripts/detect_layout.py output/deck.pptx --config assets/config.json --out output/check_report.md
python scripts/detect_layout.py output/deck.pptx --json output/check_report.json
```

静态解析 XML（**不启动 PowerPoint、不调 COM**），检查：元素越界、文本溢出、遮挡、字体白名单、字号下限、备注缺失、图片/特效降级情况。报告按 `error / warning / info` 分级并定位到页与元素。

## 第 12 步：人工终审

| 情况 | 处理 |
|---|---|
| 严重结构错误（如 3 个竞品被排成双栏） | 按 `knowledge/fail_cases/_README.md` 写案例，**回第 6 步**重新构思 |
| 配图/特效不满意 | 只重生成该项：`generate_images.js --only-slide <id>` / `generate_effects.js --only-slide <id>` |
| 版式微调 | 用户手改 PPT；把可复用经验回写卡片或视觉系统 |
| 视觉美感不足 | 明确告知"这是模型上限"，列出建议人工打磨的 3–5 处，不要声称已达金奖水平 |

**回写是"越用越准"的唯一机制**：不回写，下次还会犯同一个错。

## 第 13 步之外：视觉复验（可选但推荐）

交付前把 PPTX 逐页渲染成图，按 `evaluation-rubric.md` 的呈现维度做一次视觉复核（层级/对齐/间距/留白/配色/可读性/遮挡/图表与图文关系/一致性）。本包的示例集就是这么复核出来的，首轮复核发现过"图表坐标轴显示无意义序号""两栏标题样式不对称""底部留白过大""白字对比度不足"等问题。