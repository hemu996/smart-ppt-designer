#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从参考 PPTX / PDF 提取视觉系统（风格库构建工具，v5.6）

用途：给一份参考稿（.pptx / .pdf），产出可直接被构建脚本调用的视觉系统 JSON，
     以及一份人可读的风格卡片（markdown）。

用法：
    python scripts/extract_style.py <参考文件> --name ref-tea-green --out assets/visual-systems/ref-tea-green.json
    python scripts/extract_style.py --batch .dumate/inbox --out-dir assets/visual-systems --card-dir assets/style-cards

说明：提取是启发式的——配色按出现频次与饱和度选主色/强调色，字体映射到 config.json 白名单，
     字号层级沿用技能包标准档位。结果标注 extraction.confidence，低置信度建议人工微调。
"""
from __future__ import annotations

import argparse
import colorsys
import collections
import json
import re
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "assets" / "config.json").read_text(encoding="utf-8"))
WHITELIST = CONFIG["fonts"]["whitelist"]
THEME_TAGS = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6")

TIERS = {
    "title_size": [36, 44], "section_size": [28, 32], "page_title_size": [20, 24],
    "module_size": [16, 18], "body_size": [13, 15], "caption_size": [10, 11], "metric_size": [40, 60],
}
GRID = {"columns": 12, "margin_cols": 1, "unit_cm": 0.3, "unit_in": 0.1181,
        "tolerance_in": 0.02, "content_x_in": 1.38, "content_w_in": 11.45}
LAYERS = {"L1_background": 0, "L2_decoration": [10, 19], "L3_content": [20, 29], "L4_title": [30, 39],
          "notes": "构建脚本按 z_index 升序绘制；装饰层不得高于内容层（红线第 11 条）"}

FONT_MAP = (
    (("思源黑体", "Source Han Sans"), "思源黑体"),
    (("Source Han Serif", "宋体", "SimSun", "标宋", "Song"), "宋体"),
    (("雅黑", "YaHei"), "微软雅黑"),
    (("黑体", "SimHei"), "黑体"),
    (("Arial", "Calibri"), "Arial"),
)


def rgb_of(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hsv(h):
    r, g, b = rgb_of(h)
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def lum(h):
    r, g, b = rgb_of(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def hue_dist(a, b):
    d = abs(a - b)
    return min(d, 1 - d)


def shade(h, k):
    r, g, b = rgb_of(h)
    f = lambda v: max(0, min(255, int(v * k)))
    return "%02X%02X%02X" % (f(r), f(g), f(b))


def map_font(name: str) -> str:
    if not name:
        return CONFIG["fonts"]["default_cn"]
    if name in WHITELIST:
        return name
    for keys, target in FONT_MAP:
        if any(k in name for k in keys):
            return target
    return CONFIG["fonts"]["default_cn"]


def harvest(xml: str, colors, fonts, sizes):
    for c in re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', xml):
        colors[c.upper()] += 1
    for t in re.findall(r'typeface="([^"]+)"', xml):
        if not t.startswith("+"):
            fonts[t] += 1
    for s in re.findall(r'sz="(\d+)"', xml):
        sizes[int(s) / 100] += 1


def read_pptx(p: Path) -> dict:
    z = zipfile.ZipFile(p)
    names = z.namelist()
    slides = [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    colors, fonts, sizes = collections.Counter(), collections.Counter(), collections.Counter()
    m_colors, m_fonts, m_sizes = collections.Counter(), collections.Counter(), collections.Counter()
    tables = charts = shapes = 0
    for n in slides:
        x = z.read(n).decode("utf-8", "replace")
        harvest(x, colors, fonts, sizes)
        tables += len(re.findall(r"<a:tbl>", x))
        shapes += len(re.findall(r"<p:sp>", x))
    for n in names:
        if re.fullmatch(r"ppt/slide(?:Layouts|Masters)/\w+\.xml", n):
            harvest(z.read(n).decode("utf-8", "replace"), m_colors, m_fonts, m_sizes)
    # 整页铺底填充色（p:bg 或铺满画布的矩形）→ 用于判定底色与明暗模式
    bg_cands = collections.Counter()
    for n in names:
        if not re.fullmatch(r"ppt/slides/slide\d+\.xml|ppt/slide(?:Layouts|Masters)/\w+\.xml", n):
            continue
        x = z.read(n).decode("utf-8", "replace")
        for m in re.finditer(r"<p:bg>(.*?)</p:bg>", x, re.S):
            c = re.search(r'srgbClr val="([0-9A-Fa-f]{6})"', m.group(1))
            if c:
                bg_cands[c.group(1).upper()] += 5
        for sp in re.finditer(r"<p:sp>.*?</p:sp>", x, re.S):
            blk = sp.group(0)
            off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', blk)
            ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', blk)
            if not (off and ext):
                continue
            if abs(int(off.group(1))) < 120000 and abs(int(off.group(2))) < 120000 \
               and int(ext.group(1)) >= 11000000 and int(ext.group(2)) >= 6200000:
                c = re.search(r'srgbClr val="([0-9A-Fa-f]{6})"', blk)
                if c:
                    bg_cands[c.group(1).upper()] += 3
    from_masters = sum(colors.values()) + sum(fonts.values()) < 40
    if from_masters:
        colors.update(m_colors)
        fonts.update(m_fonts)
        sizes.update(m_sizes)
    theme = {}
    if "ppt/theme/theme1.xml" in names:
        th = z.read("ppt/theme/theme1.xml").decode("utf-8", "replace")
        for t in THEME_TAGS:
            m = re.search(r"<a:%s>.*?val=\"([0-9A-Fa-f]{6})\"" % t, th, re.S)
            if m:
                theme[t] = m.group(1).upper()
    canvas = [13.333, 7.5]
    if "ppt/presentation.xml" in names:
        m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"',
                      z.read("ppt/presentation.xml").decode("utf-8", "replace"))
        if m:
            canvas = [round(int(m.group(1)) / 914400, 3), round(int(m.group(2)) / 914400, 3)]
    media = len([n for n in names if n.startswith("ppt/media/") and not n.endswith("/")])
    return {"kind": "pptx", "pages": len(slides), "canvas": canvas, "theme": theme,
            "bg": (bg_cands.most_common(1)[0][0] if bg_cands else None),
            "colors": colors, "fonts": fonts, "sizes": sizes,
            "counts": {"shapes": shapes, "tables": tables,
                       "charts": len([n for n in names if re.fullmatch(r"ppt/charts/chart\d+\.xml", n)]),
                       "media": media},
            "from_masters": from_masters}


def read_pdf(p: Path) -> dict:
    import fitz
    from PIL import Image
    import io
    doc = fitz.open(p)
    colors = collections.Counter()
    fonts = collections.Counter()
    for i in range(min(4, doc.page_count)):
        pm = doc[i].get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        im = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB").resize((140, 79))
        q = im.quantize(colors=10, method=Image.Quantize.MEDIANCUT).convert("RGB")
        for cnt, c in sorted(q.getcolors(), reverse=True)[:8]:
            colors["%02X%02X%02X" % c] += cnt
    try:
        for f in doc[0].get_fonts():
            fonts[f[3]] += 1
    except Exception:
        pass
    r = doc[0].rect
    canvas = [round(r.width / 72, 3), round(r.height / 72, 3)]
    pages = doc.page_count
    doc.close()
    return {"kind": "pdf", "pages": pages, "canvas": canvas, "theme": {},
            "colors": colors, "fonts": fonts, "sizes": collections.Counter(),
            "counts": {"note": "PDF：取渲染帧主色；不解析逐页矢量对象"}, "from_masters": False}


def build_system(sig: dict, name: str, label: str, source: str) -> dict:
    colors = sig["colors"]
    if not colors:  # 页面全部使用主题/方案色：用主题色兜底
        for k, v in (sig.get("theme") or {}).items():
            colors[v] += 3 if k.startswith("accent") else 2
        sig["theme_only"] = True
    if not colors:
        colors["44546A"] += 3
        colors["FFFFFF"] += 2
    top = colors.most_common(16)
    # 底色判定：优先用「整页铺底」的填充色（p:bg 或铺满画布的矩形），避免把黑色文字误判成深色底
    bg = sig.get("bg")
    if not bg:
        for c, n in top:
            if lum(c) > 0.92:
                bg = c
                break
        if not bg:
            for c, n in top:
                if lum(c) < 0.12:
                    bg = c
                    break
    bg = bg or (top[0][0] if top else "#111111")
    conf_theme_only = bool(sig.get("theme_only"))
    if lum(bg) > 0.92:
        bg = "#FFFFFF"
    elif lum(bg) < 0.06:
        bg = "#111111"
    dark = lum(bg) < 0.45
    brand = []
    for c, n in top:
        if n < 3:
            continue
        h, s, v = hsv(c)
        if s >= 0.30 and 0.16 < v <= 1.0 and lum(c) > 0.08:
            brand.append((c, n, h, s, v))
    content_brand = list(brand)
    seen = {b[0] for b in brand}
    # 页面自身品牌色不足两种时，才用主题/方案色补充（避免 Office 默认主题色污染提取结果）
    if len(content_brand) < 2:
        for c in sig["theme"].values():
            if c in seen or c == bg:
                continue
            h, s, v = hsv(c)
            if s >= 0.30 and 0.16 < v <= 1.0:
                brand.append((c, 3, h, s, v))
                seen.add(c)
    deep = [b for b in brand if b[4] <= 0.82]
    chosen = (deep or brand or [("#333333", 0, 0, 0, 0)])[0]
    primary, prim_n = chosen[0], chosen[1]
    ph = hsv(primary)[0]
    # 强调色：先按频次设下限（避免个别异色小面积元素把强调色带偏），再在候选里取色相最远者
    pool = [b for b in brand if b[0] != primary and b[1] >= max(3, int(prim_n * 0.25))]
    if not pool:
        pool = [b for b in brand if b[0] != primary]
    accent = primary
    best = -1
    for c, n, h, s, v in pool:
        d = hue_dist(h, ph)
        score = d * 2 + (n / 100.0)
        if d > 0.05 and score > best:
            best, accent = score, c
    if accent == primary and pool:
        accent = pool[0][0]
    text = "#F2F2F2" if dark else "#2E2620"
    text_light = "#B9BDC7" if dark else "#7A6A5A"
    fonts_top = [f for f, _ in sig["fonts"].most_common(4)]
    title_font = map_font(fonts_top[0] if fonts_top else "")
    body_font = map_font(fonts_top[1] if len(fonts_top) > 1 else title_font)
    conf = "high"
    if conf_theme_only:
        conf = "medium（页面无显式色值，配色取自主题/方案色）"
    elif not brand:
        conf = "low（未识别出饱和品牌色，主色为兜底值）"
    elif sig["from_masters"]:
        conf = "medium（配色取自母版/版式，非页面元素）"
    elif sig["kind"] == "pdf":
        conf = "medium（PDF 由渲染帧取色，非矢量精确值）"
    return {
        "system_name": name,
        "label": label,
        "mode": "dark" if dark else "light",
        "usage": f"由参考稿《{source}》自动提取；{label}。适合场景请对照 style-index.json 的 keywords 选用，未确认前不要当默认。",
        "colors": {"primary": "#" + primary, "secondary": "#" + shade(primary, 0.72),
                   "accent": "#" + accent, "background": bg,
                   "text": text, "text_light": text_light},
        "fonts": {"title": title_font, "body": body_font, **TIERS},
        "decorations": {"title_bar": "rule", "card_border": "hairline", "section_divider": "band"},
        "navigation": {"mode": "sidebar", "active_color": "#" + accent, "inactive_color": "#" + shade(accent, 0.55),
                       "text_active": text, "text_inactive": text_light},
        "grid": GRID,
        "icon_style": "solid",
        "transition": "fade",
        "layers": LAYERS,
        "image_style": "humanities" if not dark else "tech",
        "chart_palette": ["#" + c for c, _ in top[:6] if c != bg][:5] or ["#" + primary],
        "density": {"max_modules_per_page": 5, "max_bullets_per_module": 4},
        "extraction": {
            "source_file": source, "method": "zipfile/XML 频次统计（pptx）或渲染帧取色（pdf）",
            "date": date.today().isoformat(), "confidence": conf,
            "signals": {
                "pages": sig["pages"], "canvas_in": sig["canvas"],
                "top_colors": [{"hex": c, "count": n} for c, n in top[:8]],
                "fonts_raw": fonts_top,
                "sizes_pt_top": [s for s, _ in sorted(sig["sizes"].items())[:10]],
                "objects": sig["counts"],
            },
            "note": "自动提取仅供调用起点；标签、适用场景与语义化命名建议人工校订后使用。",
        },
    }


def card_md(sysd: dict, source: str) -> str:
    e = sysd["extraction"]
    c = sysd["colors"]
    return "\n".join([
        f"# 风格卡片：{sysd['label']}（`{sysd['system_name']}`）",
        "",
        f"- **来源参考稿**：`{source}`（{e['signals']['pages']} 页，画布 {e['signals']['canvas_in'][0]}×{e['signals']['canvas_in'][1]} in）",
        f"- **模式**：{'深色' if sysd['mode'] == 'dark' else '浅色'}｜**置信度**：{e['confidence']}",
        f"- **配色**：主色 `{c['primary']}`｜次色 `{c['secondary']}`｜强调 `{c['accent']}`｜底色 `{c['background']}`",
        f"- **字体**：标题 {sysd['fonts']['title']}／正文 {sysd['fonts']['body']}",
        f"- **高频用色（原始信号）**：{', '.join(x['hex'] + '×' + str(x['count']) for x in e['signals']['top_colors'][:6])}",
        f"- **原始字体**：{', '.join(e['signals']['fonts_raw']) or '（未从页面识别，取自母版/版式）'}",
        f"- **版式对象**：{e['signals']['objects']}",
        "",
        "调用方式：把页面计划的 `design_brief.visual_system` 设为该 `system_name`；或按 `style-index.json` 的关键词检索后选用。",
        "注意：自动提取的风格是调用起点，不是成品；标签与适用场景请对照原稿校订，未经确认不得当默认风格。",
        "",
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", nargs="?", help="参考文件路径")
    ap.add_argument("--batch", help="目录：批量处理其中所有 .pptx/.pdf")
    ap.add_argument("--name", help="视觉系统 system_name")
    ap.add_argument("--label", help="中文标签")
    ap.add_argument("--out", help="输出视觉系统 JSON")
    ap.add_argument("--card", help="输出风格卡片 markdown")
    ap.add_argument("--out-dir", default=str(ROOT / "assets" / "visual-systems"))
    ap.add_argument("--card-dir", default=str(ROOT / "assets" / "style-cards"))
    a = ap.parse_args()

    targets = []
    if a.batch:
        d = Path(a.batch)
        targets = sorted([p for p in d.iterdir() if p.suffix.lower() in (".pptx", ".pdf")])
    elif a.ref:
        targets = [Path(a.ref)]
    else:
        ap.error("需要 <参考文件> 或 --batch <目录>")

    results = []
    for p in targets:
        stem = re.sub(r"[^0-9A-Za-z]+", "-", p.stem)[:38].strip("-").lower() or "ref"
        name = a.name or f"ref-{stem}"
        label = a.label or f"参考稿：{p.stem[:24]}"
        try:
            if p.stat().st_size < 5000 and p.suffix.lower() == ".pptx":
                raise ValueError(f"文件疑似损坏（仅 {p.stat().st_size} 字节）")
            sig = read_pptx(p) if p.suffix.lower() == ".pptx" else read_pdf(p)
            sysd = build_system(sig, name, label, p.name)
            out = Path(a.out) if a.out else Path(a.out_dir) / f"{name}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(sysd, ensure_ascii=False, indent=2), encoding="utf-8")
            cardp = Path(a.card) if a.card else Path(a.card_dir) / f"{name}.md"
            cardp.parent.mkdir(parents=True, exist_ok=True)
            cardp.write_text(card_md(sysd, p.name), encoding="utf-8")
            results.append({"file": p.name, "ok": True, "name": name, "label": label,
                            "mode": sysd["mode"], "out": str(out), "card": str(cardp),
                            "colors": sysd["colors"], "confidence": sysd["extraction"]["confidence"],
                            "pages": sig["pages"], "keywords": []})
            print(f"[OK ] {p.name} → {name}（{sysd['mode']}，主色 {sysd['colors']['primary']}，强调 {sysd['colors']['accent']}）")
        except Exception as ex:
            results.append({"file": p.name, "ok": False, "error": f"{type(ex).__name__}: {ex}"})
            print(f"[FAIL] {p.name} :: {type(ex).__name__}: {ex}")

    if a.batch:
        idx = Path(a.out_dir).parent / "style-index.json"
        old = json.loads(idx.read_text(encoding="utf-8")) if idx.exists() else {"styles": [], "failures": []}
        by = {s["name"]: s for s in old.get("styles", [])}
        for r in results:
            if r.get("ok"):
                by[r["name"]] = {k: r[k] for k in ("name", "label", "file", "mode", "colors", "confidence", "pages")} | {"keywords": r["keywords"]}
        old["styles"] = sorted(by.values(), key=lambda x: x["name"])
        old["failures"] = [{"file": r["file"], "error": r["error"]} for r in results if not r.get("ok")]
        idx.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n索引已更新：{idx}")


if __name__ == "__main__":
    main()