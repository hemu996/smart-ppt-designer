# -*- coding: utf-8 -*-
"""
给 client.js 注入：
  A) TPL_PREVIEWS 常量（92 张已有模板的内联缩略图），彻底摆脱宿主路由
  B) 纯 JS zip 抽图函数 extractPptxThumb(arrayBuffer) —— 导入即出预览
  C) 导入按钮 + localStorage 持久化用户导入模板
  D) previewUrl 三级兜底：导入图 > 内联图 > 宿主路由
幂等：重复执行会先清除旧注入。
"""
import json, re, io, os, sys

CLIENT = r'D:\文档\deepseek-harness\default-workspace\smart-ppt-studio\client.js'
PREV = r'D:\文档\deepseek-harness\default-workspace\smart-ppt-studio\data\tpl_previews.json'

sys.stdout.reconfigure(encoding='utf-8')
src = io.open(CLIENT, encoding='utf-8').read()

# ---------- 幂等：清掉旧注入 ----------
src = re.sub(r'\n    /\* SPPS-INLINE-PREVIEWS:START \*/.*?/\* SPPS-INLINE-PREVIEWS:END \*/',
             '', src, flags=re.S)
src = re.sub(r'\n    /\* SPPS-IMPORT:START \*/.*?/\* SPPS-IMPORT:END \*/',
             '', src, flags=re.S)

# ---------- A) 内联预览数据 ----------
previews = json.load(io.open(PREV, encoding='utf-8'))
prev_json = json.dumps(previews, ensure_ascii=False, separators=(',', ':'))
blockA = '''
    /* SPPS-INLINE-PREVIEWS:START */
    // 92 张已有模板的缩略图（构建期从 docProps/thumbnail.jpeg 抽出并压缩）。
    // 之所以内联：宿主 /smart-ppt-studio/thumb 路由在部分 GUI 进程里未注册，
    // 全部卡片会 404 退化成「暂无预览图」。内联后前端自足，刷新即出图。
    const TPL_PREVIEWS = ''' + prev_json + ''';
    /* SPPS-INLINE-PREVIEWS:END */
'''

# 插到 const PREVIEW_ROUTE 之前
anchor = "    // 预览图由宿主半按需从 .pptx 内的 docProps/thumbnail.jpeg 取出，"
assert anchor in src, 'A 锚点丢失'
src = src.replace(anchor, blockA + '\n' + anchor, 1)

