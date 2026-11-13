#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为「用户模板库」建索引（规格 v9.9 前置功能：模板填充模式）。

按规格要求，用户上传的模板**不复制原文件**，只把风格信息提取到索引，供生成前检索与按需读取：

- `assets/user-templates/index.json`：逐份模板的 页数 / 尺寸 / 主题字体 / 主题色 / 风格标签 / 关键词 / 原路径 / 体积
- `assets/user-templates/fonts-index.json`：随模板附带的字体清单（字体族 / 字重 / 来源路径，不复制不安装）

用法：
    python scripts/index_user_templates.py                     # 用内置默认素材目录
    python scripts/index_user_templates.py --source "D:/某个目录" --source "D:/另一个目录"

说明：只读取 pptx 内的少量 XML 条目（presentation.xml / theme1.xml）与字体 name 表，不解析整份文件，速度快。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import struct
import zipfile
from pathlib import Path

DEFAULT_SOURCES = [r'D:\文档\deepseek-harness\default-workspace\ppt-assets\A113：创新创赛', r'D:\文档\deepseek-harness\default-workspace\ppt-assets\国赛金奖ppt']
OUT_DIR = Path('assets/user-templates')

# 风格标签推断：命中路径或文件名即打标
STYLE_RULES = [
    ('国潮红金', ['红金', '红金风格', '朱红', '国奖', '国金']),
    ('国潮棕金', ['棕', '土金', '非遗', '陶瓷', '瓷', '茶', '咖啡', '陶艺', '工匠']),
    ('科技深蓝', ['蓝', '科技', '芯片', '智慧', '锅炉', '绝缘', '低碳']),
    ('科技黑金', ['黑金', '黑金版', '智能ai']),
    ('医疗科技白', ['医', '恒风量', '风机', '器械', 'airflow']),
    ('乡村绿', ['乡村', '振兴', '农业', '绿', '脱贫', '农域', '水果', '茶产业']),
    ('教育人文', ['教育', '财务', '学校', '职院', '课堂', '蒲公英']),
]
KEYWORD_STOP = ('ppt', 'pptx', 'pptm', '模板', '版', '改', '制作')

NAME_ID_FAMILY, NAME_ID_SUBFAMILY = 1, 2


def font_names(path: Path) -> dict:
    """解析 ttf/otf/ttc 的 name 表，取字体族与字重（不依赖 fontTools）"""
    try:
        b = path.read_bytes()
    except Exception:
        return {}
    if b[:4] == b'ttcf':
        if len(b) < 16:
            return {}
        base = struct.unpack('>I', b[12:16])[0]
    else:
        base = 0
    if len(b) < base + 12:
        return {}
    try:
        num_tables = struct.unpack('>H', b[base + 4:base + 6])[0]
    except struct.error:
        return {}
    name_tbl = None
    for i in range(num_tables):
        rec = base + 12 + 16 * i
        if rec + 16 > len(b):
            break
        tag = b[rec:rec + 4]
        off, ln = struct.unpack('>II', b[rec + 8:rec + 16])
        if tag == b'name':
            name_tbl = (off, ln)
            break
    if not name_tbl:
        return {}
    off, ln = name_tbl
    tbl = b[off:off + ln]
    if len(tbl) < 6:
        return {}
    count = struct.unpack('>H', tbl[2:4])[0]
    str_off = struct.unpack('>H', tbl[4:6])[0]
    out = {}
    for i in range(count):
        r = 6 + 12 * i
        if r + 12 > len(tbl):
            break
        pid, eid, lid, nid, slen, soff = struct.unpack('>HHHHHH', tbl[r:r + 12])
        if pid == 3 and nid in (NAME_ID_FAMILY, NAME_ID_SUBFAMILY):
            try:
                txt = tbl[str_off + soff:str_off + soff + slen].decode('utf-16-be').strip()
            except Exception:
                continue
            if txt and nid not in out:
                out[nid] = txt
    return {'family': out.get(NAME_ID_FAMILY), 'subfamily': out.get(NAME_ID_SUBFAMILY)}


