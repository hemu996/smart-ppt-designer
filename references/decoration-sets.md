# 装饰组库与高阶版式配方（v8.7）

**一句话**：装饰组把"1 个计划元素"展开成"多个基础图元"，并在 PPTX 里包成**真实 `<p:grpSp>` 组**——这是本包把内页密度从 形/页 ≈18 拉到国赛区间（≥55）的主要手段，口径见 `gsl-alignment.md`。

## 一、为什么这样做（来自素材库实测）

参考稿的 形/页 在 53.5–122.9、组/页 在 2.6–31.5，做法是**基础图元拼版 + 组件整组复用**：大量 `rect / roundRect / ellipse / line / chevron` 构成页边距装饰、卡片、编号块，再整组搬到多页复用。本包此前每页只有十几个元素、装饰还是孤立单元素，所以密度差约 3 倍。

## 二、库结构

```
assets/decoration-sets/
├── index.json              # 索引（id / label / shape_count）
├── left-rail-geometry.json # 左侧竖轨几何（13 图元）
├── right-rail-ruler.json   # 右侧细线标尺（13）
├── top-rule-band.json      # 顶部规则带（14）
├── bottom-rule-band.json   # 底部规则带（12）
├── corner-ticks.json       # 四角刻线（12）
├── side-dots-grid.json     # 侧边点阵（14）
├── texture-mesh.json       # 网格纹理（14）
├── glow-orbs.json          # 光斑辉光（12）
└── section-rail.json       # 竖排章节标签轨道（11）
```

每组 12–14 个图元，只占**页边距**（外框 0–0.82in / 12.86–13.333in / y 0–0.26in / y 7.36–7.5in），不进入内容安全区。

## 三、在页面计划里怎么用

```json
{
  "type": "decoration_set",
  "role": "decoration",
  "set_id": "top-rule-band",
  "z_index": 10
}
```

规则：

1. `z_index` 必须是 **10–19（L2 装饰层）**，校验器会报 error；
2. `set_id` 必须存在于库中，校验器列出可选值；
2.1 `x_in / y_in / w_in / h_in` 填**该组的外框**（取组 JSON 里最小 `x/y` 与最大 `x+w / y+h`）——校验器据此查越界；装饰组位于页边距，**不参与版式 zone 检查**；
3. 每个**内容页 2–3 组**（`config.json:decoration_sets.sets_per_content_page`），封面上限放宽到 3–4 组；
4. 组合建议（按"左侧是否已有导航"区分，避免同区冲突）：
   - 左侧无导航时（`cover-full-image` 等版式）：`left-rail-geometry + top-rule-band + side-dots-grid`
   - **左侧有导航时（`sidebar-nav` 版式，本包默认导航）：不要用 `left-rail-geometry`**（会压住母版导航栏），
     改用 `right-rail-ruler + top-rule-band + bottom-rule-band`；校验器会对这种冲突给 warning
   - 数据页：`right-rail-ruler + top-rule-band + side-dots-grid`
   - 章节页 / 封面：`corner-ticks + right-rail-ruler + top-rule-band`
   - 结尾页：`corner-ticks + bottom-rule-band + side-dots-grid`
   - 装饰组内"底块 + 细线"叠压属正常分层：`detect_layout.py` 记为 info（装饰层内叠），不计遮挡 error
5. **装饰占比口径**：`纯装饰 ≤ 本页元素总数 1/3`（红线 19/20）只统计**点缀型装饰元素**（`role: decoration` 且非装饰组）；**装饰组不计入**该口径——它承担的是版面框架而不是点缀，改用**组数上限**约束：内容页 2–3 组、封面 / 章节 / 结尾页 3–4 组（`config.json:decoration_sets.sets_per_content_page`，超出上限校验器给 warning）。密度涨的是"形"，不是"计划条目"。

## 四、颜色与分层

- 组内 `fill` 用视觉系统 token：`primary / accent / surface / text_light`，由构建脚本按所选视觉系统解析，**不写死色值**；
- 大面积块用 `fill_transparency` 6–25%，细线/刻度用实色，保证深色底与浅色底都成立；
- 装饰组永远画在 L2，构建脚本按 `z_index` 升序绘制，装饰不会盖住内容（红线 11）。

## 五、构建与校验落点

- `scripts/build_pptx.js`：`addDecorationSetEl()` 逐图元绘制并用 `objectName` 打标（`DSET#<页号>#<组名>#<序号>`），XML 后处理把同一组的连续 `<p:sp>` 包成 `<p:grpSp>`（identity 变换，子形状坐标不变），并在构建日志输出"装饰组 N 组 / M 图元"；组不存在时**降级跳过并记入报告**，不中断构建；
- `scripts/validate_plan.py`：校验 `set_id` 存在性、`z_index` 分层、内容页组数下限（低于下限给 warning，并提示国赛对齐目标 形/页 ≥55）；
- 生成后：`score_deck.py` 的「国赛对齐度」分项按 `config.json:gsl_alignment.targets` 对比 形/页、组/页等指标。

## 六、边界

装饰组解决的是"密度与边界秩序"，**不等于设计师手笔**：组内几何是通用图元拼版，不含原创图形与手绘信息图（见 `gsl-alignment.md` 第六节）。要做"专属图形"仍需生图或人工绘制后按 `image` 元素嵌入。