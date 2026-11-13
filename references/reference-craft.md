# 参考手法规范补充（从素材库参考稿实测得出）

本文件把素材库参考稿里**实测出来的做法**转成可执行规范。**只在以下两种情况读**：
用户给了参考稿/模板要借鉴时；或在讨论"要不要改本包规范"时。其余情况按 `visual-system.md`、`layout-templates.md` 等常规规范执行。

实测数据与台账见 `knowledge/reference_analysis/craft-ledger.md`（10 份 pptx / 170 页），
重新生成：`python scripts/analyze_reference.py`。

## 一、参考稿总体画像（实测）

| 维度 | 实测 | 说明 |
|---|---|---|
| 每页形状 | 0–122.9 | 基础图元拼版为主：`rect` 2551 次、`roundRect` 512、`ellipse` 475 |
| 每页组合 | 0–31.5 | 先做组件、再整组跨页复用 |
| 每页图片 | 1–15.4，大图占比≈0 | 图片主要当装饰件，而非摄影配图 |
| 字号 | 5–287pt，跨度 5.7×–31.9× | **没有统一梯度**（标题档 1–9 个、正文档 4–11 个） |
| 每页色值 | 2.2–11.6 | 收敛度差异极大（黑金 2.2 极简 / 红金 11.6 丰富） |
| 原生对象 | 6 份有表格页、7 份有图表页，各 1–4 页 | 数据对象用得克制 |
| 动效与备注 | 1 页动画、1 份转场、备注 10/10 为空 | 参考稿基本不做动效、也不写备注 |
| 版式 | 多为 1–3 个 | 设计落在页面元素上，而非母版体系 |

## 二、可直接照做的套路（与现有规范不冲突）

| # | 套路 | 实测依据 | 落到哪 |
|---|---|---|---|
| 1 | 封面：大字主视觉（≥40pt）+ 一处装饰件带 + 信息行，不做白底色块 | 最大字号 80–287pt | `cover-design.md` + `cover-title` 卡片 |
| 2 | 装饰件按"组"做一次、跨页复用（封面带、章节带、页脚位） | 组/页 2–32 | `visual-effects.md` + 母版装饰层（L2） |
| 3 | 内页只依赖 `rect` / `roundRect` / `ellipse` 三类图元，并严格 12 列对齐 | rect/roundRect/ellipse 占比最高 | `layout-templates.md` zones + `visual-system.md` 网格 |
| 4 | 图主导页：字/页 ≤ 80，图片承担主视觉，文字只留标题 + 一句结论 | 38 页整页视觉（除 Airflow） | `image-strategy.md` + `cover-full-image` |
| 5 | 章节页：超大字形 + 极少文字（≤14 字） | 章节/大字页实测 | `cover-design.md` 章节页规范（120pt 编号） |
| 6 | 数据页克制使用原生图表（每份 1–3 页），其余靠文字与图形 | 原生图表页 1–3 | `native-objects.md` + `layout-data-dash` |
| 7 | 多模块内页：模块内部结构一致（图标 + 小标题 + 要点） | 共性手法 1、2 | `layout-templates.md` 六条纪律 |
| 8 | 配色收敛：单页色值控制在 3–6 个 | 每页色数 2.2–11.6 | `visual-system.md` 6 色 + 图表调色板 |

## 三、明确不采纳的参考稿做法

| 做法 | 为什么不采纳 |
|---|---|
| 整页图片拼装（0 形状、0 文本框） | 违反红线第 1、10 条，交付后不可改字改数（见 `../knowledge/fail_cases/fc-20261105-01.md`） |
| 备注全部留空 | 违反红线第 14 条（每页必须有讲者备注） |
| 5–9pt 极小正文 | 低于 `config.json` 的 `fonts.min_pt = 10`，投影现场不可读 |
| 单页 11 个以上色值 | 超出视觉系统 6 色的收敛要求，会破坏"整份统一"（红线第 13 条） |
| 逐页不同字号档位 | 违反红线第 16 条（统一字号梯度 H1–H4 / Body / Caption / Metric） |

## 四、待评估改进项（**尚未实施**，需用户确认后才改规范或脚本）

| 缺口 | 参考稿依据 | 现状 | 若实施要动哪里 |
|---|---|---|---|
| 超大字档 | 封面/章节 100–287pt 主视觉字 | 最大 H1 44pt / Metric 60pt | 视觉系统 `fonts`（新增 `display_size`）+ `validate_plan.py` 字号区间 + 卡片规范 |
| 装饰件密度 | 图/页最高 15.4，装饰位图密铺 | 仅 4 类特效模板 | `assets/effect-templates/` 增类 + `config.json` 增密度参数 + `visual-effects.md` |
| 组件组复用 | 组/页最高 31.5，跨页整组复制 | 无"组件组"概念 | `build_pptx.js` 需支持"组件组"定义与复用（工程改动较大） |
| 预设几何装饰 | `parallelogram`/`trapezoid`/`homePlate`/`plaque` 做装饰 | 几何以 rect/roundRect/ellipse 为主 | `page-plan-schema.md` 的 `shape_type` 枚举 + `build_pptx.js` 映射 |

未确认前**不要**把这些当成现行规范；页面计划仍按现有梯度与几何枚举编写，否则校验会报错。

## 五、复核方式

```bash
python scripts/analyze_reference.py        # 重新实测参考稿，产出 knowledge/reference_analysis/data
python scripts/validate_plan.py <plan.json> --knowledge knowledge   # 规范仍以校验器为准
python scripts/detect_layout.py <deck.pptx>                        # 原生对象与排版核对
```