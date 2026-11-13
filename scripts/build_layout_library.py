#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从素材库样本逐页明细提炼「常见布局特征库」（规格 v9.3 L663：模板校验兜底的依据）。

数据源：`knowledge/reference_analysis/data/ref-*.json`（10 份样本 153 页的逐页实测明细，
由 `scripts/analyze_reference.py` 静态解压生成，不含 PowerPoint / COM）。

用法：
    python scripts/build_layout_library.py            # 生成/刷新 assets/layout-patterns/common-layouts.json
    python scripts/build_layout_library.py --min-count 2 --out assets/layout-patterns/common-layouts.json

口径：
- 样本逐页没有元素坐标，因此布局指纹用「角色 × 映射卡片 × 元素量分箱」表达；
- 每条布局记录该组内的形数 / 图数 / 文本块数实测区间（min–max），供计划侧判定"是否接近常见布局"；
- 不足 `--min-count` 次的组合视为孤例，不进入库（避免把偶发版式当标准）。
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import statistics

# 样本角色 → 计划 slide_type
ROLE_MAP = {
    "封面": "cover", "章节": "section_divider", "章节页": "section_divider",
    "内容页": "content", "密集内容页": "content", "数据页": "data_chart",
    "图主导页": "concept", "结尾页": "closing",
}
# 样本「映射卡片」 → 计划 card_used / 版式
CARD_MAP = {
    "cover-title": "cover-title",
    "layout-sidebar-nav": "layout-sidebar-nav",
    "layout-data-dash": "layout-data-dash",
    "layout-four-grid": "layout-four-grid",
    "layout-two-column": "layout-two-column",
    "timeline-horizontal": "timeline-horizontal",
    "hierarchy-tree": "hierarchy-tree",
    "funnel-conversion": "funnel-conversion",
    "metric-highlight": "metric-highlight",
    "problem-solution": "problem-solution",
    "comparison-matrix": "comparison-matrix",
    "layout-toc-number-grid": "layout-toc-number-grid",
    "整页视觉（cover-full-image）": "layout-image-bleed",
}
# 计划侧可映射到的包内版式模板（—fix 时用）
CARD_TO_LAYOUT = {
    "cover-title": "cover-full-image",
    "layout-image-bleed": "image-bleed",
    "layout-sidebar-nav": "sidebar-nav",
    "layout-data-dash": "data-dashboard",
    "layout-four-grid": "four-grid",
    "layout-toc-number-grid": "toc-number-grid",
    "layout-two-column": "sidebar-nav",
    "timeline-horizontal": "sidebar-nav",
    "hierarchy-tree": "sidebar-nav",
    "funnel-conversion": "sidebar-nav",
    "metric-highlight": "data-dashboard",
    "problem-solution": "four-grid",
    "comparison-matrix": "four-grid",
}

ROLE_LABEL = {"cover": "封面", "section_divider": "章节页", "content": "内容页",
              "data_chart": "数据页", "concept": "图主导页", "closing": "结尾页"}


