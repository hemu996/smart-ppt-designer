#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参考稿制作手法拆解与卡片映射（素材库分析工具，v5.6）

用途：把素材库里的参考稿逐份拆开，量化"这些稿子是怎么做的"，并映射到本技能包的设计卡片，
    产物可直接作为写规范的依据与检索用的知识（配合 references/reference-craft.md 使用）。

方法与本包其余脚本一致：静态解压 .pptx 解析 XML，不启动 PowerPoint、不调 COM。

用法：
    python scripts/analyze_reference.py                       # 默认读 assets/templates/references
    python scripts/analyze_reference.py --ref-dir <目录> --out-dir <目录>
    python scripts/analyze_reference.py --file assets/templates/references/xxx.pptx

输出：<out-dir>/<slug>.json（逐页明细）、_all.json（汇总）、_mapping.json（卡片映射与配色字号量化）
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
EMU = 914400.0
CHART_KINDS = ("barChart", "pieChart", "lineChart", "doughnutChart", "scatterChart", "areaChart", "radarChart")
KIND_CN = {"pic": "图", "sp": "形", "grp": "组", "gf": "框"}


def geom_of(node):
    off = node.find(f".//{A}off")
    ext = node.find(f".//{A}ext")
    if off is None or ext is None:
        return None
    try:
        return (int(off.get("x")) / EMU, int(off.get("y")) / EMU,
                int(ext.get("cx")) / EMU, int(ext.get("cy")) / EMU)
    except (TypeError, ValueError):
        return None


