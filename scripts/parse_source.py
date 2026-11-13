#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多源材料解析（工作流第 1 步，v5.1）

把 PDF / DOCX / HTML / PPTX / 文本 转成统一的 Markdown 素材（默认 output/source.md），
供后续"提炼论点 + 数据 + 口径"使用。

本脚本只做**结构与文字抽取**，不做总结、不做改写；抽不到内容时如实报告，不编造。

用法：
    python scripts/parse_source.py --input 材料.pdf --out output/source.md
    python scripts/parse_source.py --input 方案.docx --out output/source.md --max-chars 60000

依赖（按需，缺库时给出安装提示，不擅自安装）：
    .pdf  → 优先 PyMuPDF（pymupdf），其次 pypdf
    .docx → python-docx
    .pptx → python-pptx
    .html → 标准库（无需安装）

退出码：0 = 成功；1 = 解析失败；2 = 参数/依赖问题
"""

from __future__ import annotations

import argparse
import html.parser
import re
import sys
from datetime import datetime
from pathlib import Path

MIN_USEFUL_CHARS = 200


class _TextExtractor(html.parser.HTMLParser):
    SKIP = {"script", "style", "head", "title", "nav", "footer", "header", "noscript", "iframe", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0
        self._block = {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br"}

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag in self._block:
            self.parts.append("\n")
        if tag in ("h1", "h2", "h3"):
            self.parts.append("#" * int(tag[1]) + " ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in self._block:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        raw = " ".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def parse_pdf(p: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    try:
        import pymupdf  # noqa
        doc = pymupdf.open(str(p))
        pages = []
        for i, page in enumerate(doc, 1):
            pages.append(f"\n\n<!-- 第 {i} 页 -->\n\n" + page.get_text("text").strip())
        return "".join(pages).strip(), notes
    except ImportError:
        notes.append("未安装 pymupdf，改用 pypdf")
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        pages = []
        for i, page in enumerate(reader.pages, 1):
            pages.append(f"\n\n<!-- 第 {i} 页 -->\n\n" + (page.extract_text() or "").strip())
        return "".join(pages).strip(), notes
    except ImportError:
        raise SystemExit("[FAIL] 缺少 PDF 解析库，请先安装：python -m pip install pymupdf  （或 pypdf）")


def parse_docx(p: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    try:
        import docx  # python-docx
    except ImportError:
        raise SystemExit("[FAIL] 缺少 DOCX 解析库，请先安装：python -m pip install python-docx")
    d = docx.Document(str(p))
    parts: list[str] = []
    for para in d.paragraphs:
        t = (para.text or "").strip()
        if not t:
            continue
        style = (para.style.name or "").lower()
        if style.startswith("heading"):
            level = "".join(ch for ch in style if ch.isdigit()) or "1"
            parts.append("#" * min(6, int(level)) + " " + t)
        else:
            parts.append(t)
    for ti, table in enumerate(d.tables, 1):
        parts.append(f"\n\n<!-- 表格 {ti} -->")
        for row in table.rows:
            parts.append("| " + " | ".join((c.text or "").strip() for c in row.cells) + " |")
    notes.append(f"抽取段落 {len(d.paragraphs)} 个、表格 {len(d.tables)} 个（跳过页眉页脚与批注）")
    return "\n\n".join(parts).strip(), notes


def parse_pptx(p: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    try:
        from pptx import Presentation
    except ImportError:
        raise SystemExit("[FAIL] 缺少 PPTX 解析库，请先安装：python -m pip install python-pptx")
    prs = Presentation(str(p))
    parts: list[str] = []
    for i, slide in enumerate(prs.slides, 1):
        parts.append(f"## 第 {i} 页")
        for sh in slide.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                for line in sh.text_frame.text.splitlines():
                    if line.strip():
                        parts.append(f"- {line.strip()}")
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            parts.append(f"  - 备注：{slide.notes_slide.notes_text_frame.text.strip()[:200]}")
    notes.append(f"抽取 {len(prs.slides)} 页幻灯片文字（可用于风格提取参考）")
    return "\n".join(parts).strip(), notes


def parse_html(p: Path) -> tuple[str, list[str]]:
    ex = _TextExtractor()
    ex.feed(p.read_text(encoding="utf-8", errors="replace"))
    return ex.text(), ["已剔除 script/style/nav/footer/header 等节点"]


def parse_text(p: Path) -> tuple[str, list[str]]:
    return p.read_text(encoding="utf-8", errors="replace").strip(), []


PARSERS = {
    ".pdf": parse_pdf, ".docx": parse_docx, ".doc": parse_docx, ".pptx": parse_pptx,
    ".html": parse_html, ".htm": parse_html,
    ".txt": parse_text, ".md": parse_text, ".markdown": parse_text,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="多源材料解析 → Markdown 素材")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="output/source.md")
    ap.add_argument("--max-chars", type=int, default=120000, help="输出字符上限（超出截断并提示）")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        print(f"[FAIL] 输入文件不存在：{src}")
        return 2
    parser = PARSERS.get(src.suffix.lower())
    if parser is None:
        print(f"[FAIL] 不支持的输入格式：{src.suffix}（支持 .pdf/.docx/.html/.pptx/.txt/.md）")
        return 2

    try:
        body, notes = parser(src)
    except SystemExit as e:
        print(e)
        return 2

    chars = len(re.sub(r"\s", "", body))
    truncated = False
    if len(body) > args.max_chars:
        body = body[: args.max_chars] + "\n\n<!-- 已截断 -->"
        truncated = True

    lines = [
        "# 源材料抽取结果",
        "",
        f"- 源文件：`{src.as_posix()}`",
        f"- 格式：`{src.suffix.lower()}`｜抽取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 有效字符数（不含空白）：{chars}" + ("（已按上限截断）" if truncated else ""),
    ]
    if notes:
        lines.append("- 抽取说明：" + "；".join(notes))
    lines += ["", "> 本文件只做结构与文字抽取，未做总结或改写。论点、数据与口径需在工作流第 1 步中人工/模型提炼。", "", "---", "", body, ""]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[ok] 已抽取 {chars} 个有效字符 → {out}")

    if chars < MIN_USEFUL_CHARS and src.suffix.lower() == ".pdf":
        print("[warn] PDF 有效字符过少，可能是扫描件/图片型文档：")
        print("       建议先做 PDF→图片 渲染后走图像识读，并在素材中标注“由图像识读，未逐字校对”。")
    return 0


if __name__ == "__main__":
    sys.exit(main())