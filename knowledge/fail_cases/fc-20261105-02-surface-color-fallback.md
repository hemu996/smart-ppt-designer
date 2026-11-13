# 失效案例 fc-20261105-02：深色系统卡片被画成半透明白

- 日期：2026-11-05
- 场景：v8.7 国金标准示例稿（`tech-gold-noir` 暗金夜）重建，目录页 6 张编号卡
- 现象：卡片底渲染为**中灰**（采样 `RGB(154,152,150)`），卡内白色章节名几乎不可读；四宫格内容页的标题、模块标题、结论行也是**深色**，在深色底上完全看不见。
- 定位过程：
  1. 渲染成图（PowerPoint 导出 PDF → PyMuPDF → 2000×1125 PNG）后逐页目检，发现两类配色缺陷；
  2. 采样卡片区域像素，得中灰；背景为 `#0B0B10`（深）→ 卡片不是"浅色视觉系统"的预期表现；
  3. 读 `assets/pptxgenjs-config.js:resolveToken()`：解析顺序是「先查 `system.colors[token]`，再落到 `config.theme`」，而 `config.theme.background = FFFFFF`；
  4. 扫描 19 套视觉系统：**全部没有 `surface` 键** → `surface` 一律落到白色；`colors.text` 在深色系统里是白色，但计划里标题元素显式写了 `color: "primary"`（`#1F1B16` 近黑）→ 深底深字。
- 根因：两条独立缺陷叠加
  - a) 深色视觉系统缺 `surface` 键 → token 回落到白色主题值；
  - b) 计划里文字色误用 `primary`（深色系统的 primary 是底色系，不是文字色）。
- 修复：
  1. 为 9 套 `mode=dark` 视觉系统补 `surface`（取 `primary`），浅色系统保持落到白色主题值即可；
  2. 生成器统一把 `color == "primary"` 的文字改为 `text`（深色系统为白）；卡片组件底由 `text_light` 改 `surface`；
  3. 重新构建 → 采样确认卡片底 `RGB(31,27,22)`（深褐）、描边金色 `RGB(184,144,47)`。
- 验收：`detect_layout` error 0；`score_deck` 自评 A 92.6 / B 93.7，国赛对齐度 20/20；渲染图逐页目检通过。
- 沉淀：`references/anti-patterns.md`「深色视觉系统必须自带 surface 颜色键」；生成检查项——**深色系统的文字色不得用 `primary`**。