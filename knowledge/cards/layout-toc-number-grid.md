---
id: layout-toc-number-grid
name: 目录编号卡（2×3）
relation_type: 并列
tags: [布局, 目录, 编号卡, 并列, 导航]
---

## 适用条件

- **目录页专用**：把 4–6 个章节 / 板块平级列出；
- 每张卡 = 序号（36–60pt 金色）+ 章节名（20–24pt）+ 一句话说明（12–14pt）；
- 6 个用 2×3，4 个用 2×2。

## 反例（禁止使用）

- 章节之间存在主次或先后关系 → 用 `timeline-horizontal` 或金字塔类卡片；
- 章节超过 6 个 → 先合并归类，或拆成两页目录；
- 内容页误用该版式（正文用编号卡会显得空洞）→ 内容页请用 `layout-four-grid` / `layout-sidebar-nav`。

## 与视觉系统的关系

编号与描边取视觉系统 `accent`，卡片底用 `card_style.fill_alpha` 规定的半透明底（如 `tech-gold-noir` 的 86% 近黑底 + 金色细描边）。
