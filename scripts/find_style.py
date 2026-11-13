#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格库检索（v5.6）

作用：在「不设默认风格」的前提下，按内容关键词 / 明暗偏好检索可用视觉系统，
     给出候选 system_name 与配色摘要，供页面计划的 design_brief.visual_system 使用。

用法：
    python scripts/find_style.py --list
    python scripts/find_style.py 红金 乡村振兴
    python scripts/find_style.py --keyword 医疗 --mode dark
    python scripts/find_style.py --keyword 竞赛 --json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "assets" / "style-index.json"


def load() -> dict:
    if not INDEX.exists():
        raise SystemExit("找不到 assets/style-index.json，请先运行 scripts/build_style_library.py 生成风格库")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    # 个人风格库（v8.2）：assets/personal-styles/*.json，与内置同 schema，直接可检索
    have = {s.get("name") for s in idx["styles"]}
    for f in sorted((ROOT / "assets" / "personal-styles").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = d.get("system_name", f.stem)
        if name in have:
            continue
        idx["styles"].append({
            "name": name, "label": d.get("label", name), "keywords": d.get("keywords", []),
            "built_in": False, "personal": True, "mode": d.get("mode"), "colors": d.get("colors"),
            "confidence": "personal（个人风格库）",
            "source_files": d.get("source_samples", []),
            "system_json": f"assets/personal-styles/{f.name}", "card": d.get("card"), "originals": [],
        })
    return idx


def match(s: dict, words: list[str]) -> int:
    hay = " ".join([s.get("name", ""), s.get("label", ""), " ".join(s.get("keywords", []))]).lower()
    return sum(1 for w in words if w.lower() in hay)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("keywords", nargs="*", help="内容关键词，如：红金 乡村振兴")
    ap.add_argument("--keyword", action="append", default=[], help="追加关键词（可重复）")
    ap.add_argument("--mode", choices=["dark", "light"], help="只要深色或浅色系统")
    ap.add_argument("--list", action="store_true", help="列出全部风格")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    a = ap.parse_args()
    idx = load()
    styles = idx["styles"]
    words = list(a.keywords) + list(a.keyword)
    if a.mode:
        styles = [s for s in styles if s.get("mode") == a.mode]
    if words and not a.list:
        scored = [(match(s, words), s) for s in styles]
        scored = [(n, s) for n, s in scored if n > 0]
        scored.sort(key=lambda x: (-x[0], x[1]["name"]))
        styles = [s for _, s in scored]
    if not words and not a.list:
        ap.error("请给出关键词，或使用 --list 列出全部")
    if a.json:
        print(json.dumps({"count": len(styles), "styles": styles}, ensure_ascii=False, indent=2))
        return
    if not styles:
        print("没有匹配风格。不要因此套用默认风格：请按内容推导，或向用户确认参考方向。")
        print("可用风格：" + "、".join(s["name"] for s in idx["styles"]))
        return
    print(f"命中 {len(styles)} 个风格（未命中不要回落默认，先按内容推导或向用户确认）：\n")
    for s in styles:
        c = s.get("colors") or {}
        tag = "内置·已校订" if s.get("built_in") else ("个人风格库" if s.get("personal") else "参考稿提取")
        print(f"- {s['name']} ｜ {s['label']} ｜ {s['mode']} ｜ {tag}")
        print(f"    主色 {c.get('primary')} / 强调 {c.get('accent')} / 底色 {c.get('background')}")
        print(f"    关键词：{('、'.join(s.get('keywords') or []) or '—')}")
        if s.get("originals"):
            print(f"    原文件：{s['originals'][0]}")
        print(f"    卡片：{s.get('card') or '—'}")


if __name__ == "__main__":
    main()