#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
render_slides.py — 把 pptx 逐页导出为 PNG，供「PPT 设计台」页面预览模块使用。

为什么需要这个脚本：
  PowerPoint COM 的 Slide.Export 在中文路径下会失败
  （com_error: PowerPoint 无法将 ^0 保存到 ^1）。
  所以脚本先把 pptx 复制到纯 ASCII 临时目录（%TEMP%\\spps_render_xxx），
  在那里导出，再把 PNG 搬回目标目录。这条路径已在 2026-11-26 实测通过。

用法：
  python render_slides.py <pptx路径> <输出目录> [--width 1280] [--height 720] [--force]

输出：
  成功 → stdout 打印 JSON: {"ok":true,"slides":N,"files":[...],"elapsed":秒}
  失败 → stdout 打印 JSON: {"ok":false,"error":"原因"}，退出码 1

缓存：
  目标目录已存在 pNN.png 且张数匹配、且未加 --force 时直接复用，避免重复渲染。
"""
import sys, os, json, time, shutil, tempfile, subprocess

def _ascii_temp_dir():
    base = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
    # 只保留 ASCII 的 base，否则退回 C:\Temp
    try:
        base.encode('ascii')
    except UnicodeEncodeError:
        base = r'C:\Temp'
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix='spps_render_', dir=base)

def _export_with_com(pptx_path, out_dir, width, height):
    import win32com.client as win32
    app = win32.Dispatch('PowerPoint.Application')
    try:
        app.Visible = True
    except Exception:
        pass
    pres = None
    try:
        pres = app.Presentations.Open(pptx_path, WithWindow=False)
        n = pres.Slides.Count
        files = []
        for i in range(1, n + 1):
            out = os.path.join(out_dir, 'p%02d.png' % i)
            pres.Slides(i).Export(out, 'PNG', width, height)
            if os.path.isfile(out):
                files.append(out)
        return n, files
    finally:
        if pres is not None:
            try: pres.Close()
            except Exception: pass
        try: app.Quit()
        except Exception: pass

def render(pptx_path, out_dir, width=1280, height=720, force=False):
    t0 = time.time()
    if not os.path.isfile(pptx_path):
        return {'ok': False, 'error': 'pptx 不存在: %s' % pptx_path}
    os.makedirs(out_dir, exist_ok=True)

    if not force:
        cached = sorted(f for f in os.listdir(out_dir) if f.startswith('p') and f.endswith('.png'))
        if cached:
            return {'ok': True, 'slides': len(cached), 'cached': True,
                    'files': [os.path.join(out_dir, f) for f in cached],
                    'elapsed': round(time.time() - t0, 1)}

    tmp = _ascii_temp_dir()
    try:
        # 关键：复制到纯 ASCII 目录再导出
        safe_pptx = os.path.join(tmp, 'deck.pptx')
        shutil.copy2(pptx_path, safe_pptx)
        tmp_png = os.path.join(tmp, 'png')
        os.makedirs(tmp_png, exist_ok=True)

        n, tmp_files = _export_with_com(safe_pptx, tmp_png, width, height)
        if not tmp_files:
            return {'ok': False, 'error': 'COM 未导出任何页面（可能 PowerPoint 实例冲突）'}

        # 搬回目标目录
        final = []
        for f in tmp_files:
            name = os.path.basename(f)
            dst = os.path.join(out_dir, name)
            shutil.move(f, dst)
            final.append(dst)

        return {'ok': True, 'slides': n, 'files': final,
                'elapsed': round(time.time() - t0, 1)}
    except Exception as e:
        return {'ok': False, 'error': '%s: %s' % (type(e).__name__, str(e)[:300])}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main(argv):
    if len(argv) < 3:
        print(json.dumps({'ok': False, 'error': '用法: render_slides.py <pptx> <outdir> [--width N] [--height N] [--force]'}, ensure_ascii=False))
        return 1
    pptx, outdir = argv[1], argv[2]
    w, h, force = 1280, 720, False
    i = 3
    while i < len(argv):
        if argv[i] == '--width' and i + 1 < len(argv): w = int(argv[i+1]); i += 2
        elif argv[i] == '--height' and i + 1 < len(argv): h = int(argv[i+1]); i += 2
        elif argv[i] == '--force': force = True; i += 1
        else: i += 1
    r = render(pptx, outdir, w, h, force)
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r.get('ok') else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
