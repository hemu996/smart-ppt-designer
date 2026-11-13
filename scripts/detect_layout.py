#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""排版静态检测 + 原生对象核对（工作流第 10 步，v5.1）。

用法：
    python scripts/detect_layout.py output/deck.pptx --config assets/config.json --out output/check_report.md
    python scripts/detect_layout.py output/deck.pptx --json output/check_report.json

检测：越界 / 溢出 / 遮挡 / 字体白名单 / 字号下限 / **讲者备注缺失** / **图表分类是否为业务名**，
并核对原生深度：母版、原生图表、原生表格、图片与特效数量。

设计约束（红线）：**不启动 PowerPoint、不调用 COM**，只解压 .pptx 静态解析 XML。
退出码：0 = 无 error；1 = 存在 error；2 = 文件无法解析。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}
EMU_PER_IN = 914400
DEFAULT_CANVAS_IN = (13.333, 7.5)


class Shape:
    __slots__ = ("idx", "name", "kind", "geom", "text", "fonts", "sizes")

    def __init__(self, idx, name, kind, geom, text, fonts, sizes):
        self.idx = idx
        self.name = name
        self.kind = kind
        self.geom = geom
        self.text = text
        self.fonts = fonts
        self.sizes = sizes

    @property
    def is_text(self) -> bool:
        return bool(self.text.strip())

    @property
    def area(self) -> float:
        if not self.geom:
            return 0.0
        return max(0.0, self.geom[2]) * max(0.0, self.geom[3])


def emu_to_in(value) -> float:
    try:
        return int(value) / EMU_PER_IN
    except (TypeError, ValueError):
        return 0.0


def load_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def slide_size(zf: zipfile.ZipFile):
    try:
        root = ET.fromstring(zf.read("ppt/presentation.xml"))
        sz = root.find("p:sldSz", NS)
        if sz is not None:
            return emu_to_in(sz.get("cx")), emu_to_in(sz.get("cy"))
    except Exception:
        pass
    return DEFAULT_CANVAS_IN


def slide_names(zf: zipfile.ZipFile) -> list[str]:
    names = [n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]

    def key(n):
        m = re.search(r"(\d+)", n.rsplit("/", 1)[-1])
        return int(m.group(1)) if m else 0

    return sorted(names, key=key)


def shape_geometry(elem):
    xfrm = elem.find(".//a:xfrm", NS)
    if xfrm is None:
        xfrm = elem.find(".//p:xfrm", NS)
    if xfrm is None:
        return None
    off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return emu_to_in(off.get("x")), emu_to_in(off.get("y")), emu_to_in(ext.get("cx")), emu_to_in(ext.get("cy"))


def intersect_area(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    dx = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    dy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    return dx * dy


def parse_slide(zf: zipfile.ZipFile, name: str) -> list[Shape]:
    root = ET.fromstring(zf.read(name))
    shapes: list[Shape] = []
    idx = 0
    for tag, kind in (("p:sp", "sp"), ("p:pic", "pic"), ("p:graphicFrame", "graphicFrame"), ("p:cxnSp", "cxnSp")):
        for elem in root.iter(tag.replace("p:", "{http://schemas.openxmlformats.org/presentationml/2006/main}")):
            idx += 1
            c = elem.find(".//p:cNvPr", NS)
            label = c.get("name") if c is not None else f"{kind}{idx}"
            text = "".join((t.text or "") for t in elem.findall(".//a:t", NS))
            fonts = []
            for ftag in ("a:latin", "a:ea", "a:cs"):
                for f in elem.findall(f".//{ftag}", NS):
                    tf = f.get("typeface")
                    if tf and tf not in fonts:
                        fonts.append(tf)
            sizes = [int(r.get("sz")) / 100.0 for r in elem.findall(".//a:rPr", NS) if r.get("sz")]
            shapes.append(Shape(idx, label, kind, shape_geometry(elem), text, fonts, sizes))
    return shapes


def estimate_text_capacity(text, box_w, box_h, font_pt, line_ratio) -> dict:
    w_pt, h_pt = box_w * 72.0, box_h * 72.0
    chars_per_line = max(1, int(w_pt / max(1.0, font_pt)))
    needed_lines = max(1, math.ceil(len(text) / chars_per_line))
    needed_h_pt = needed_lines * font_pt * line_ratio
    return {"chars_per_line": chars_per_line, "needed_lines": needed_lines,
            "needed_h_pt": needed_h_pt, "available_h_pt": h_pt,
            "ratio": (needed_h_pt / h_pt) if h_pt else 0.0}


def analyse_notes(zf: zipfile.ZipFile, slide_count: int, issues: list, report: dict) -> None:
    notes = [n for n in zf.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]
    nonempty = 0
    for n in notes:
        try:
            text = "".join((t.text or "") for t in ET.fromstring(zf.read(n)).findall(".//a:t", NS)).strip()
            if len(text) >= 10:
                nonempty += 1
        except Exception:
            continue
    report["notes_slides"] = len(notes)
    report["notes_nonempty"] = nonempty
    if nonempty < slide_count:
        issues.append({
            "slide": 0, "level": "error", "kind": "讲者备注缺失",
            "element": f"notesSlide {nonempty}/{slide_count}",
            "detail": f"仅 {nonempty} 页有非空讲者备注（红线第 14 条：每页必须有）",
            "advice": "回到页面计划补齐 notes 字段并重新构建",
        })


def analyse_charts(zf: zipfile.ZipFile, issues: list, report: dict) -> None:
    charts = sorted([n for n in zf.namelist() if re.fullmatch(r"ppt/charts/chart\d+\.xml", n)],
                    key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)))
    report["charts"] = len(charts)
    for n in charts:
        try:
            xml = zf.read(n).decode("utf-8", "replace")
        except Exception:
            continue
        cats = re.findall(r"<c:cat>(.*?)</c:cat>", xml, re.S)
        names = []
        for block in cats:
            names += re.findall(r"<c:v>([^<]*)</c:v>", block)
        numeric_only = bool(names) and all(re.fullmatch(r"\d+(\.\d+)?", x.strip()) for x in names)
        if numeric_only:
            issues.append({
                "slide": 0, "level": "error", "kind": "图表分类为数字占位",
                "element": n.rsplit("/", 1)[-1],
                "detail": f"分类轴取值为纯数字：{names[:5]}（应为业务名称）",
                "advice": "在页面计划的 chart.labels 写业务名后重新构建；渲染端把分类显示成序号即为此问题",
            })