def analyse_deck(path: Path, slug: str) -> dict:
    z = zipfile.ZipFile(path)
    names = z.namelist()
    order = []
    if "ppt/presentation.xml" in names and "ppt/_rels/presentation.xml.rels" in names:
        rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"',
                               z.read("ppt/_rels/presentation.xml.rels").decode("utf-8", "replace")))
        for rid in re.findall(r'<p:sldId[^>]*r:id="([^"]+)"',
                              z.read("ppt/presentation.xml").decode("utf-8", "replace")):
            m = re.search(r"slide(\d+)\.xml", rels.get(rid, ""))
            if m:
                order.append(f"ppt/slides/slide{m.group(1)}.xml")
    if not order:
        order = sorted([n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)],
                       key=lambda n: int(re.findall(r"\d+", n)[0]))

    chart_kinds = collections.Counter()
    for n in names:
        if re.fullmatch(r"ppt/charts/chart\d+\.xml", n):
            cx = z.read(n).decode("utf-8", "replace")
            for k in CHART_KINDS:
                if f"<c:{k}" in cx:
                    chart_kinds[k] += 1
                    break

    slides, layouts = [], collections.Counter()
    for i, n in enumerate(order, 1):
        root = ET.fromstring(z.read(n))
        tree = root.find(f".//{P}cSld/{P}spTree")
        relpath = n.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
        relmap = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"',
                                 z.read(relpath).decode("utf-8", "replace"))) if relpath in names else {}
        lay = ""
        for tgt in relmap.values():
            if "slideLayout" in tgt:
                lay = tgt.split("/")[-1]
                layouts[lay] += 1
                break
        st = {"slide": i, "layout": lay, "sp": 0, "pic": 0, "grp": 0, "gf": 0, "tbl": 0, "chart": 0,
              "chars": 0, "size_max": 0, "size_min": 0, "tblocks": 0, "big_short": False,
              "geom": collections.Counter(), "colors": collections.Counter(), "kinds": [], "pic_area": [],
              "transition": root.find(f".//{P}transition") is not None,
              "anim": root.find(f".//{P}timing") is not None}
        if tree is not None:
            for sp in tree.iter(f"{P}sp"):
                st["sp"] += 1
                pg = sp.find(f".//{A}prstGeom")
                if pg is not None and pg.get("prst"):
                    st["geom"][pg.get("prst")] += 1
                local = 0
                for rpr in sp.iter(f"{A}rPr"):
                    s = rpr.get("sz")
                    if s:
                        v = int(s) / 100.0
                        local = max(local, v)
                        st["size_max"] = max(st["size_max"], v)
                        st["size_min"] = v if st["size_min"] == 0 else min(st["size_min"], v)
                for c in sp.iter(f"{A}srgbClr"):
                    st["colors"][c.get("val", "").upper()] += 1
                tx = "".join(t.text or "" for t in sp.iter(f"{A}t")).strip()
                if tx:
                    st["tblocks"] += 1
                    if local >= 36 and len(tx) <= 6:
                        st["big_short"] = True
            st["grp"] = len(list(tree.iter(f"{P}grpSp")))
            for pic in tree.iter(f"{P}pic"):
                st["pic"] += 1
                g = geom_of(pic)
                st["pic_area"].append(round(g[2] * g[3] / (13.333 * 7.5), 2) if g else 0.0)
            for gf in tree.iter(f"{P}graphicFrame"):
                st["gf"] += 1
                if gf.find(f".//{A}tbl") is not None:
                    st["tbl"] += 1
                if any(el.tag.endswith("}chart") for el in gf.iter()):
                    st["chart"] += 1
            st["chars"] = len("".join(t.text or "" for t in tree.iter(f"{A}t")).strip())
            for node in list(tree):
                tag = node.tag
                st["kinds"].append("sp" if tag == f"{P}sp" else "pic" if tag == f"{P}pic"
                                   else "grp" if tag == f"{P}grpSp" else "gf" if tag == f"{P}graphicFrame" else "?")
        seq = []
        for k in st["kinds"]:
            if k == "?":
                continue
            if seq and seq[-1][0] == k:
                seq[-1][1] += 1
            else:
                seq.append([k, 1])
        st["layer_order"] = " → ".join(f"{KIND_CN.get(k, k)}{'' if c == 1 else '×' + str(c)}" for k, c in seq)
        st["bigness"] = round(sum(1 for a in st["pic_area"] if a >= 0.25) / max(1, len(st["pic_area"])), 2) \
            if st["pic_area"] else 0
        st["ncolors"] = len(st["colors"])
        st["geom"] = dict(st["geom"].most_common(5))
        st["colors"] = dict(st["colors"].most_common(5))
        slides.append(st)

    n = len(slides) or 1
    total_pics = sum(s["pic"] for s in slides)
    big_pics = sum(1 for s in slides for a in s["pic_area"] if a >= 0.25)
    roles = []
    for st in slides:
        if st["slide"] == 1:
            roles.append("封面")
        elif st["chars"] <= 14 and st["size_max"] >= 36:
            roles.append("章节/大字页")
        elif st["slide"] == len(slides):
            roles.append("结尾页")
        elif st["tbl"] or st["chart"]:
            roles.append("数据页")
        elif st["pic"] and st["chars"] < 70:
            roles.append("图主导页")
        elif st["chars"] >= 150:
            roles.append("密集内容页")
        else:
            roles.append("内容页")

    def card_of(p):
        r = p["角色"]
        if r in ("封面", "章节/大字页", "结尾页"):
            return "cover-title"
        if p["表"] or p["图表"]:
            return "layout-data-dash"
        if p["大字短文本"] and p["文本块"] <= 4:
            return "metric-highlight"
        if r == "图主导页":
            return "整页视觉（cover-full-image）"
        if p["文本块"] >= 4:
            return "layout-sidebar-nav"
        if p["文本块"] == 2:
            return "layout-two-column"
        return "layout-sidebar-nav"

    slide_meta = [{"页": s["slide"], "角色": roles[idx], "映射卡片": card_of({"角色": roles[idx], "表": s["tbl"],
                    "图表": s["chart"], "大字短文本": s["big_short"], "文本块": s["tblocks"]}),
                   "版式": s["layout"], "形": s["sp"], "组": s["grp"], "图": s["pic"], "框": s["gf"],
                   "表": s["tbl"], "图表": s["chart"], "大图占比": s["bigness"], "字": s["chars"],
                   "文本块": s["tblocks"], "色数": s["ncolors"], "大字短文本": s["big_short"],
                   "最大字号": s["size_max"], "最小字号": s["size_min"],
                   "图层顺序": s["layer_order"], "几何": s["geom"], "用色": list(s["colors"])[:4]}
                  for idx, s in enumerate(slides)]

    return {
        "summary": {
            "slug": slug, "file": path.name, "bytes": path.stat().st_size, "pages": len(slides),
            "avg_shapes": round(sum(s["sp"] for s in slides) / n, 1),
            "avg_groups": round(sum(s["grp"] for s in slides) / n, 1),
            "avg_pics": round(total_pics / n, 1),
            "big_pic_ratio": round(big_pics / max(1, total_pics), 2),
            "avg_chars": round(sum(s["chars"] for s in slides) / n, 1),
            "avg_tblocks": round(sum(s["tblocks"] for s in slides) / n, 1),
            "avg_colors": round(sum(s["ncolors"] for s in slides) / n, 1),
            "table_pages": sum(1 for s in slides if s["tbl"]),
            "chart_pages": sum(1 for s in slides if s["chart"]),
            "chart_kinds": dict(chart_kinds),
            "transition_pages": sum(1 for s in slides if s["transition"]),
            "anim_pages": sum(1 for s in slides if s["anim"]),
            "distinct_layouts": len(layouts),
            "role_sequence": roles,
            "title_sizes": sorted({s["size_max"] for s in slides if s["size_max"]}),
            "body_sizes": sorted({s["size_min"] for s in slides if s["size_min"]})[:8],
            "geom_top": dict(collections.Counter(k for s in slides for k, v in s["geom"].items()
                                                for _ in range(v)).most_common(10)),
        },
        "slides": slide_meta,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-dir", default=str(ROOT / "assets" / "templates" / "references"))
    ap.add_argument("--out-dir", default=str(ROOT / "knowledge" / "reference_analysis" / "data"))
    ap.add_argument("--file", help="只分析单份参考稿")
    a = ap.parse_args()

    ref_dir = Path(a.ref_dir)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [Path(a.file)] if a.file else sorted(
        [p for p in ref_dir.iterdir() if p.suffix.lower() in (".pptx", ".pdf")])
    index = ROOT / "assets" / "style-index.json"
    slug_of = {}
    if index.exists():
        for st in json.loads(index.read_text(encoding="utf-8"))["styles"]:
            for f in st.get("source_files", []):
                slug_of[f] = st["name"]

    summaries, mapping, failures, used = [], collections.Counter(), [], set()
    for p in targets:
        # 条目名：仅在映射到参考稿提取条目（ref-*）时用它；否则用文件名（保留中文，只剔非法字符），并保证唯一
        mapped = slug_of.get(p.name) or ""
        base = mapped if mapped.startswith("ref-") else \
            (re.sub(r'[\\/:*?"<>|]+', "-", p.stem).strip("-") or "sample")
        slug, k = base, 2
        while slug in used:
            slug, k = f"{base}-{k}", k + 1
        used.add(slug)
        try:
            if p.suffix.lower() == ".pdf":
                raise ValueError("PDF：请先用同设计的 pptx 分析（本脚本只解析 pptx）")
            if p.stat().st_size < 5000:
                raise ValueError(f"文件损坏（仅 {p.stat().st_size} 字节）")
            r = analyse_deck(p, slug)
            (out_dir / f"{slug}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            summaries.append(r["summary"])
            per = collections.Counter(s["映射卡片"] for s in r["slides"])
            for k, v in per.items():
                mapping[k] += v
            print(f"[OK ] {slug:24s} {r['summary']['pages']:>3}页 形/页{r['summary']['avg_shapes']:>6} "
                  f"组/页{r['summary']['avg_groups']:>5} 图/页{r['summary']['avg_pics']:>5} "
                  f"字/页{r['summary']['avg_chars']:>6} 色数/页{r['summary']['avg_colors']:>5} "
                  f"表页{r['summary']['table_pages']:>2} 图页{r['summary']['chart_pages']:>2}")
            print(f"      映射：{dict(per)}")
        except Exception as e:
            failures.append({"file": p.name, "error": f"{type(e).__name__}: {e}"})
            print(f"[FAIL] {p.name} :: {type(e).__name__}: {e}")

    total = sum(s["pages"] for s in summaries)
    dyn = sum(v for k, v in mapping.items() if not k.startswith("整页视觉"))
    (out_dir / "_all.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "_mapping.json").write_text(json.dumps({
        "total_pages": total, "mapped_pages": dyn,
        "coverage": round(dyn / total, 3) if total else 0,
        "distribution": dict(mapping), "failures": failures,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总：{len(summaries)} 份 / {total} 页｜可映射到已卡片化结构 {dyn} 页"
          f"（{(dyn/total*100 if total else 0):.0f}%）｜失败 {len(failures)} 份")
    print(f"输出目录：{out_dir}")


if __name__ == "__main__":
    main()