# 生图集成（DSH 内置 `dsh.image`）

本技能包**不实现生图能力**（红线第 7 条），只负责三件事：判断哪些页要图 → 把页面计划翻译成 prompt → 把图片路径嵌进 PPTX。
实际出图由 **DSH 内置的 `dsh.image`**（底层阿里云通义万相 API）完成。

> **环境已知情况（如实标注）**：本轮开发在本机探测 `dsh` / `dsh.image` 命令均**未在 PATH 中找到**。
> 按规格末尾的要求「技术上实现不了先反馈再调整，不要自行换路线」，此处**不擅自替换生图实现**：
> 脚本仍只产出 prompt 清单（`image_requests.json`）并按 `dsh.image` 契约声明参数；
> 请确认 `dsh.image` 在本机的实际调用方式（命令路径或 DSH 工具名）后再执行第 ②步。
> 确认前可先用环境中实际可用的图片生成能力出图（**禁止**脚本自实现生图或本地画图替代）。

## 一、三段式调用

```
① 生成清单   node scripts/generate_images.js --plan output/plan.json --candidate A --emit output/image_requests.json
             （需要装饰/特效素材时：node scripts/generate_effects.js --plan output/plan.json --candidate A --emit output/effect_requests.json）
② 调用生图   DSH 按本文件逐条调用 dsh.image，把结果落盘到 output/images/slide_<id>_<type>.png
③ 回填路径   node scripts/generate_images.js --plan output/plan.json --candidate A --fill output/images
```

`image_requests.json` 的结构（由 ① 生成，不要手改）：

```json
{
  "tool": "dsh.image",
  "style": "humanities",
  "retry": { "max_attempts": 2, "backoff_ms": 1500 },
  "on_failure": "solid_color",
  "requests": [
    {
      "slide_id": 1,
      "slide_type": "cover",
      "image_type": "cover_visual",
      "size": [1920, 1080],
      "prompt": "深红底金线，国风厚重，茶山梯田晨雾，抽象渐变背景，低细节，留白充足，左侧大面积留白，适合叠加金色标题，画面内不出现任何文字，不出现写实人物",
      "prompt_source": "generated",
      "target_path": "output/images/slide_1_cover_visual.png",
      "target_name": "slide_1_cover_visual.png"
    }
  ]
}
```

## 二、生图前先搜网络参考图（规格验收项）

规格要求「生图前自动搜索网络参考图，生成结果更贴合主题」。执行顺序：

1. 用主题关键词检索免费图库/公开图（`node scripts/search_photos.js` 或环境内的图片搜索能力），取 3–4 张候选；
2. 人工或模型判断这批参考的**配色倾向、构图、材质**，把结论压成 prompt 里的风格词（**不下载整图当素材**，除非授权允许）；
3. 再调用 `dsh.image` 出图。参考图只作风格依据，不替代出图。

## 三、参数映射

| 技能包字段 | `dsh.image` 参数 | 说明 |
|---|---|---|
| `request.prompt` | prompt / text | **已完成风格拼接**，直接传入，不要再叠风格词，否则整份 PPT 风格会漂 |
| `request.size[0]` / `[1]` | 尺寸（width/height 或档位） | 只接受固定档位时选最接近的横版比例（16:9） |
| `request.target_path` | 不支持指定输出路径时，由 Agent 把结果另存到该路径 | 文件名必须保持 `slide_<id>_<type>.png`，否则 ③ 回填找不到 |
| `style`（顶层） | 一般无需传 | 风格已写进 prompt |

### 书法标题五型（封面/章节/结尾 L4 标题层，v8.2）

**默认偏好：飞白书法** —— 国潮 / 红金风格默认用飞白体（笔画丝丝露白、有毛笔笔触质感），不是普通楷体。

| 风格 | Prompt 模板 | 适用 |
|---|---|---|
| **飞白书法（默认）** | 毛笔飞白书法，笔画丝丝露白，有笔触质感，金色烫金效果，国风，中国书法，透明背景 | 国潮红金风格默认；文化类项目、章节页、结尾页 |
| 狂野书法 | 字体狂野奔放，笔画飘逸，富有动感张力，飞白，国风，中国书法，笔触流畅，白底黑字 | 创新创业、科技突破、热血主题 |
| 秀气书法 | 字体娟秀雅致，笔画细腻，文人书法风格，白底黑字，国风 | 人文、文化、教育类项目 |
| 粗黑体 | 超粗黑体，方正有力，现代简约，白底黑字 | 商务、金融、专业类项目 |
| 手写体 | 自然手写字体，亲切随意，钢笔手写感，白底黑字 | 学生项目、轻量主题 |

实现要求：

- 标题文字内容 + 风格 prompt → `dsh.image` 生成**透明背景** PNG，作 **L4 标题层**（图片形式，不能改文字，但视觉优于 PPT 内置字体）；
- 颜色由 prompt 指定（黑字 / 金字 / 白字）；透明背景生成失败（返回实底）按失败处理，不要叠在页面上；
- **同一份稿只用一种书法风格**（风格漂移属返工项）；每份稿书法标题 ≤ 2 处，其余页面用普通标题条（见 `assets/effect-templates/gold-calligraphy.json` 的 `styles`）。

## 四、尺寸

| 图片类型 | 尺寸 | 理由 |
|---|---|---|
| `cover_visual` / `section_background` / `closing_background` | 1920 × 1080 | 整页背景，覆盖 13.333×7.5in 画布 |
| `concept_illustration` | 800 × 600 | 半版插图，避免文件过大 |
| 装饰/特效素材（烫金、纹样、发光、粒子） | Android 同比例透明 PNG（≥800 × 800） | L2/L4 装饰层，透明背景 |

> 接口对宽高可能有整除/像素区间约束，会把 1920×1080 归一化到 1920×1072 这类最接近的合规值；图片按整页拉伸嵌入，比例不变，无需额外补偿。

## 五、失败与重试

1. 单张最多 `retry.max_attempts`（默认 2）次、间隔 `retry.backoff_ms`（默认 1500ms），仅在超时、限流、返回为空时重试；**内容违规类拒绝不要重试**（换更中性的描述）。
2. 仍失败 → 跳过该图，不写错误文件；③ 步把该页 `image_path` 置 `null`。
3. 构建时 `image_path` 为空或文件缺失 → 该页降级为 `on_failure = solid_color` 纯色背景，**流程照常完成**（红线第 15 条三级降级）。
4. 交付说明必须写明"第 X 页配图已降级为纯色背景"。

## 六、批量与限流

- 逐条串行调用，不要并发十几张；一份稿通常只有 3–5 张（红线第 6 条）。
- 同一份 PPT 的 prompt 共用同一风格前缀（来自视觉系统），**不要为单张图单独改风格**。
- 装饰件优先"做一次、多页复用"（样本实测：组合/页 0.3–21.6），不要逐页生成。

## 七、验证清单

- [ ] `image_requests.json` 每项都有 `prompt`、`size`、`target_name`；
- [ ] 出图数量 3–5 张、不超过总页数 1/3；
- [ ] 所有 prompt 共用同一风格前缀；
- [ ] `--fill` 后页面计划 `image_path` 与实际文件一致；
- [ ] 故意让一张图失败，PPT 仍能正常生成（纯色降级）。