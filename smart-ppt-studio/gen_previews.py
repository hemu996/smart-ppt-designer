# -*- coding: utf-8 -*-
"""从 95 份模板的 docProps/thumbnail.jpeg 抽出缩略图，生成前端自足预览数据。
浏览器环境不能用宿主路由（当前 GUI 未注册 /smart-ppt-studio/thumb），
所以把缩略图压成小 JPEG base64 内联进 client.js。
"""
import json, re, os, zipfile, base64, io
from PIL import Image

CLIENT = r'D:\文档\deepseek-harness\default-workspace\smart-ppt-studio\client.js'
OUT = r'D:\文档\deepseek-harness\default-workspace\smart-ppt-studio\data\tpl_previews.json'

s = open(CLIENT, encoding='utf-8').read()
d = json.loads(re.search(r'const STYLE_DATA = (\{.*?\});\n', s, re.S).group(1))
templates = d['templates']
print('模板数:', len(templates))

previews = {}
ok = 0
for tp in templates:
    p = tp.get('path', '')
    if not p.lower().endswith(('.pptx', '.pptm', '.potx', '.ppsm', '.ppsx')):
        continue
    if not os.path.isfile(p):
        continue
    try:
        with zipfile.ZipFile(p) as z:
            if 'docProps/thumbnail.jpeg' not in z.namelist():
                continue
            raw = z.read('docProps/thumbnail.jpeg')
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        im.thumbnail((480, 270), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=72)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        previews[tp['id']] = 'data:image/jpeg;base64,' + b64
        ok += 1
    except Exception as e:
        print('  跳过', tp['id'], type(e).__name__)
        continue

json.dump(previews, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('成功抽图:', ok, '/', len(templates))
print('数据文件 KB:', round(os.path.getsize(OUT)/1024, 1))
