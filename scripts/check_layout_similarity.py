#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""布局接近度校验（规格 v9.3 L663「模板校验兜底」）。

判定每页布局是否「接近素材库常见布局」，分三层：
1. matched    —— (角色 × 卡片) 命中样本提炼的常见布局条目；
2. acceptable —— 样本未覆盖该组合，但 card_used / layout_template 属包内合法素材（布局仍合规，仅提示）；
3. deviated   —— card_used 与 layout_template 均不在包内合法集合，或几何拓扑散乱
                 （内容元素未形成清晰区块：列带 / 行带数超过上限）。

deviated 页给出「退回最接近布局」的建议；`--fix` 可把偏离页的 card_used / layout_template
改判为最接近布局并输出新计划（不覆盖原文件）。

用法：
    python scripts/check_layout_similarity.py --plan output/plan.json --candidate A
    python scripts/check_layout_similarity.py --plan output/plan.json --candidate A --json output/layout_similarity.json
    python scripts/check_layout_similarity.py --plan output/plan.json --candidate A --fix --out output/plan_fallback.json

退出码：0 = 无偏离；1 = 存在偏离。
"""
from __future__ import annotations

import argparse
import copy
import glob
import io
import json
import os
import sys


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


def asset_ids():
    """包内合法卡片 / 版式集合（与 validate_plan.py 同口径）"""
    cards = {os.path.basename(p)[:-3] for p in glob.glob("knowledge/cards/*.md")
             if not os.path.basename(p).startswith("_")}
    layouts = {os.path.basename(p)[:-5] for p in glob.glob("assets/layout-templates/*.json")}
    return cards, layouts


def is_decoration(e):
    if str(e.get("role") or "") in ("decoration", "background"):
        return True
    z = e.get("z_index")
    return isinstance(z, (int, float)) and not isinstance(z, bool) and 10 <= float(z) < 20


def bands(vals, tol):
    out = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def topo(elements, tol):
    """内容元素的列带 / 行带数（按左边界、上边界聚类）"""
    content = [e for e in elements if not is_decoration(e)]
    if not content:
        return 0, 0
    xs = [float(e.get("x_in") or 0) for e in content]
    ys = [float(e.get("y_in") or 0) for e in content]
    return len(bands(xs, tol)), len(bands(ys, tol))


def nearest(patterns, role, card):
    """同 role 优先、同 card 次之、样本条目优先，再按出现频次"""
    def key(p):
        return (
            0 if p["role"] == role else (0 if p["role"] == "*" else 1),
            0 if p["card"] == card else 1,
            0 if p.get("source") == "sample" else 1,
            -int(p.get("count") or 0),
        )
    return sorted(patterns, key=key)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--candidate", default="A")
    ap.add_argument("--lib", default="assets/layout-patterns/common-layouts.json")
    ap.add_argument("--config", default="assets/config.json")
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--out", default=None, help="--fix 时输出改判后的计划")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    lib = load(args.lib)
    patterns = lib["patterns"]
    cfg = load(args.config)
    fb = cfg.get("layout_fallback") or {}
    tol = float(fb.get("band_tolerance_in", 0.3))
    max_col = int(fb.get("max_col_bands", 8))
    max_row = int(fb.get("max_row_bands", 12))
    factor = float(fb.get("shape_factor", 3.0))
    ov = float(fb.get("extreme_over", 2.0))
    un = float(fb.get("extreme_under", 0.3))
    cards, layouts = asset_ids()

    plan = load(args.plan)
    cand = next((c for c in (plan.get("candidates") or []) if c.get("candidate_id") == args.candidate), None)
    if cand is None:
        print("[FAIL] 计划里没有候选 %s" % args.candidate)
        sys.exit(2)

    rows, deviated = [], []
    for s in (cand.get("slides") or []):
        sid = s.get("slide_id")
        role = str(s.get("slide_type") or "")
        card = str(s.get("card_used") or "")
        lt = str(s.get("layout_template") or "")
        els = [e for e in (s.get("elements") or []) if isinstance(e, dict)]
        cb, rb = topo(els, tol)
        hit = [p for p in patterns if p["role"] == role and p["card"] == card]
        best = max(hit, key=lambda p: int(p.get("count") or 0)) if hit else nearest(patterns, role, card)

        # 元素量极端偏离：与库中同 role 条目的形状区间（换算回元素数）比较
        extreme = ""
        same = [p for p in patterns if p["role"] == role and p.get("shape_range")]
        if same:
            hi = max(float(p["shape_range"][1]) for p in same) / factor
            lo = min(float(p["shape_range"][0]) for p in same) / factor
            if hi > 0 and len(els) > hi * ov:
                extreme = "元素量过密：%d 个 > 该角色常见上限 %d 的 %.1f 倍" % (len(els), round(hi), ov)
            elif lo > 0 and len(els) < lo * un:
                extreme = "元素量过疏：%d 个 < 该角色常见下限 %d 的 %.1f 倍" % (len(els), round(lo), un)

        if card not in cards and lt not in layouts:
            status, why = "deviated", "card_used 与 layout_template 均不在包内合法集合"
        elif extreme:
            status, why = "deviated", extreme
        elif cb > max_col or rb > max_row:
            status, why = "deviated", "几何极端散乱：内容元素形成 %d 列带 / %d 行带（上限 %d/%d）" % (cb, rb, max_col, max_row)
        elif hit:
            status, why = "matched", ""
        else:
            status, why = "acceptable", "样本未覆盖该组合，属包内合法布局"

        rows.append({
            "slide_id": sid, "slide_type": role, "card_used": card,
            "elements": len(els), "content_bands": [cb, rb],
            "status": status, "reason": why,
            "matched_pattern": best["name"], "matched_id": best["id"],
            "suggest_card": best["card"], "suggest_layout_template": best.get("layout_template"),
            "advice": "" if status != "deviated" else
                      "建议退回「%s」（card_used=%s / layout_template=%s）"
                      % (best["name"], best["card"], best.get("layout_template")),
        })
        if status == "deviated":
            deviated.append(rows[-1])

    n = len(rows)
    n_ok = sum(1 for r in rows if r["status"] == "matched")
    n_acc = sum(1 for r in rows if r["status"] == "acceptable")
    rate = (len(deviated) / n) if n else 0.0
    report = {
        "plan": args.plan, "candidate": args.candidate, "library": args.lib,
        "library_patterns": len(patterns), "library_source": lib.get("generated_from"),
        "pages": n, "matched": n_ok, "acceptable": n_acc,
        "deviated": len(deviated), "deviation_rate": round(rate, 3), "rows": rows,
    }

    lines = ["# 布局接近度校验（模板校验兜底）", "",
             "- 计划：`%s`｜候选：%s｜布局库：%d 条（%s）"
             % (args.plan, args.candidate, len(patterns), lib.get("generated_from", "")),
             "- 页数 %d｜命中常见布局 %d｜样本未覆盖但包内合法 %d｜偏离 %d（%.1f%%）"
             % (n, n_ok, n_acc, len(deviated), rate * 100), "",
             "| 页 | 类型 | 卡片 | 元素 | 列/行带 | 判定 | 最接近布局 |",
             "|---|---|---|---|---|---|---|"]
    label = {"matched": "命中", "acceptable": "可接受", "deviated": "**偏离**"}
    for r in rows:
        lines.append("| %s | %s | %s | %d | %d/%d | %s | %s |" % (
            r["slide_id"], r["slide_type"] or "-", r["card_used"] or "-", r["elements"],
            r["content_bands"][0], r["content_bands"][1], label[r["status"]], r["matched_pattern"]))
    if deviated:
        lines += ["", "## 偏离页与退回建议", ""]
        for r in deviated:
            lines.append("- 第 %s 页：%s（%s）" % (r["slide_id"], r["advice"], r["reason"]))
    md = "\n".join(lines) + "\n"
    md_path = args.md or "output/layout_similarity.md"
    os.makedirs(os.path.dirname(md_path) or ".", exist_ok=True)
    io.open(md_path, "w", encoding="utf-8", newline="").write(md)
    print(md)
    if args.json_out:
        json.dump(report, io.open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if args.fix and deviated:
        fixed = copy.deepcopy(plan)
        fcand = next((c for c in (fixed.get("candidates") or []) if c.get("candidate_id") == args.candidate), None)
        idx = {r["slide_id"]: r for r in deviated}
        for s in (fcand.get("slides") or []):
            r = idx.get(s.get("slide_id"))
            if not r:
                continue
            s["card_used"] = r["suggest_card"]
            s["layout_template"] = r["suggest_layout_template"] or s.get("layout_template")
        out = args.out or "output/plan_fallback.json"
        json.dump(fixed, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[fix] 已把 %d 个偏离页改判为最接近布局 → %s" % (len(deviated), out))

    print("[summary] 命中 %d / 可接受 %d / 偏离 %d（%.1f%%）"
          % (n_ok, n_acc, len(deviated), rate * 100))
    return 1 if deviated else 0


if __name__ == "__main__":
    sys.exit(main())