def deck_info(path: Path) -> dict:
    info = {'size_mb': round(path.stat().st_size / 1048576, 2)}
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            info['pages'] = len([n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)])
            pre = z.read('ppt/presentation.xml').decode('utf-8', 'ignore')
            m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"', pre)
            if m:
                cx, cy = int(m.group(1)), int(m.group(2))
                info['slide_size_emu'] = [cx, cy]
                info['aspect'] = round(cx / cy, 3) if cy else None
            if 'ppt/theme/theme1.xml' in names:
                th = z.read('ppt/theme/theme1.xml').decode('utf-8', 'ignore')
                fonts = [f for f in dict.fromkeys(re.findall(r'<a:latin typeface="([^"]*)"', th)) if f]
                info['theme_fonts'] = fonts[:6]
                cols = re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', th)
                info['theme_colors'] = [c.upper() for c in dict.fromkeys(cols)][:8]
            if 'docProps/app.xml' in names and 'pages' not in info:
                app = z.read('docProps/app.xml').decode('utf-8', 'ignore')
                m2 = re.search(r'<Slides>(\d+)</Slides>', app)
                if m2:
                    info['pages'] = int(m2.group(1))
    except zipfile.BadZipFile:
        info['format'] = 'legacy-ppt'
    return info


def style_tags(text: str) -> list:
    low = text.lower()
    tags = [name for name, keys in STYLE_RULES if any(k.lower() in low for k in keys)]
    return tags or ['未归类']


def keywords(name: str) -> list:
    parts = re.split(r'[^\w\u4e00-\u9fff]+', name)
    out = []
    for w in parts:
        w = w.strip()
        if len(w) < 2 or w.lower() in KEYWORD_STOP:
            continue
        if w not in out:
            out.append(w)
    return out[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', action='append', default=None, help='素材目录，可多次传入')
    ap.add_argument('--out-dir', default=str(OUT_DIR))
    a = ap.parse_args()
    sources = a.source or DEFAULT_SOURCES
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    templates, fonts, missing = [], [], []
    for src in sources:
        root = Path(src)
        if not root.exists():
            missing.append(src)
            continue
        for p in sorted(root.rglob('*')):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            rel = str(p.relative_to(root))
            if ext in ('.pptx', '.pptm', '.ppt'):
                info = deck_info(p)
                templates.append({
                    'id': 'ut-%03d' % (len(templates) + 1),
                    'name': p.stem,
                    'path': str(p),
                    'rel_in_source': rel,
                    'source_dir': str(root),
                    'format': info.pop('format', 'pptx'),
                    'style_tags': style_tags(str(root) + '/' + rel),
                    'keywords': keywords(p.stem),
                    **info,
                })
            elif ext in ('.ttf', '.otf', '.ttc'):
                nm = font_names(p)
                fonts.append({
                    'file': p.name,
                    'path': str(p),
                    'ext': ext.lstrip('.'),
                    'size_kb': round(p.stat().st_size / 1024, 1),
                    'family': nm.get('family'),
                    'subfamily': nm.get('subfamily'),
                })

    idx = {
        '_note': ('规格 v9.9 前置功能「模板填充模式」的用户模板库索引：**只登记，不复制原文件**。'
                  '生成前先读本索引（几 KB），按关键词/风格标签检索出 2-3 份候选，再按需读取对应原文件；'
                  '不得整体读取全部模板。新增素材后重跑 scripts/index_user_templates.py 刷新。'),
        'sources': sources,
        'missing_sources': missing,
        'count': len(templates),
        'templates': templates,
    }
    fidx = {
        '_note': ('随模板附带的字体清单（v9.9）：**只登记，不复制、不安装**。'
                  '生成稿优先使用开源可商用字体；如需使用此处列出的字体，请自行确认授权后再安装。'),
        'count': len(fonts),
        'fonts': fonts,
    }
    json.dump(idx, io.open(out_dir / 'index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    json.dump(fidx, io.open(out_dir / 'fonts-index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('模板索引: %d 份 → %s' % (len(templates), out_dir / 'index.json'))
    print('字体清单: %d 个 → %s' % (len(fonts), out_dir / 'fonts-index.json'))
    if missing:
        print('缺失目录:', missing)
    by_tag = {}
    for t in templates:
        for tag in t['style_tags']:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    print('风格标签分布:', dict(sorted(by_tag.items(), key=lambda x: -x[1])))


if __name__ == '__main__':
    main()