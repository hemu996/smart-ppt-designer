# 参考素材库（knowledge/reference_library/）

从用户提供的国赛/政务样本 PPT 提炼的**布局模式、封面风格与装饰元素**，用于"照着参考稿做"时快速对表。
数据来源：`assets/sample-ppts/` 的 8 份样本（136 页）逐页实测，方法与脚本见 `scripts/analyze_reference.py`。

## 一、目录（v8.3：子目录已按规格对齐）

| 路径 | 内容 |
|---|---|
| `layout-patterns/layout-patterns.md` | 布局模式：页面骨架序列、模块密度、可复用版式（**学习目标①：排版逻辑**） |
| `element-stacking/element-stacking.md` | 元素堆叠方式与视觉节奏（**学习目标②③：元素堆叠 + 视觉节奏，规格列为最核心**） |
| `cover-styles/cover-styles.md` | 封面风格：各系统的封面配方，含章节过渡页五要素与结尾页规范 |
| `decoration-elements/decoration-elements.md` | 装饰元素：金线/纹样/印章/发光/粒子，及对应特效模板 |
| `visual-systems/_README.md` | 视觉系统索引（实体在 `assets/visual-systems/`，此处为指针） |
| `sample-ppts/_README.md` | 样本索引与用途（实体在 `assets/sample-ppts/`，此处为指针） |
| `data/` | 逐页实测数据：`<样本>.json`、`_all.json`、`_mapping.json`（`scripts/analyze_reference.py` 生成） |

## 二、与规格目录的对应

| 规格目录 | 实际位置 | 说明 |
|---|---|---|
| `reference_library/visual-systems/` | 本目录 `visual-systems/`（指针）→ 实体 `assets/visual-systems/` | 构建脚本只从 `config.json:visual_system.dir` 读一处，实体不复制 |
| `reference_library/sample-ppts/` | 本目录 `sample-ppts/`（指针）→ 实体 `assets/sample-ppts/` | **按用户明确要求**样本放 assets 下；8 份原文件 535 MB，不重复占用空间 |
| `reference_library/layout-patterns/`、`cover-styles/`、`decoration-elements/`、`element-stacking/` | 本目录文档承载（`element-stacking/` 为独立子目录） | 便于按需读取，不拆多余层级 |

## 三、样本实测基线（9 份 / 144 页）

| 样本 | 页 | 形/页 | 组/页 | 图/页 | 字/页 | 色数/页 | 表页 | 图页 | 明暗 | 实测主色 | 实测强调 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 红色国风非遗文化 | 18 | 59.1 | 12.9 | 6.7 | 219 | 3.1 | 1 | 3 | 浅 | `#604626` | `#46130A` |
| 16页-国奖红金（康帅制作） | 17 | 55.6 | 21.6 | 15.4 | 134 | 11.6 | 1 | 1 | 浅 | `#AB1F10` | `#F5DE8E` |
| 东方遗韵——源文件 | 6 | 25.0 | 13.5 | 10.8 | 175 | 12.3 | 0 | 0 | 浅 | `#B3743B` | `#7F4134` |
| 刺绣文化 | 15 | 42.6 | 3.9 | 5.1 | 193 | 7.7 | 0 | 2 | 浅 | `#027184` | `#FFD4A0` |
| 04 中国风 非遗乐器 | 23 | 21.0 | 7.8 | 8.6 | 114 | 6.7 | 0 | 2 | 深 | `#875F3B` | `#D8AD55` |
| 红色党建帮助老人 | 18 | 26.2 | 4.8 | 6.4 | 188 | 5.7 | 1 | 2 | 浅 | `#800000` | `#F5A67E` |
| 财务云教育平台 | 4 | 45.2 | 9.2 | 7.8 | 117 | 6.8 | 0 | 1 | 深 | `#31A29E` | `#FFFF00` |
| Airflow·艾弗洛（医疗） | 35 | 7.7 | 0.3 | 5.6 | 205 | 6.2 | 5 | 0 | 见备注 | 不可靠 | 不可靠 |
| 华芯科技战略决策分析_加动画 | 8 | 14.8 | 0.0 | 0.2 | 198 | 6.1 | 3 | 0 | 浅 | `#3C465A` | `#FF8C32` |

逐页明细：`python scripts/analyze_reference.py --ref-dir assets/sample-ppts --out-dir knowledge/reference_library/data`。

> Airflow 是整页图片型稿件（33/35 页为 0 形状、0 文本框），其形状色值不可靠，见 `../fail_cases/fc-20261105-01.md`。

## 四、使用纪律

- 这里的数字是**样本实况**，不是本包标准；冲突时以 `references/` 的规范为准（原生可编辑、每页备注、统一字号梯度、显式图层）。
- 样本中"色数/页最高 12.3"说明参考稿普遍不收敛；本包按视觉系统 6 色 + 图表调色板执行，**不要照抄高色数**。
- 页面角色与卡片映射是按字数、字号、是否含表图做的启发式推断，引用时如实标注。