def band(v, edges):
    """返回 (下界, 上界, 档位编号)"""
    for i, (lo, hi) in enumerate(edges):
        if lo <= v < hi:
            return lo, hi, i
    return edges[-1][0], edges[-1][1], len(edges) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="knowledge/reference_analysis/data")
    ap.add_argument("--out", default="assets/layout-patterns/common-layouts.json")
    ap.add_argument("--min-count", type=int, default=2)
    args = ap.parse_args()

    shape_edges = [(0, 20), (20, 50), (50, 90), (90, 140), (140, 10 ** 9)]
    pic_edges = [(0, 1), (1, 4), (4, 9), (9, 10 ** 9)]

    groups = collections.defaultdict(list)
    files = sorted(glob.glob(os.path.join(args.data_dir, "ref-*.json")))
    total_pages = 0
    for f in files:
        slug = os.path.basename(f)[:-5]
        d = json.load(io.open(f, encoding="utf-8"))
        for s in d.get("slides", []):
            total_pages += 1
            role = ROLE_MAP.get(str(s.get("角色") or ""))
            card = CARD_MAP.get(str(s.get("映射卡片") or ""))
            if not role or not card:
                continue
            shp = int(s.get("形") or 0)
            pic = int(s.get("图") or 0)
            tblk = int(s.get("文本块") or 0)
            sb = band(shp, shape_edges)
            pb = band(pic, pic_edges)
            groups[(role, card, sb[2], pb[2])].append(
                {"slug": slug, "page": s.get("页"), "shape": shp, "pic": pic, "tblk": tblk})

    patterns = []
    for (role, card, sbi, pbi), rows in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(rows) < args.min_count:
            continue
        shp_r = sorted(r["shape"] for r in rows)
        pic_r = sorted(r["pic"] for r in rows)
        tblk_r = sorted(r["tblk"] for r in rows)
        patterns.append({
            "id": "%s|%s|sh%d|pic%d" % (role, card, sbi, pbi),
            "name": "%s｜%s｜%s元素·%s图" % (
                ROLE_LABEL.get(role, role), card,
                {0: "少量", 1: "中量", 2: "较多", 3: "大量", 4: "极密"}.get(sbi, "?"),
                {0: "无", 1: "少", 2: "中", 3: "多"}.get(pbi, "?")),
            "role": role,
            "card": card,
            "layout_template": CARD_TO_LAYOUT.get(card, "sidebar-nav"),
            "shape_band": list(shape_edges[sbi][:2]),
            "pic_band": list(pic_edges[pbi][:2]),
            "shape_range": [shp_r[0], shp_r[-1]],
            "pic_range": [pic_r[0], pic_r[-1]],
            "tblk_range": [tblk_r[0], tblk_r[-1]],
            "count": len(rows),
            "sources": ["%s#p%s" % (r["slug"], r["page"]) for r in rows[:6]],
            "source": "sample",
        })

    # 样本缺「章节页 / 目录页」，按包内规范补条目（source=package）
    for _r, _c, _lt, _nm in (
        ("section_divider", "cover-title", "cover-full-image",
         "章节过渡页（五要素：全屏背景图 / 超大编号 / 章节标题 / 一句话说明 / 装饰线）"),
        ("toc", "layout-toc-number-grid", "toc-number-grid", "目录页（编号网格）"),
    ):
        patterns.append({
            "id": "package|%s" % _r, "name": "%s（包内规范补条目）" % _nm,
            "role": _r, "card": _c, "layout_template": _lt,
            "shape_band": None, "pic_band": None,
            "shape_range": None, "pic_range": None, "tblk_range": None,
            "count": 0, "sources": ["包内规范（样本未覆盖）"], "source": "package",
        })

    # 包内版式模板 / 卡片：作为扩展条目（补齐规格要求的 30-50 种覆盖面）
    for card, lt in CARD_TO_LAYOUT.items():
        if any(p["card"] == card for p in patterns):
            continue
        patterns.append({
            "id": "package|%s" % card,
            "name": "包内版式：%s（%s）" % (card, lt),
            "role": "*",
            "card": card,
            "layout_template": lt,
            "shape_band": None, "pic_band": None,
            "shape_range": None, "pic_range": None, "tblk_range": None,
            "count": 0,
            "sources": ["包内版式模板 / 设计卡片"],
            "source": "package",
        })

    doc = {
        "_note": ("v9.0.2 常见布局特征库（规格 v9.3 L663 模板校验兜底的依据）："
                  "由 scripts/build_layout_library.py 从素材库样本逐页明细（data/ 覆盖 9 份 153 页）提炼；"
                  "样本逐页无元素坐标，故以「角色 × 映射卡片 × 元素量分箱」为布局指纹，"
                  "并记录组内形数 / 图数 / 文本块数实测区间。计划侧由 scripts/check_layout_similarity.py 判定接近度。"),
        "generated_from": "%d 份样本 / %d 页（%s）" % (len(files), total_pages, args.data_dir),
        "min_count": args.min_count,
        "pattern_count": len(patterns),
        "patterns": patterns,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(doc, io.open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("布局特征库已生成：%s" % args.out)
    print("  条目 %d 条（样本提炼 %d 条 / 包内扩展 %d 条）"
          % (len(patterns), sum(1 for p in patterns if p["source"] == "sample"),
             sum(1 for p in patterns if p["source"] == "package")))


if __name__ == "__main__":
    main()