# ---------- B) 纯 JS zip 抽图 + C) 导入持久化 ----------
blockB = r'''
    /* SPPS-IMPORT:START */
    // 浏览器端零依赖抽取 .pptx 的 docProps/thumbnail.jpeg。
    // 实测本机模板该成员都是 stored(0)，直接切片即可；deflate(8) 时用
    // DecompressionStream('deflate-raw') 兜底（Electron/Chromium 支持）。
    function pptxThumbBytes(buf) {
      const dv = new DataView(buf), u8 = new Uint8Array(buf);
      // 1) 倒着找 EOCD (PK\005\006)
      let eo = -1, min = Math.max(0, buf.byteLength - 22 - 65535);
      for (let i = buf.byteLength - 22; i >= min; i--) {
        if (dv.getUint32(i, true) === 0x06054b50) { eo = i; break; }
      }
      if (eo < 0) return null;
      const count = dv.getUint16(eo + 10, true);
      let p = dv.getUint32(eo + 16, true);
      const WANT = 'docProps/thumbnail.jpeg';
      for (let n = 0; n < count; n++) {
        if (p + 46 > buf.byteLength || dv.getUint32(p, true) !== 0x02014b50) return null;
        const method = dv.getUint16(p + 10, true);
        const csize = dv.getUint32(p + 20, true);
        const nameLen = dv.getUint16(p + 28, true);
        const extraLen = dv.getUint16(p + 30, true);
        const comLen = dv.getUint16(p + 32, true);
        const loc = dv.getUint32(p + 42, true);
        const name = new TextDecoder().decode(u8.subarray(p + 46, p + 46 + nameLen));
        if (name === WANT) {
          if (loc + 30 > buf.byteLength || dv.getUint32(loc, true) !== 0x04034b50) return null;
          const lName = dv.getUint16(loc + 26, true);
          const lExtra = dv.getUint16(loc + 28, true);
          const start = loc + 30 + lName + lExtra;
          return { method, raw: u8.subarray(start, start + csize) };
        }
        p += 46 + nameLen + extraLen + comLen;
      }
      return null;
    }
    async function pptxThumbDataUrl(buf) {
      const hit = pptxThumbBytes(buf);
      if (!hit) return null;
      let bytes = hit.raw;
      if (hit.method === 8 && typeof DecompressionStream !== 'undefined') {
        try {
          const ds = new DecompressionStream('deflate-raw');
          bytes = new Uint8Array(await new Response(
            new Blob([bytes]).stream().pipeThrough(ds)).arrayBuffer());
        } catch (e) { return null; }
      } else if (hit.method !== 0) {
        return null;
      }
      // 缩到 480x270 省 localStorage 空间（用 canvas 重编码）
      try {
        const blob = new Blob([bytes], { type: 'image/jpeg' });
        const bmp = await createImageBitmap(blob);
        const cv = document.createElement('canvas');
        const w = 480, h = Math.round(w * bmp.height / bmp.width);
        cv.width = w; cv.height = h;
        cv.getContext('2d').drawImage(bmp, 0, 0, w, h);
        bmp.close();
        return cv.toDataURL('image/jpeg', 0.72);
      } catch (e) {
        let bin = '';
        for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
        return 'data:image/jpeg;base64,' + btoa(bin);
      }
    }
    // 用户导入模板（含自动生成的预览图）持久化在 localStorage
    const IMPORT_KEY = 'spps.imported.v1';
    function loadImported() {
      try { return JSON.parse(localStorage.getItem(IMPORT_KEY) || '[]'); } catch (e) { return []; }
    }
    function saveImported(list) {
      try { localStorage.setItem(IMPORT_KEY, JSON.stringify(list)); return true; }
      catch (e) { return false; }
    }
    // 从 zip 里读页数 / 主题色 / 字体，尽力而为，失败就留空
    async function pptxMeta(buf) {
      // 轻量：只数 ppt/slides/slideN.xml
      const dv = new DataView(buf), u8 = new Uint8Array(buf);
      let eo = -1, min = Math.max(0, buf.byteLength - 22 - 65535);
      for (let i = buf.byteLength - 22; i >= min; i--) {
        if (dv.getUint32(i, true) === 0x06054b50) { eo = i; break; }
      }
      if (eo < 0) return {};
      const count = dv.getUint16(eo + 10, true);
      let p = dv.getUint32(eo + 16, true), pages = 0;
      for (let n = 0; n < count; n++) {
        if (p + 46 > buf.byteLength) break;
        const nameLen = dv.getUint16(p + 28, true);
        const extraLen = dv.getUint16(p + 30, true);
        const comLen = dv.getUint16(p + 32, true);
        const name = new TextDecoder().decode(u8.subarray(p + 46, p + 46 + nameLen));
        if (/^ppt\/slides\/slide\d+\.xml$/.test(name)) pages++;
        p += 46 + nameLen + extraLen + comLen;
      }
      return { pages: pages || null, aspect: 1.778 };
    }
    /* SPPS-IMPORT:END */
'''
anchor2 = "    const PREVIEW_ROUTE = '/smart-ppt-studio/thumb?p=';"
assert anchor2 in src, 'B 锚点丢失'
src = src.replace(anchor2, blockB + '\n' + anchor2, 1)

# ---------- D) previewUrl 三级兜底 ----------
old = "    const previewUrl = (x) => (x && x.path ? PREVIEW_ROUTE + encodeURIComponent(x.path) : '');"
new = """    const previewUrl = (x) => {
      if (!x) return '';
      if (x.preview) return x.preview;                       // 用户导入时自动抽出的图
      if (TPL_PREVIEWS[x.id]) return TPL_PREVIEWS[x.id];     // 构建期内联图（自足，不依赖宿主）
      if (x.path) return PREVIEW_ROUTE + encodeURIComponent(x.path); // 最后才试宿主路由
      return '';
    };"""
assert old in src, 'D 锚点丢失'
src = src.replace(old, new, 1)

io.open(CLIENT, 'w', encoding='utf-8').write(src)
print('注入完成，client.js 字节数:', len(src.encode('utf-8')))