def analyse_tables(zf: zipfile.ZipFile, issues: list, report: dict) -> None:
    count = 0
    for n in slide_names(zf):
        try:
            count += len(ET.fromstring(zf.read(n)).findall(".//a:tbl", NS))
        except Exception:
            continue
    report["tables"] = count


def analyse_media(zf: zipfile.ZipFile, report: dict) -> None:
    media = [n for n in zf.namelist() if n.startswith("ppt/media/") and not n.endswith("/")]
    report["media"] = len(media)
    masters = [n for n in zf.namelist() if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", n)]
    layouts = [n for n in zf.namelist() if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)]
    report["masters"] = len(masters)
    report["layouts"] = len(layouts)
    if not layouts:
        report["layouts"] = 0


def analyse(pptx: Path, cfg: dict) -> dict:
    th = cfg.get("layout_thresholds", {})
    fonts_cfg = cfg.get("fonts", {})
    tol = float(th.get("tolerance_in", 0.02))
    gap_min = float(th.get("min_gap_in", 0.05))
    min_pt = float(fonts_cfg.get("min_pt", 10))
    line_ratio = float(th.get("line_height_ratio", 1.35))
    overlap_ignore = float(th.get("overlap_ignore_ratio", 0.15))
    overlap_min_area = float(th.get("overlap_min_area_in2", 0.12))
    max_title_lines = int(th.get("max_title_lines", 2))
    whitelist = set(fonts_cfg.get("whitelist", []))

    issues: list[dict] = []
    report: dict = {}
    fonts_seen, sizes_seen = set(), set()

    with zipfile.ZipFile(pptx) as zf:
        width, height = slide_size(zf)
        slides = slide_names(zf)
        if not slides:
            raise ValueError("没有找到任何幻灯片（ppt/slides/*.xml）")

        analyse_notes(zf, len(slides), issues, report)
        analyse_charts(zf, issues, report)
        analyse_tables(zf, issues, report)
        analyse_media(zf, report)

        for order, sname in enumerate(slides, start=1):
            shapes = parse_slide(zf, sname)
            canvas_area = width * height
            for sh in shapes:
                if not sh.geom:
                    continue
                x, y, w, h = sh.geom
                fonts_seen.update(sh.fonts)
                sizes_seen.update(sh.sizes)
                if sh.area >= canvas_area * 0.95:
                    continue
                if x < -tol or y < -tol or x + w > width + tol or y + h > height + tol:
                    issues.append({"slide": order, "level": "error", "kind": "越界", "element": sh.name,
                                   "detail": f"({x:.3f},{y:.3f},{w:.3f}×{h:.3f})in 超出画布 {width:.3f}×{height:.3f}in",
                                   "advice": "缩小尺寸或回移坐标，留出安全边距"})
                for font in sh.fonts:
                    if whitelist and font not in whitelist:
                        issues.append({"slide": order, "level": "error", "kind": "字体不在白名单", "element": sh.name,
                                       "detail": f"字体 {font!r} 不在白名单", "advice": "改用白名单内字体"})
                for size in sh.sizes:
                    if size < min_pt:
                        issues.append({"slide": order, "level": "error", "kind": "字号过小", "element": sh.name,
                                       "detail": f"字号 {size:g}pt < 下限 {min_pt:g}pt", "advice": "投影场景下不可读，请加大或精简文案"})
                if sh.is_text and sh.sizes:
                    body_pt = max(sh.sizes)
                    est = estimate_text_capacity(sh.text, w, h, body_pt, line_ratio)
                    if est["ratio"] > 1.15:
                        issues.append({"slide": order, "level": "error", "kind": "文本可能溢出", "element": sh.name,
                                       "detail": f"{len(sh.text)} 字 / 约 {est['chars_per_line']} 字每行 = {est['needed_lines']} 行，需约 {est['needed_h_pt'] / 72:.2f}in，框高 {h:.2f}in（估算）",
                                       "advice": "增大 h_in/w_in、减小字号或精简文案"})
                    elif est["ratio"] > 1.0:
                        issues.append({"slide": order, "level": "warning", "kind": "文本临界溢出", "element": sh.name,
                                       "detail": f"估算占用 {est['ratio'] * 100:.0f}% 框高", "advice": "建议留 20% 余量"})
                    if body_pt >= 24 and est["needed_lines"] > max_title_lines:
                        issues.append({"slide": order, "level": "warning", "kind": "标题超行", "element": sh.name,
                                       "detail": f"标题估算 {est['needed_lines']} 行 > {max_title_lines}", "advice": "压缩文案或加大 w_in"})

            boxed = [s for s in shapes if s.geom and 0 < s.area < canvas_area * 0.95]
            for i in range(len(boxed)):
                for j in range(i + 1, len(boxed)):
                    a, b = boxed[i], boxed[j]
                    inter = intersect_area(a.geom, b.geom)
                    if inter <= 0:
                        continue
                    smaller = min(a.area, b.area)
                    if smaller < overlap_min_area:
                        continue
                    ratio = inter / smaller
                    if ratio <= overlap_ignore:
                        continue
                    if str(a.name).startswith("COMPOSITION#") or str(b.name).startswith("COMPOSITION#"):
                        issues.append({"slide": order, "level": "info", "kind": "构图衬底叠压",
                                       "element": f"{a.name} × {b.name}",
                                       "detail": f"构图背板（衬底）与上层元素重叠 {ratio * 100:.0f}%，属正常分层",
                                       "advice": "背板为半透明衬底，确认上层内容可读即可（构图硬约束②）"})
                        continue
                    _lower, _upper = (a, b) if a.idx < b.idx else (b, a)
                    if _lower.area >= _upper.area * 1.2 and _lower.area >= canvas_area / 8.0:
                        issues.append({"slide": order, "level": "info", "kind": "衬底叠压",
                                       "element": f"{_lower.name} × {_upper.name}",
                                       "detail": f"较大的衬底在下（先画）、较小元素在上（重叠 {ratio * 100:.0f}%），上层完全可见，属正常分层叠压",
                                       "advice": "确认上层内容可读、与衬底对比度足够即可（构图硬约束②）"})
                        continue
                    if ratio > 0.9 and (a.is_text != b.is_text):
                        issues.append({"slide": order, "level": "info", "kind": "色块承载文字",
                                       "element": f"{a.name} × {b.name}",
                                       "detail": f"文本框完整落在色块内（覆盖 {ratio * 100:.0f}%），属正常叠加",
                                       "advice": "确认文字与底色对比度足够即可"})
                        continue
                    if b.is_text and str(a.name).startswith(("DSET#", "DTEX#")):
                        issues.append({"slide": order, "level": "info", "kind": "装饰衬底文字",
                                       "element": f"{a.name} × {b.name}",
                                       "detail": f"装饰在下、文字在上（重叠 {ratio * 100:.0f}%），属正常衬底",
                                       "advice": "确认文字与衬底对比度足够即可"})
                        continue
                    if str(a.name).startswith("DSET#") and str(b.name).startswith("DSET#"):
                        issues.append({"slide": order, "level": "info", "kind": "装饰层内叠",
                                       "element": f"{a.name} × {b.name}",
                                       "detail": f"同一装饰组内图元叠加（覆盖 {ratio * 100:.0f}%），属正常分层",
                                       "advice": "装饰组内允许底块 + 细线分层，无需错开"})
                        continue
                    issues.append({"slide": order, "level": "error" if ratio > 0.35 else "warning",
                                   "kind": "元素遮挡", "element": f"{a.name} × {b.name}",
                                   "detail": f"重叠面积占较小元素 {ratio * 100:.0f}%（阈值 {overlap_ignore * 100:.0f}%）",
                                   "advice": f"错开位置，元素间保留 ≥ {gap_min}in 间隙"})

    issues.sort(key=lambda i: (i["level"] != "error", i["slide"]))
    return {
        "file": str(pptx), "canvas_in": [round(width, 3), round(height, 3)],
        "slide_count": len(slides), "issues": issues,
        "fonts_seen": sorted(fonts_seen), "sizes_seen": sorted(sizes_seen),
        "native": report,
        "counts": {
            "error": sum(1 for i in issues if i["level"] == "error"),
            "warning": sum(1 for i in issues if i["level"] == "warning"),
            "info": sum(1 for i in issues if i["level"] == "info"),
        },
    }


