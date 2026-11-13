#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材库统一检索与自检（v8.9）

一次列出 / 检索本包全部可调用素材，并给出「何时用 + 在计划里怎么写」。
把原先分散在各处的检索入口（find_style.py 只覆盖风格）补齐到 6 类素材。

用法：
    python scripts/find_asset.py --list                 # 全部素材清单与状态（自检）
    python scripts/find_asset.py 茶 品牌 渠道            # 跨类关键词检索
    python scripts/find_asset.py --kind card 比较        # 只查某一类
    python scripts/find_asset.py --recipes              # 内容类型 → 推荐组合
    python scripts/find_asset.py 痛点 --json            # JSON 输出
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("style", "card", "layout", "decoration_set", "icon", "reference", "ppt_asset")
KIND_CN = {"style": "视觉系统", "card": "设计卡片", "layout": "版式模板",
           "decoration_set": "装饰组", "icon": "图标", "reference": "参考素材",
           "ppt_asset": "工作区素材"}

RECIPES = [
    {"scene": "痛点 / 缺口分析", "layout": "four-grid", "card": "problem-solution",
     "dsets": "right-rail-ruler + top-rule-band + bottom-rule-band"},
    {"scene": "多对象对比（3+ 或维度 ≥3）", "layout": "data-dashboard / sidebar-nav", "card": "comparison-matrix",
     "dsets": "right-rail-ruler + top-rule-band"},
    {"scene": "核心指标 / 成效展示", "layout": "data-dashboard", "card": "metric-highlight",
     "dsets": "right-rail-ruler + bottom-rule-band"},
    {"scene": "流程 / 路径 / 三链协同", "layout": "four-grid / image-bleed", "card": "funnel-conversion",
     "dsets": "corner-ticks + top-rule-band + bottom-rule-band"},
    {"scene": "层级 / 分类 / 组织架构", "layout": "sidebar-nav", "card": "hierarchy-tree",
     "dsets": "right-rail-ruler + top-rule-band"},
    {"scene": "时间线 / 阶段推进", "layout": "sidebar-nav / data-dashboard", "card": "timeline-horizontal",
     "dsets": "corner-ticks + bottom-rule-band"},
    {"scene": "目录 / 六宫格导航", "layout": "toc-number-grid", "card": "layout-toc-number-grid",
     "dsets": "corner-ticks + top-rule-band + right-rail-ruler"},
    {"scene": "封面 / 章节 / 结尾（大字页）", "layout": "cover-full-image", "card": "cover-title",
     "dsets": "corner-ticks + top-rule-band + right-rail-ruler"},
]


def _frontmatter(p: Path) -> dict:
    txt = p.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            out[k.strip()] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
        else:
            out[k.strip()] = v
    return out


