# smart-ppt-designer

> 把「材料」变成「能讲的国赛级 PPT」的技能包：原生可编辑、视觉体系统一、风格按内容检索而非套模板。

[![license](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![red-lines](https://img.shields.io/badge/%E7%BA%A2%E7%BA%BF-29-red.svg)](SKILL.md) [![workflow](https://img.shields.io/badge/%E5%B7%A5%E4%BD%9C%E6%B5%81-13%20%E6%AD%A5-blue.svg)](SKILL.md) [![styles](https://img.shields.io/badge/%E8%A7%86%E8%A7%89%E7%B3%BB%E7%BB%9F-19-orange.svg)](SKILL.md)

**一句话：你给 PDF / DOCX / 旧 PPT / 参考图，它产出一份评委愿意看完、每个字都能在 PowerPoint 里直接改的演示稿——不做图片拼贴、不套固定模板、封面自动用 AI 书法烫金。**

这不是"输入主题、吐一版 PPT"的生成器。它解决的是真实场景里最难的那一段：手里有材料，要在有限时间里做出能讲、能改、能过的 PPT。

- 原生 PowerPoint 对象（形状 / 表格 / 图表 / 备注），双击即改，不崩
- 19 套视觉系统按内容检索匹配，不写死默认风格
- 29 条红线 + 13 步工作流，把踩过的坑固化成强制规范
- 配套 `smart-ppt-studio` 插件：左侧栏直接检索、预览、一键导入模板

## 目录

- [它到底强在哪](#它到底强在哪)
- [目录结构](#目录结构)
- [配套插件 smart-ppt-studio](#配套插件smart-ppt-studio左侧栏设计台)

---

## 它到底强在哪

### 1. 真正原生可编辑，不是图片拼贴

很多"AI 做 PPT"的产物本质是一堆图片——看起来能看，一改就崩。这里每一项都是 PowerPoint 原生对象：

- 原生形状、原生表格、数据驱动图表
- 可编辑公式、讲者备注
- 多图层堆叠（背景 → 装饰 → 内容 → 标题）
- 装饰组与组件复用落地为真实 `<p:grpSp>` 组，可整体挪动

**判据很简单：产物在 PowerPoint 里打开，每个文字框双击都能改。**

### 2. 风格靠检索，不设默认

不写死主题色和版式。它按「沟通目的 + 信息关系」去素材库里检索匹配的设计卡片与布局模板；风格同样按内容检索，或从你给的参考稿里提取成可复用的风格卡片（`ref-*.json`）。

**好处**：换一个主题不会得到同一套换色的 PPT。

### 3. 参考稿能"学会"，不止"参考"

你给一份参考稿（`.pptx` / `.pdf`），它会把原文件入库保留，并逐份提取出可调用的风格——风格卡片、风格索引、以及这稿用到的具体手法。

新参考稿随时可以再提取入库，库越用越懂你的口味。

### 4. 硬边界写在规范里，而不是靠自觉

29 条红线（违反即返工）覆盖了真实踩过的坑，例如：

- 封面必须是 AI 书法体，不得用系统字体冒充
- 卡片精致度：序号带、投影写入
- 背景禁令、语义小图标禁用、装饰性渐变禁用
- 跨客户端兼容（WPS / Office / Mac）规避

这些不是建议，是**脚本会校验、不合格就阻断出稿**的门槛。

### 5. 出稿后自己会挑毛病

排版静态检测不启动 PowerPoint、不调 COM，直接扫产物：

- 溢出、遮挡、坐标越界
- 装饰层与文字层的图层顺序
- 密度指标（形/页、组/页、字号跨度）
- 自评分 < 75 分 → 自动回写最弱页重排，最多 N 轮

**检测报告是结构化 JSON + Markdown，不是一句"看起来还行"。**

### 6. 配图有策略，不是逢缺必生图

缺图时的优先级：

1. 复用本稿既有的封面 / 章节图（风格一定统一）
2. AI 按本页主题生成，且必须融入本稿风格
3. 免费图库兜底
4. 纯色背景

判据写在 `references/image-strategy.md`，不是每次临时拍脑袋。

---

## 能力边界（诚实部分）

**能做到国金参考图的 70–80%**：高密度内页、章节导航、视觉系统统一、封面大图、原生图表与数据卡片、全对象可编辑。结构密度与视觉手法已对齐素材库区间（形/页 ≥55、组/页 ≥3、封面章节页最大字号 ≥187pt、字号跨度 ≥5.7×）。

**差距在哪**：实拍级大图、定制插画、设计师级细节打磨。

**唯一的硬上限**：设计师级"高级感"需要人工终审微调。视觉效果约能到 85–90%，最后那 10–15% 的"金奖级惊艳感"靠人。

> 不吹"全自动出金奖稿"。能自动化的是结构、密度、规范、校验；审美终审这一步，脚本替不了人。

---

## 快速上手

```bash
# 1. 解析输入材料
python scripts/parse_source.py --input 材料.pdf --out output/source.md

# 2. 检索素材（风格 / 卡片 / 版式 / 装饰组 / 图标；--list 自检）
python scripts/find_asset.py 红金 乡村振兴

# 3. 检索或提取风格
python scripts/find_style.py 红金 乡村振兴        # 或 --list / --mode dark
python scripts/extract_style.py 参考稿.pptx --name ref-xxx

# 4. 校验页面计划
python scripts/validate_plan.py output/plan.json --knowledge knowledge

# 5. 构建 PPTX（母版 + 章节导航 + 原生对象 + 备注）
node scripts/build_pptx.js --plan output/plan.json --candidate A --out output/deck.pptx

# 6. 排版检测 + 自评分
python scripts/detect_layout.py output/deck.pptx --config assets/config.json --out output/check_report.md
python scripts/score_deck.py --plan output/plan.json --candidate A --deck output/deck.pptx
```

完整十三步工作流见 `SKILL.md`。

---

## 目录结构

| 目录 | 内容 |
|---|---|
| `SKILL.md` | 技能主文件：能力、红线、十三步工作流、按需读取指引 |
| `references/` | 分主题规范：版式四原则、封面设计、构图约束、兼容性、配图策略、模板填充等 |
| `scripts/` | 构建与校验脚本（Python + Node） |
| `assets/` | 素材库：风格卡、卡片、版式模板、装饰组、图标、视觉系统、视觉特效模板 |
| `knowledge/` | 学习记忆：评审结论回写、失败案例、参考稿拆解数据 |
| `integrations/` | 外部集成：生图 / 抠图 provider 顺序与实测记录 |
| `examples/` | 页面计划示例 |

---

## 设计取舍（为什么这么做）

**为什么不用一套固定模板？**
固定模板换主题必然同构，这是"模板味"的根源。风格检索 + 参考稿提取让每份稿子的视觉决策都跟着内容走。

**为什么红线要写成脚本可校验的？**
"注意不要溢出"是空话。把阈值写进配置、把检查写进脚本，才能保证第 20 次出稿和第 1 次是同一个标准。

**为什么坚持内容原生可编辑？**
PPT 是给人改的。不能改的产物在真实协作里等于废稿——改一个字要重新生成整页，没人受得了。

**为什么要有"诚实的能力边界"章节？**
因为夸大能力会让人在错误的地方信任它。知道它做到 70–80%、知道最后 10–15% 要人工，比听到"全自动国赛级"有用得多。

---

## 环境要求

- **Python 3.9+**：脚本主语言
- **Node.js 16+**：`build_pptx.js`（依赖 `pptxgenjs` / `jszip`）
- **Microsoft PowerPoint**（可选）：仅在需要 COM 真开验证、或需要渲染核对时使用；纯生成与静态检测不需要它

```bash
npm install     # 安装 jszip / pptxgenjs
```

字体建议使用开源可商用字体（霞鹜文楷 / 思源黑体、宋体 / HarmonyOS Sans / MiSans / EB Garamond）；商业字库需自行取得授权。

---

## 许可

本仓库为技能包的**源码与文档部分**。参考稿原文件、样本 PPT、模板二进制等大体积素材未随仓库分发——它们不参与生成逻辑，只影响"参考手法提取"和"样本借鉴"类任务的素材丰富度。

使用前请自行确认所用字体、图片、模板素材的授权范围。


---

## 配套插件：smart-ppt-studio（左侧栏设计台）

仓库内 `smart-ppt-studio/` 是可选的 DeepSeek Harness 左侧栏插件，把技能包的能力带进 GUI：

- 检索 19 套视觉系统、速查 29 条红线与 13 步工作流
- **模板库支持一键导入**：本地 `.pptx` 拖入即自动抽取封面缩略图作预览（纯前端解包，无需后端）
- 模板预览改为前端内联，不再依赖宿主缩略图路由，离线也能显示
- 选风格 / 选模板后一键生成技能包可执行的生成指令

详见 [`smart-ppt-studio/README.md`](smart-ppt-studio/README.md)。
