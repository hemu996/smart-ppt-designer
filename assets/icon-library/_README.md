# 内置图标库

图标用**原生形状组合**绘制（保持可编辑，红线：禁止用图片贴图标）。库文件：`icons.json`，共 **64 个**图标，覆盖 9 个类别。

## 一、用法

页面计划里直接引用：

```json
{
  "type": "icon",
  "icon": "chart-column",
  "x_in": 2.6,
  "y_in": 1.75,
  "w_in": 0.5,
  "h_in": 0.5,
  "color": "primary"
}
```

- `icon`：`icons.json` 中 `icons` 下的键名；
- `x_in/y_in/w_in/h_in`：目标框（建议 **0.4–0.8in**，与标题同行时居中于标题行）；
- `color`：颜色 token（`primary` / `secondary` / `accent` / `text` / `text_light` / `background`），取当前视觉系统的对应色；不填默认 `accent`；
- `build_pptx.js` 会把 `icons.json` 里 100×100 的坐标等比缩放后逐个画成原生形状。

## 二、类别与图标清单

| 类别 | 图标 |
|---|---|
| 数据 | `chart-bar` `chart-column` `chart-line` `chart-pie` `chart-doughnut` `dashboard` `table` `formula` |
| 流程 | `process-flow` `loop-cycle` `arrow-right` `arrow-up` `steps-up` `funnel` `milestone` `roadmap` |
| 时间 | `clock` `calendar` `timeline` `hourglass` `deadline` |
| 人物组织 | `person` `team` `group` `org-tree` `handshake` `elder` |
| 医疗健康 | `health-cross` `pill` `heart-pulse` `stethoscope` `herb` `moxibustion` `clinic` `rehab` |
| 教育文化 | `book` `graduation` `diploma` `culture-seal` `brush` `scroll` `lotus` `inkstone` |
| 地点空间 | `map` `pin` `building` `community` `home` `route` `globe` |
| 安全合规 | `shield` `lock` `badge-check` `check` `warning` `audit` |
| 增长价值 | `growth-arrow` `coin` `medal` `award` `star` `trophy` `idea` `spark` |

## 三、使用约束

1. **一页最多 4 个图标**，只用在模块标题、指标卡片、要点前导，不要做纯装饰。
2. 图标颜色必须来自视觉系统 token，不要写死十六进制（否则整份 PPT 配色会花）。
3. 图标尺寸统一：模块标题行同一页内必须同尺寸，偏差 ≤ 0.05in。
4. 图标不承载信息含义之外的文字，不要在图里塞关键词。
5. 库里没有合适的图标时：优先改用已有图标表达相近含义；确实需要新图标时按 `icons.json` 的 `shape_vocabulary` 追加（只用原生形状词表内的形状）。

## 四、新增图标

在 `icons.json` 的 `icons` 下追加一项：

```json
"my-icon": { "category": "自定义", "shapes": [ { "shape": "rect", "x": 20, "y": 20, "w": 60, "h": 60, "fill": "primary" } ] }
```

- 坐标基准：100×100 视框，`x/y/w/h` 为 0–100 的相对值；
- `fill` 只能用 token（见 `meta.fill_tokens`）；
- `shape` 只能用 `meta.shape_vocabulary` 里的形状名（PptxGenJS 原生形状）；
- 追加后跑一次 `python scripts/validate_plan.py output/plan.json --knowledge knowledge`，确认引用的图标名存在。