def load_styles() -> list[dict]:
    items = []
    idx = ROOT / "assets" / "style-index.json"
    if idx.exists():
        for s in json.loads(idx.read_text(encoding="utf-8")).get("styles", []):
            items.append({"kind": "style", "id": s.get("name"), "label": s.get("label") or s.get("name"),
                          "when": f"内容关键词命中：{', '.join(s.get('keywords') or [])[:46]}（明暗 {s.get('mode')}）",
                          "how": 'design_brief.visual_system = "%s"' % s.get("name"),
                          "keys": list(s.get("keywords") or []), "extra": str(s.get("mode") or "")})
    for f in sorted((ROOT / "assets" / "personal-styles").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = d.get("system_name", f.stem)
        items.append({"kind": "style", "id": nm, "label": f"个人风格库：{d.get('label', nm)}",
                      "when": "自己满意、要复用的个人风格", "how": 'design_brief.visual_system = "%s"' % nm,
                      "keys": list(d.get("keywords") or []), "extra": str(d.get("mode") or "")})
    return items


def load_cards() -> list[dict]:
    items = []
    for f in sorted((ROOT / "knowledge" / "cards").glob("*.md")):
        if f.name.startswith("_"):
            continue
        fm = _frontmatter(f)
        items.append({"kind": "card", "id": fm.get("id", f.stem), "label": fm.get("name", f.stem),
                      "when": f"信息关系为「{fm.get('relation_type', '—')}」；标签 {'/'.join(fm.get('tags') or []) or '—'}",
                      "how": 'slides[].card_used = "%s"' % fm.get("id", f.stem),
                      "keys": [str(fm.get("relation_type", ""))] + [str(x) for x in (fm.get("tags") or [])],
                      "extra": str(fm.get("relation_type", ""))})
    return items


def load_layouts() -> list[dict]:
    items = []
    for f in sorted((ROOT / "assets" / "layout-templates").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        zs = list((d.get("zones") or {}).keys())
        items.append({"kind": "layout", "id": d.get("name", f.stem), "label": d.get("label", f.stem),
                      "when": str(d.get("use_when") or ""), "how": 'slides[].layout_template = "%s"' % d.get("name", f.stem),
                      "keys": zs, "extra": f"{len(zs)} 个区"})
    return items


def load_dsets() -> list[dict]:
    items = []
    p = ROOT / "assets" / "decoration-sets" / "index.json"
    if p.exists():
        for j in json.loads(p.read_text(encoding="utf-8")).get("sets", []):
            items.append({"kind": "decoration_set", "id": j.get("id"), "label": j.get("label"),
                          "when": "页边距框架装饰（提密度、立秩序）；组合建议见 references/decoration-sets.md",
                          "how": 'elements[] = {type:"decoration_set", set_id:"%s", z_index:10-19}' % j.get("id"),
                          "keys": ["装饰", "密度", "页边距", "框架"], "extra": f"{j.get('shape_count')} 图元"})
    return items


def load_icons() -> list[dict]:
    items = []
    p = ROOT / "assets" / "icon-library" / "icons.json"
    if p.exists():
        for name, v in (json.loads(p.read_text(encoding="utf-8")).get("icons") or {}).items():
            cat = str((v or {}).get("category", ""))
            items.append({"kind": "icon", "id": name, "label": name,
                          "when": f"分类「{cat}」的语义图标（原生形状绘制，非图片）",
                          "how": 'elements[] = {type:"icon", icon:"%s", color:"accent"}' % name,
                          "keys": [cat], "extra": cat})
    return items


def load_refs() -> list[dict]:
    tc = len(list((ROOT / "assets" / "target-cases").glob("*.jpg")))
    sp = len(list((ROOT / "assets" / "sample-ppts").glob("*.pptx")))
    rf = len([f for f in (ROOT / "assets" / "templates" / "references").glob("*") if not f.name.endswith(".md")])
    return [
        {"kind": "reference", "id": "assets/target-cases/", "label": f"目标案例图（{tc} 张）",
         "when": "写计划前对照国金稿共性；成稿后做观感自检", "how": "人工参考（非计划字段）",
         "keys": ["国金", "案例", "对标", "观感"], "extra": f"{tc} 张"},
        {"kind": "reference", "id": "assets/sample-ppts/", "label": f"用户样本稿（{sp} 份）",
         "when": "需要真实稿的风格与结构参照", "how": "人工参考；量测用 scripts/analyze_reference.py",
         "keys": ["样本", "参考稿", "实测"], "extra": f"{sp} 份"},
        {"kind": "reference", "id": "assets/templates/references/", "label": f"早期参考原文件（{rf} 份）",
         "when": "从参考稿提取风格时", "how": "python scripts/extract_style.py --file <原文件>",
         "keys": ["提取", "风格", "参考"], "extra": f"{rf} 份"},
    ]


def load_ppt_assets() -> list[dict]:
    """v9.0.6 工作区素材分类目录（ppt-assets，432 份，按 类别/人物线索/视觉级别/用途 编目）。

    对应用户「封面人物形象替换法」的归类步骤：先在此找同类别同级别的现成素材，
    找不到才用 AI 生成。规范见 references/cover-persona-swap.md。
    """
    items = []
    p = ROOT / "assets" / "ppt-assets-catalog.json"
    if not p.exists():
        return items
    doc = json.loads(p.read_text(encoding="utf-8"))
    for a in doc.get("items", []):
        desc = " · ".join(x for x in (a.get("category"), a.get("persona"),
                                     a.get("visual_level"), a.get("use")) if x)
        items.append({
            "kind": "ppt_asset",
            "id": a.get("rel", ""),
            "label": "%s（%s）" % (a.get("name"), a.get("asset_level")),
            "when": desc,
            "how": "路径：%s" % a.get("path"),
            "keys": [a.get("category", ""), a.get("persona", ""),
                     a.get("visual_level", ""), a.get("use", ""),
                     a.get("kind", ""), a.get("top", "")] + list(a.get("tags") or []),
            "extra": str(a.get("size_mb") or ""),
        })
    return items


LOADERS = {"style": load_styles, "card": load_cards, "layout": load_layouts,
           "decoration_set": load_dsets, "icon": load_icons, "reference": load_refs,
           "ppt_asset": load_ppt_assets}


def collect(kinds=None) -> list[dict]:
    out = []
    for k in (kinds or KINDS):
        out.extend(LOADERS[k]())
    return out


def match(item: dict, words: list[str]) -> int:
    hay = " ".join([str(item.get("id") or ""), str(item.get("label") or ""), str(item.get("when") or ""),
                    str(item.get("extra") or "")] + [str(x) for x in (item.get("keys") or [])]).lower()
    return sum(1 for w in words if w.lower() in hay)


def main() -> None:
    ap = argparse.ArgumentParser(description="素材库统一检索（v8.9）")
    ap.add_argument("words", nargs="*", help="关键词（可多个，空格分隔）")
    ap.add_argument("--kind", choices=KINDS, help="只查某一类素材")
    ap.add_argument("--list", action="store_true", help="列出全部素材与计数（自检）")
    ap.add_argument("--recipes", action="store_true", help="输出内容类型 → 推荐组合")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    a = ap.parse_args()

    if a.recipes:
        rows = [{"场景": r["scene"], "版式 layout_template": r["layout"], "卡片 card_used": r["card"],
                 "装饰组 set_id": r["dsets"]} for r in RECIPES]
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print("内容类型 → 推荐组合（候选，不设默认；最终按内容判断并按 style_rationale 说明理由）\n")
            for r in rows:
                print(f"· {r['场景']}")
                print(f"    版式：{r['版式 layout_template']}")
                print(f"    卡片：{r['卡片 card_used']}")
                print(f"    装饰：{r['装饰组 set_id']}")
            print("\n注：素材 id 必须真实存在；校验器会逐一核对，写错会报 error 并列出可选值。")
        return

    kinds = [a.kind] if a.kind else None
    items = collect(kinds)

    if not a.list and a.words:
        scored = [(match(it, a.words), it) for it in items]
        hits = [it for sc, it in sorted(scored, key=lambda x: -x[0]) if sc > 0]
    else:
        hits = items

    # 自检/清单模式：按类汇总
    if a.list or not a.words:
        by = {}
        for it in items:
            by.setdefault(it["kind"], []).append(it)
        if a.json:
            print(json.dumps({k: [i["id"] for i in v] for k, v in by.items()}, ensure_ascii=False, indent=2))
        else:
            print(f"素材库清单（共 {len(items)} 项）")
            for k in KINDS:
                v = by.get(k) or []
                if not v:
                    continue
                print(f"\n【{KIND_CN[k]}】{len(v)} 项 —— 引用字段：{v[0]['how'].split('=')[0].strip()}")
                for it in v:
                    print(f"   - {it['id']:<24} {it['label']}（{it['extra']}）")
            print("\n检索用法：python scripts/find_asset.py <关键词…>；组合推荐：--recipes")
        return

    if a.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return

    print(f"命中 {len(hits)} 项（关键词：{' '.join(a.words)}）\n")
    for it in hits:
        print(f"【{KIND_CN[it['kind']]}】{it['id']}｜{it['label']}")
        print(f"    何时用：{it['when']}")
        print(f"    怎么写：{it['how']}")
    if not hits:
        print("未命中。可先 python scripts/find_asset.py --list 看全量；风格类也可用 scripts/find_style.py。")


if __name__ == "__main__":
    main()