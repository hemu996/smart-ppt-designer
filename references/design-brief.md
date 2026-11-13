# 设计规范确认清单（生成前必做）

第 2 步"设计规范确认"的作业指引。**这一步没做完，不要进第 6 步写页面计划**——先定风格再排版，返工代价最大。

## 一、必须确认的 10 项

| # | 项目 | 取值来源 | 不确定时怎么办 |
|---|---|---|---|
| 1 | 沟通目的 | 简报里的"希望对方做什么" | 素材里读不出来就问用户一句 |
| 2 | 信息关系（主关系） | 内容主体之间的关系 | 同上；决定主卡片检索方向 |
| 3 | 受众与场合 | 简报 / 用户说明 | 默认"评委/领导 + 投影现场" |
| 4 | 视觉系统（从风格库检索选定，或从参考稿提取） | `assets/style-index.json` + `assets/visual-systems/` | **不设默认**：先 `python scripts/find_style.py <内容关键词>` 检索候选；无命中就按内容推导、或先问用户一句；选完必须写明 `style_rationale` |
| 5 | 导航方式 | 侧边栏（默认）/ 顶部 | 页数 ≥ 12 时用侧边栏；≤ 8 页可用顶部 |
| 6 | 页数区间 | 汇报时长（≈1.5–2 分钟/页） | 10 分钟路演 → 12–16 页 |
| 7 | 生图预算 | 3–5 张（红线第 6 条） | 封面必 1 张，章节页每 4–6 页 1 张，概念页 ≤ 2 张 |
| 8 | 创意度档位（v8.9） | `assets/config.json` 的 `creative_level`：`off` / `conservative` / `balanced` / `expressive` | **默认 `off`，与既有行为完全一致**；想更有设计感再逐档上调。档位只影响三处：① 内容页装饰组上下限 ② 卡片圆角 ③ 构建日志里的档位追溯。不改配色与字体 |
| 9 | 章节导航开关（v9.0） | 计划 `design_brief.navigation_enabled`（要不要做） | **默认关闭**：包级 `config.navigation.enabled = false`，计划里不写 `navigation_enabled` 即关闭；要开**必须显式写 `true`**（写 `false` 等价于默认）；要做再选范围 `navigation_scope`（`full` / `sparse`（默认，每章首个内容页）/ `none`），逐页可用 `slides[].show_navigation` 覆盖 |
| 10 | 视觉母题（v9.0.2） | 计划 `design_brief.visual_motifs`：3–5 种装饰性母题（1 主 + 2–4 次） | **不设默认**：从内容推导（如茶产业 → 茶芽 / 叶脉 / 茶渍纹）并写明来源；只约束装饰元素，面积 ≤ 页面 1/5；规则见 `references/visual-motifs.md` |
| 12 | 模板生成模式（v9.0.6 合入） | `design_brief.template_mode`（`free` 自由生成 / `fill` 模板填充） | **默认 `free`**；生成前先问用户。选 fill 先读 `assets/user-templates/index.json` 挑 2–3 份候选给用户定，再问封面字体「保持原样 / 升级书法烫金」；**红线 28 封面 AI 书法强制仍生效**。流程见 `references/user-templates.md` |
| 13 | 动画开关（v9.0.6 合入） | `design_brief.animation_mode`（`none` / `basic` 默认 / `advanced`） | **先问要不要加动画**；动画取自 `assets/animations/animations.json`（43 种）。**本机适配**：每页 ≤5 个动画元素、同页风格统一、禁夸张，且**不要逐元素排队淡入**（用户明确嫌过"一个个顺序出现太久"）——优先整页一次性或只点结论 |

## 二、确认结果的落点

全部写进页面计划的 `design_brief` 段（见 `page-plan-schema.md`）：

```json
"design_brief": {
  "visual_system": "ref-tea-green",
  "style_rationale": "内容为茶产业振兴方案，按关键词检索命中 ref-tea-green（茶绿清雅），取自参考稿 茶产业振兴.pptx，与主题一致",
  "navigation_mode": "sidebar",
  "sections": ["背景与缺口", "方案设计", "试点验证", "落地路径"],
  "page_count_target": 14,
  "image_budget": 4,
  "effect_budget": 2,
  "creative_level": "off",
  "navigation_enabled": false,
  "navigation_scope": "sparse",
}
```

- `navigation_enabled`（v9.0）：章节导航总开关。**制作前先问用户要不要**；**默认关闭**（包级 `config.navigation.enabled = false`）：计划级缺省即关闭，要开**必须显式写 `true`**；`false` = 全篇不画（母版侧栏底板同样不画）。优先级：逐页 `show_navigation` > 本开关 > `navigation_scope`。
- `navigation_scope`（v9.0）：`full`（非封面页都画）/ `sparse`（默认，只画每章首个内容页）/ `none`；章节过渡页不画（左侧留给 `section-rail` 装饰轨道）。

- `creative_level`（v8.9）：创意度开关，默认 `off`；`balanced` / `expressive` 会放宽本页装饰组上限并加大卡片圆角，构建日志会打印实际生效档位。

- `sections` 决定导航栏的章节条目与每页的高亮归属，**必须与内页 `section_name` 一一对应**；
- `page_count_target` 与 `meta.slide_count` 相差超过 30% 时要在 `rationale` 里说明；
- `effect_budget` 指烫金标题/发光装饰/纹样边框/粒子背景这类**装饰素材**张数（默认 ≤ 3）。

## 三、从已有 PPT 提取风格（模板复用）

用户提供参考 PPT/参考稿时：

1. 用 `scripts/parse_source.py` 或视觉观察提取：主色/辅色/强调色、标题与正文字体、字号区间、标题装饰形式（色块 / 竖条 / 印章）、导航形式；
2. 写入 `assets/visual-systems/` 下的自定义系统文件（`custom-*.json`），字段结构照抄现有 4 套；
3. **只提取可复用的"规范"，不复用原稿的文案与结论**；
4. 提取结果与原稿有明显冲突时（例如原稿三种蓝色混用），取其中最接近规范的一套并说明。

## 四、确认清单（勾完再进第 3 步）

- [ ] 沟通目的、主关系、受众三项已明确
- [ ] 视觉系统已选定（内置 / 参考稿提取 / 用户指定），文件存在，且 `style_rationale` 已写明理由（无默认回落）
- [ ] 导航方式与章节列表已定，章节数与内容分段一致
- [ ] 视觉母题已按内容选定 3–5 种（1 主 + 2–4 次）并写入 `visual_motifs`，**不设默认**
- [ ] 章节导航**要不要**已问过用户（**默认关闭**）：要开必须显式写 `navigation_enabled: true`（不写即关闭，含母版侧栏底板）；要开时写明 `navigation_scope`（`full` / `sparse` / `none`）
- [ ] 页数区间与生图/效果预算已定
- [ ] 字号区间取自视觉系统 `fonts`，没有自造字号
- [ ] 所有固定取值的来源都能说清（用户说的 / 简报写的 / 视觉系统定义的），没有"我觉得"