# 设计卡片库

卡片是"什么内容该用什么样的页面结构"的可检索知识单元。**检索靠 `relation_type` + 页面用途，不靠主题词**——所以这里没有"医疗""教育""金融"这类主题卡片，主题靠内容与卡片的"适用条件"匹配。

## 一、现有卡片（11 张）

| 卡片 ID | 名称 | `relation_type` | 什么时候用 | 配套布局模板 |
|---|---|---|---|---|
| `cover-title` | 封面标题页 | 通用 | 封面、章节过渡页 | `cover-full-image` |
| `layout-sidebar-nav` | 侧边栏导航页 | 通用 | 内页高密度多模块（2–4 模块），章节 ≥ 3 | `sidebar-nav` |
| `layout-four-grid` | 四宫格并列 | 并列 | 恰好 4 个平级模块 | `four-grid` |
| `layout-data-dash` | 数据仪表盘页 | 比较 | 指标卡 + 图表 + 明细表同屏 | `data-dashboard` |
| `layout-two-column` | 双栏并列 | 并列 | **恰好 2 个**平级对象 | `sidebar-nav` / `four-grid` |
| `comparison-matrix` | 多对象对比矩阵 | 比较 | 3 个及以上对象，或 2 对象 × ≥3 维度 | `data-dashboard` |
| `timeline-horizontal` | 横向时间线 | 时间 | 3–6 个有真实先后的节点 | `sidebar-nav` |
| `hierarchy-tree` | 层级结构树 | 层级 | 上下级/包含关系，2–3 层 | `sidebar-nav` |
| `funnel-conversion` | 转化漏斗 | 因果 | 逐级收窄且每级有量化 | `data-dashboard` |
| `metric-highlight` | 关键指标强调页 | 通用 | 一页只钉一个关键数字 | `sidebar-nav` |
| `problem-solution` | 问题—方案对照 | 因果 | "因为某问题，所以某方案" | `sidebar-nav` |

`通用` 表示该卡片与信息关系类型无关（封面、单点强调、布局骨架），检索时不作为 `relation_type` 命中依据。

> 关于数量：规格列出的示例卡片是 8–10 张，实际保留了 11 张——多出的一张是 `comparison-matrix`，用于支撑验收项"**3 个竞品不会输出双栏**"（`layout-two-column` 的反例必须指向一个真实存在的替代卡片）。

## 二、怎么检索（工作流第 5 步）

1. 先读 `../fail_cases/`，把相近案例当本轮反例；
2. 按页面用途选**布局模板**（骨架）：`sidebar-nav` / `four-grid` / `data-dashboard` / `cover-full-image`；
3. 按 `relation_type` 与用途挑 **3–5 张卡片**（不是全读）；
4. 逐张核对"反例（禁止使用）"：命中就不许用；
5. 卡片与布局模板需要配套（见上表）：3 个对象不得用四宫格、单点数字不得用仪表盘。

## 三、格式规范

卡片格式（5 个必填字段、写作要求、校验方式）见 `../../references/card-spec.md`。摘要：

- frontmatter：`id`（与文件名一致）、`name`、`relation_type`（6 类之一或 `通用`）；
- 正文：**必须有「适用条件」与「反例（禁止使用）」两段**（红线：卡片不能只写外观描述）；
- 建议写全「结构描述」「元素与坐标」「变体」。

## 四、怎么新增 / 修改

1. **先写失效案例**（`../fail_cases/`），确认这是反复出现的问题；
2. 判断是"现有卡片边界不清"（→ 改那张卡片的适用条件/反例）还是"确实缺一种结构"（→ 新建卡片）；
3. 新建时复制最接近的卡片作骨架；布局类卡片用 `layout-*` 命名；
4. 跑一次校验：

```bash
python scripts/validate_plan.py output/plan.json --knowledge knowledge
```

5. 卡片总量控制在 **8–12 张**。库太大反而降低检索精度。

## 五、从示例看用法

`../../examples/example_page_plan.json` 是两套完整页面计划（A/B），每页都标了 `card_used` 与 `layout_template`，可直接对照本表理解"什么内容配什么结构 + 什么骨架"。