# 组件复用规范（v8.7）

**一句话**：把"一页里的一小块结构"（导航条、卡片、编号块、图例条）定义成**计划级 component**，多页引用同一个 `component_id` —— 构建时按引用逐次展开，每个实例各自包成真实 `<p:grpSp>` 组。这是把 组/页 从 0 拉到国赛区间（≥3）的手段，口径见 `gsl-alignment.md`。

## 一、和装饰组的分工

| | 装饰组 `decoration_set` | 组件 `component` |
|---|---|---|
| 来源 | 包内库 `assets/decoration-sets/`（9 组固定几何，按 `set_id` 引用） | 页面计划里的 `components`（**按本次内容现做**，按 `component_id` 引用） |
| 位置 | 只占页边距，不进入内容安全区 | 进内容区，承载结构（卡片区、编号块、图例条、表头底） |
| 复用 | 跨页复用同一套库内几何 | 跨页复用**同一份定义**，各页锚点可不同 |
| 分层 | 固定 L2（`z_index` 10–19） | 按角色分层：结构底 L3（20–29）/ 标题条 L4（30–39） |
| 目的 | 提密度（形/页）+ 边界秩序 | 提复用（组/页）+ 跨页一致性 |

两者一起用：装饰组管"版面框架"，组件管"内容结构"。

## 二、在页面计划里怎么写

组件是**计划顶级字段**（和 `candidates` 同级），不是页内元素：

```json
{
  "components": {
    "kpi-card": {
      "label": "KPI 卡（描边 + 半透明底 + 图标位 + 标题条）",
      "shapes": [
        { "shape_type": "roundRect", "x_in": 0,    "y_in": 0,    "w_in": 2.6, "h_in": 1.5,
          "fill": "surface", "fill_transparency": 12, "line_color": "accent", "line_width_pt": 0.75 },
        { "shape_type": "rect",      "x_in": 0,    "y_in": 0,    "w_in": 2.6, "h_in": 0.34, "fill": "accent" },
        { "shape_type": "ellipse",   "x_in": 0.14, "y_in": 0.52, "w_in": 0.5, "h_in": 0.5,  "fill": "accent",
          "fill_transparency": 20 }
      ]
    }
  }
}
```

页内引用：

```json
{
  "type": "component",
  "component_id": "kpi-card",
  "x_in": 1.38, "y_in": 1.30, "w_in": 2.6, "h_in": 1.5,
  "role": "content",
  "z_index": 20
}
```

规则：

1. `components` 的 key 就是 `component_id`；每组必须有非空 `shapes` 数组，否则 `validate_plan.py` 报 error；
2. `type: "component"` 的元素必须有 `component_id`（兼容 `id` 写法）；`component_id` 不在计划 `components` 里 → error 并列出可选值；
3. 组件元素的 `x_in / y_in` 是**整组锚点**，组内每个 shape 的 `x_in / y_in` 是**相对锚点的偏移**（构建脚本做加法），`w_in / h_in` 用组内绝对尺寸；
4. 组件元素同样要写 `x_in/y_in/w_in/h_in`，填**整组外框**（校验器据此查越界）；
5. `z_index` 按角色定：结构底 / 卡片底 `20`，标题条 `30`（红线 11 的分层规则同样适用）；
6. 组内形状的 `fill` 用视觉系统 token（`primary / accent / surface / text_light`）或 6 位色值，**不写死色**；
7. 建议**内容页 2–4 个组件实例**（把整块"卡片区"做成一个组件最划算）；同一组件整份稿复用 ≥2 次才有意义，只出现 1 次就直接用 `shape` / `decoration_set` 写。

## 三、构建与成组

- `scripts/build_pptx.js`：`addComponentEl()` 逐图元绘制，`objectName` 打标 `CMP#<页号>#<component_id>#<实例序号>#<组内序号>`；每个实例的连续 `<p:sp>` 由 XML 后处理包成一个 `<p:grpSp>`（identity 变换，子形状坐标不变）；
- 构建日志输出 `组件复用：N 次 / M 个图元`；`component_id` 不存在时**降级跳过并记入报告**，不中断；
- 组件与装饰组可同页共存：装饰组在 L2、组件按角色在 L3/L4，绘制顺序由 `z_index` 保证。

## 四、校验落点

| 脚本 | 检查 |
|---|---|
| `validate_plan.py` | `components` 是否有 `shapes`；`component_id` 是否有效（error）；组件元素坐标越界（error）；`z_index` 声明与分层（error） |
| `detect_layout.py` | 成组后按 `<p:grpSp>` 识别；组内叠压（描边压底块等）记为 info，不计遮挡 error |
| `score_deck.py` | 「国赛对齐度」分项的 `组/页 ≥3` 由组件 + 装饰组共同贡献 |

## 五、边界

- 组件是**结构复用**，不是图形设计：组内几何仍是 `rect / roundRect / ellipse / line / chevron` 通用图元；
- 需要"专属图形"（品牌标识、手绘信息图）仍走生图或人工绘制后按 `image` 嵌入；
- 同一组件不要在同页叠放超过 1 次（视觉上会读成"重影"）。
