# 装饰组库（v8.7）

**用途**：以"1 个计划元素 → 多个基础图元 + 真实 PPT 组"的方式，把内页视觉密度提到国赛区间（形/页 ≥55，口径见 `references/gsl-alignment.md`）。

| 组 id | 名称 | 图元数 | 占据区域 |
|---|---|---|---|
| `left-rail-geometry` | 左侧竖轨几何 | 13 | 左页边距 x 0–0.92 |
| `right-rail-ruler` | 右侧细线标尺 | 13 | 右页边距 x 12.86–13.333 |
| `top-rule-band` | 顶部规则带 | 14 | 顶部 y 0–0.26 |
| `bottom-rule-band` | 底部规则带 | 12 | 底部 y 7.36–7.5 |
| `corner-ticks` | 四角刻线 | 12 | 四角的页边距内 |
| `side-dots-grid` | 侧边点阵 | 14 | 右侧页边距纵向点阵 |
| `texture-mesh` | 网格纹理 | 14 | 左侧页边距细线矩阵 + 顶部刻度（低透明度） |
| `glow-orbs` | 光斑辉光 | 12 | 四角发光圆 + 右侧点列（低透明度） |
| `section-rail` | 竖排章节标签轨道 | 11 | 左栏 0–1.05in；标签文字用 rotation=270 的文本框叠加（与 sidebar 导航二选一） |

- 每组 JSON 字段：`id / label / note / canvas_in / zone / shape_count / fill_tokens / shapes[]`；
- `shapes[]` 每项：`shape_type`（rect/ellipse/line）+ `x_in,y_in,w_in,h_in` + `fill`（token）+ 可选 `fill_transparency`、`line_color`、`line_width_pt`、`rotation`；
- 颜色一律用 token（`primary / accent / surface / text_light`），由构建脚本按视觉系统解析，不写死色值；
- 新增装饰组：按同 schema 加 JSON，并在 `index.json` 登记即可被 `validate_plan.py` 与 `build_pptx.js` 识别。

用法与规则见 `references/decoration-sets.md`。