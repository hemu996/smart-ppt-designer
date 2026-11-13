# -*- coding: utf-8 -*-
"""G0 基线完整性闸门 —— 所有「在 X 上做 Y」类任务的最高优先级验收。

规则：凡用户说「在/给我的 PPT 上套/加/适配 X」，操作对象就是那个文件，
交付物必须逐项等于操作前基线；不过 G0 一律不准交付。

用法：
    python baseline_gate.py <基线.pptx> <产物.pptx>
退出码 0 = 通过；1 = 拦截（内容有丢失）。
"""
import sys
import re
import zipfile
import hashlib
import json

sys.stdout.reconfigure(encoding="utf-8")
from lxml import etree

A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def manifest(path):
    z = zipfile.ZipFile(path)
    slides = sorted([n for n in z.namelist()
                     if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)],
                    key=lambda n: int(re.search(r"slide(\d+)", n).group(1)))
    per_page = []
    for n in slides:
        ts = [t.text or "" for t in etree.fromstring(z.read(n)).iter("{%s}t" % A)]
        per_page.append("".join(ts))
    m = {
        "slides": len(slides),
        "text_chars": sum(len(t) for t in per_page),
        "per_page_sha": [hashlib.sha256(t.encode("utf-8")).hexdigest()[:12]
                         for t in per_page],
        "notes": len([n for n in z.namelist()
                      if re.match(r"ppt/notesSlides/notesSlide\d+\.xml", n)]),
        "charts": len([n for n in z.namelist()
                       if re.match(r"ppt/charts/chart\d+\.xml", n)]),
        "media": len([n for n in z.namelist() if n.startswith("ppt/media/")]),
        "crc": z.testzip() or "OK",
    }
    z.close()
    return m


def main():
    base, out = sys.argv[1], sys.argv[2]
    a, b = manifest(base), manifest(out)
    fails = []
    for k in ("slides", "text_chars", "per_page_sha", "notes", "charts", "media"):
        if a[k] != b[k]:
            fails.append("%s: 基线=%s 产物=%s" % (
                k, str(a[k])[:90], str(b[k])[:90]))
    print("=" * 62)
    print("G0 基线完整性闸门")
    print("  基线 : %s" % base)
    print("  产物 : %s" % out)
    print("-" * 62)
    print("  页数      基线 %-4d 产物 %-4d %s" % (a["slides"], b["slides"],
          "OK" if a["slides"] == b["slides"] else "✗ 丢失"))
    print("  文字字符  基线 %-4d 产物 %-4d %s" % (a["text_chars"], b["text_chars"],
          "OK" if a["text_chars"] == b["text_chars"] else "✗ 丢失"))
    print("  逐页文字  %s" % ("OK 全一致" if a["per_page_sha"] == b["per_page_sha"]
                            else "✗ 有页被改"))
    print("  备注      基线 %-4d 产物 %-4d" % (a["notes"], b["notes"]))
    print("  原生图表  基线 %-4d 产物 %-4d" % (a["charts"], b["charts"]))
    print("  媒体      基线 %-4d 产物 %-4d" % (a["media"], b["media"]))
    print("  CRC       %s / %s" % (a["crc"], b["crc"]))
    print("-" * 62)
    if fails:
        print("  【拦截】内容不完整，禁止交付：")
        for f in fails:
            print("    ·", f)
        print("=" * 62)
        return 1
    print("  【通过】内容与基线一致，可继续做效果验收")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