def render_markdown(r: dict) -> str:
    n = r["native"]
    lines = [
        "# 排版检测报告", "",
        f"- 文件：`{r['file']}`",
        f"- 画布：{r['canvas_in'][0]}in × {r['canvas_in'][1]}in，共 {r['slide_count']} 页",
        f"- 结果：**error {r['counts']['error']} 项 / warning {r['counts']['warning']} 项 / info {r['counts']['info']} 项**", "",
        "## 原生对象核对", "",
        f"- 母版/版式：{n.get('masters', 0)} 个母版 + {n.get('layouts', 0)} 个自定义版式（内页应从自定义版式生成）",
        f"- 原生图表：{n.get('charts', 0)} 个（应能在 PowerPoint 中“编辑数据”）",
        f"- 原生表格：{n.get('tables', 0)} 个（应能改单元格）",
        f"- 讲者备注：{n.get('notes_nonempty', 0)}/{r['slide_count']} 页非空",
        f"- 图片对象：{n.get('media', 0)} 张", "",
        "> 本报告为静态 XML 解析的估算结果，不修改原文件；不启动 PowerPoint、不调用 COM。", "",
    ]
    if not r["issues"]:
        lines += ["## 检测结果", "", "未发现越界、溢出、遮挡、字体、字号、备注缺失或图表分类问题。", ""]
    else:
        by_slide: dict[int, list] = {}
        for it in r["issues"]:
            by_slide.setdefault(it["slide"], []).append(it)
        lines += ["## 问题清单", ""]
        for sid in sorted(by_slide):
            title = "全局" if sid == 0 else f"第 {sid} 页"
            lines += [f"### {title}", "", "| 级别 | 类型 | 元素 | 说明 | 建议 |", "|---|---|---|---|---|"]
            for it in by_slide[sid]:
                lines.append(f"| {it['level']} | {it['kind']} | {it['element']} | {it['detail']} | {it['advice']} |")
            lines.append("")
    lines += [
        "## 附录：检测到的字体与字号", "",
        f"- 字体：{', '.join(r['fonts_seen']) or '（未检测到显式字体）'}",
        f"- 字号：{', '.join(f'{s:g}pt' for s in r['sizes_seen']) or '（未检测到显式字号）'}", "",
        "## 人工终审建议", "",
        "1. 先处理所有 error（越界/溢出/遮挡/字体/字号/备注缺失/图表分类）。",
        "2. warning 逐条判断：标题超行与临界溢出建议一并修掉。",
        "3. 修改后在 PowerPoint 里另存为新文件，再重跑本脚本确认问题收敛。",
        "4. 视觉美观维度（层级/对齐/留白/对比度/一致性）不在本脚本范围内，建议按 references/evaluation-rubric.md 第二节逐页复核。",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="PPTX 排版静态检测与原生对象核对")
    ap.add_argument("pptx")
    ap.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "assets" / "config.json"))
    ap.add_argument("--out", default="check_report.md")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    pptx = Path(args.pptx)
    if not pptx.is_file():
        print(f"[FAIL] 文件不存在：{pptx}")
        return 2
    cfg = load_config(Path(args.config))
    try:
        r = analyse(pptx, cfg)
    except Exception as exc:
        print(f"[FAIL] 无法解析 PPTX：{exc}")
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(r), encoding="utf-8")
    if args.json_out:
        jp = Path(args.json_out)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"检测完成：{r['slide_count']} 页｜error {r['counts']['error']} / warning {r['counts']['warning']} / info {r['counts']['info']}")
    print(f"  原生：母版 {r['native'].get('masters', 0)}｜图表 {r['native'].get('charts', 0)}｜表格 {r['native'].get('tables', 0)}｜备注 {r['native'].get('notes_nonempty', 0)}/{r['slide_count']}｜图片 {r['native'].get('media', 0)}")
    print(f"  报告：{out}")
    for it in r["issues"][:20]:
        print(f"  [第{it['slide']}页][{it['level']}] {it['kind']} - {it['element']}：{it['detail']}")
    return 1 if r["counts"]["error"] else 0


if __name__ == "__main__":
    sys.exit(main())