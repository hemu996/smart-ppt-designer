#!/usr/bin/env node
/**
 * build_pptx.js —— 页面计划 → 原生可编辑 PPTX（v5.1，工作流第 9 步）
 *
 * 本脚本实现：
 *   - 五个母版：COVER / SECTION / CONTENT_NAV / DATA / CLOSING
 *   - 母版内置章节导航 + 当前章节高亮（红线第 12 条）
 *   - 原生形状 / 原生图表（带数据源）/ 原生表格 / 原生图标 / 讲者备注（红线第 2、3、10、14 条）
 *   - 统一视觉系统取值（红线第 5、13 条）
 *   - 图片与特效缺失时降级，不中断（红线第 15 条）
 *   - 禁用 HTML 渲染与 PowerPoint COM（红线第 1、4 条）
 *
 * 用法：
 *   node scripts/build_pptx.js --plan output/plan.json --candidate A --out output/deck.pptx
 *   node scripts/build_pptx.js --plan output/plan.json --candidate B --out output/deck_B.pptx
 */
const fs = require('fs');
const path = require('path');
const PptxGenJS = require('pptxgenjs');
const JSZip = require('jszip');
const cfg = require('../assets/pptxgenjs-config.js');

const LAYOUT_NAME = cfg.config.canvas.custom_layout || 'SMART_16x9';
const MASTERS = { cover: 'COVER', toc: 'CONTENT_NAV', section_divider: 'SECTION', content: 'CONTENT_NAV', concept: 'CONTENT_NAV', data_chart: 'DATA', closing: 'CLOSING' };

/**
 * 兼容修正：pptxgenjs 对图表分类一律写 <c:multiLvlStrRef>，部分渲染器（Office 兼容导出、LibreOffice 系）
 * 会忽略该节点并把分类退化成 1/2/3 序号。这里把它改写为等价的单层 <c:strRef>，
 * 图表仍是原生对象、数据源不变，仅修正类别引用写法（首轮视觉校验的必改项）。
 */
async function postProcessXml(file, report) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const names = Object.keys(zip.files);
  const charts = names.filter((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n));
  const slides = names.filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n))
    .sort((a, b) => Number(a.match(/(\d+)/)[1]) - Number(b.match(/(\d+)/)[1]));

  // (1) 图表分类：multiLvlStrRef → strRef（渲染端才会显示业务名而不是 1/2/3）
  let catFixed = 0;
  for (const name of charts) {
    const xml = await zip.file(name).async('string');
    const next = xml.replace(/<c:multiLvlStrRef>([\s\S]*?)<\/c:multiLvlStrRef>/g, (m, body) => {
      const f = (body.match(/<c:f>([\s\S]*?)<\/c:f>/) || [])[1] || '';
      const pts = [...body.matchAll(/<c:pt idx="(\d+)"><c:v>([\s\S]*?)<\/c:v><\/c:pt>/g)]
        .map((x) => `<c:pt idx="${x[1]}"><c:v>${x[2]}</c:v></c:pt>`);
      return `<c:strRef><c:f>${f}</c:f><c:strCache><c:ptCount val="${pts.length}"/>${pts.join('')}</c:strCache></c:strRef>`;
    });
    if (next !== xml) { zip.file(name, next); catFixed += 1; }
  }

  // (2) 渐变填充：把标记过的矩形替换为真实 <a:gradFill>（含 alpha 停点）
  const gradRequests = report.gradients || [];
  let gradFixed = 0;
  for (let i = 0; i < slides.length; i += 1) {
    const reqs = gradRequests.filter((g) => g.order === i);
    if (!reqs.length) continue;
    const name = slides[i];
    let xml = await zip.file(name).async('string');
    for (const req of reqs) {
      const { x, y, w, h } = req.emu;
      const spRe = /<p:sp>[\s\S]*?<\/p:sp>/g;
      xml = xml.replace(spRe, (sp) => {
        if (sp.indexOf(`<a:off x="${x}" y="${y}"/>`) === -1) return sp;
        if (sp.indexOf(`<a:ext cx="${w}" cy="${h}"/>`) === -1) return sp;
        const stops = req.stops.map((st) => `<a:gs pos="${Math.round(st.pos * 1000)}"><a:srgbClr val="${st.color}">${st.alpha !== undefined && st.alpha < 100 ? `<a:alpha val="${Math.round(st.alpha * 1000)}"/>` : ''}</a:srgbClr></a:gs>`).join('');
        const fill = `<a:gradFill rotWithShape="1"><a:gsLst>${stops}</a:gsLst><a:lin ang="${Math.round((req.angle || 90) * 60000)}" scaled="0"/></a:gradFill>`;
        const replaced = sp.replace(/<a:(?:solidFill|noFill)>[\s\S]*?<\/a:(?:solidFill|noFill)>/, fill);
        if (replaced !== sp) gradFixed += 1;
        return replaced;
      });
    }
    zip.file(name, xml);
  }

  // (3) 统一淡入转场：每页写入 <p:transition spd="med"><p:fade/></p:transition>
  // v9.0.6 本机适配：动效内核（morph / 自动换片 / 延续对象）由出稿后的
  // plan 显式声明 transition:none 时跳过 fade，交给后处理脚本全权决定。
  let transFixed = 0;
  // skipFade 由主流程写进 report.skip_fade 后传入（postProcessXml 作用域内没有 plan）
  const skipFade = report.skip_fade === true;
  for (const name of slides) {
    let xml = await zip.file(name).async('string');
    if (!skipFade && xml.indexOf('<p:transition') === -1) {
      const inserted = xml.replace('</p:sld>', '<p:transition spd="med"><p:fade/></p:transition></p:sld>');
      if (inserted !== xml) { zip.file(name, inserted); transFixed += 1; }
    }
  }

  // (4b) v8.9 跨客户端兼容：为已声明拉丁字体的文本补东亚（<a:ea>）与复杂文种（<a:cs>）声明。
  // 只处理含 <a:latin typeface="..."> 的段，并插在 latin 之后（保持 DrawingML 子元素顺序 latin→ea→cs）。
  let fontDeclared = 0;
  const fontStats = { latin: 0, ea: 0, cs: 0 };
  for (const name of slides) {
    const xml = await zip.file(name).async('string');
    fontStats.latin += (xml.match(/<a:latin /g) || []).length;
    fontStats.ea += (xml.match(/<a:ea /g) || []).length;
    fontStats.cs += (xml.match(/<a:cs /g) || []).length;
    const next = xml.replace(/<a:rPr([^>/]*)>([\s\S]*?)<\/a:rPr>/g, (m, attrs, body) => {
      if (body.indexOf('<a:ea') !== -1) return m;
      const lm = body.match(/<a:latin typeface="([^"]+)"[^>]*\/>/);
      if (!lm) return m;
      const t = lm[1];
      return `<a:rPr${attrs}>` + body.replace(lm[0], `${lm[0]}<a:ea typeface="${t}"/><a:cs typeface="${t}"/>`) + '</a:rPr>';
    });
    if (next !== xml) { zip.file(name, next); fontDeclared += 1; }
  }
  report.font_declared = fontDeclared;
  report.font_stats = fontStats;

  // (4c) v9.0 卡片精致度：给打标为 CARD* 的卡片形状加轻微投影（outerShdw，插在 </p:spPr> 之前，符合 schema 顺序）
  let cardShadow = 0;
  for (const name of slides) {
    const xml = await zip.file(name).async('string');
    const next = xml.replace(/<p:sp>[\s\S]*?<\/p:sp>/g, (sp) => {
      if (!/name="CARD(?!INDEX)\d+"/.test(sp)) return sp;
      if (sp.indexOf('<a:effectLst>') !== -1) return sp;
      const eff = '<a:effectLst><a:outerShdw blurRad="63500" dist="25400" dir="5400000" rotWithShape="0">'
                + '<a:srgbClr val="000000"><a:alpha val="22000"/></a:srgbClr></a:outerShdw></a:effectLst>';
      return sp.replace('<\/p:spPr>', eff + '</p:spPr>');
    });
    if (next !== xml) { zip.file(name, next); cardShadow += 1; }
  }
  report.card_shadow_pages = cardShadow;

  // (5) v8.7 装饰组建组：把同一装饰组的连续 <p:sp> 包成 <p:grpSp>（identity 变换，子形状坐标不变）
  let grouped = 0;
  try {
    for (let si = 0; si < slides.length; si += 1) {
      const xml = await zip.file(slides[si]).async('string');
      const blocks = [...xml.matchAll(/<p:sp>[\s\S]*?<\/p:sp>/g)];
      const keyOf = [];
      const groups = {};
      blocks.forEach((b, idx) => {
        const nm = (b[0].match(/<p:cNvPr[^>]*name="([^"]*)"/) || [])[1] || '';
        const mmD = nm.match(/^DSET#(\d+)#([^#]+)#(\d+)$/);
        const mmC = nm.match(/^CMP#(\d+)#([^#]+)#(\d+)#(\d+)$/);
        let key = '';
        if (mmD) key = 'DSET#' + mmD[1] + '#' + mmD[2];
        else if (mmC) key = 'CMP#' + mmC[1] + '#' + mmC[2] + '#' + mmC[3];
        if (!key) return;
        keyOf[idx] = key;
        (groups[key] = groups[key] || []).push(idx);
      });
      if (!Object.keys(groups).length) continue;
      const handled = {};
      let pos = 0;
      let out = '';
      let local = 0;
      for (let i = 0; i < blocks.length; i += 1) {
        if (handled[i]) continue;
        const b = blocks[i];
        out += xml.slice(pos, b.index);
        const idxs = (keyOf[i] && groups[keyOf[i]]) || null;
        const ok = idxs && idxs.length >= 2 && idxs.every((v, k) => k === 0 || v === idxs[k - 1] + 1);
        if (ok) {
          const inner = idxs.map((v) => blocks[v][0]).join('');
          const offs = [];
          const exts = [];
          const ro = /<a:off x="(-?\d+)" y="(-?\d+)"/g;
          let mo;
          while ((mo = ro.exec(inner)) !== null) offs.push([Number(mo[1]), Number(mo[2])]);
          const re2 = /<a:ext cx="(\d+)" cy="(\d+)"/g;
          let me;
          while ((me = re2.exec(inner)) !== null) exts.push([Number(me[1]), Number(me[2])]);
          if (offs.length && offs.length === exts.length) {
            let x0 = offs[0][0];
            let y0 = offs[0][1];
            let x1 = 0;
            let y1 = 0;
            for (let k = 0; k < offs.length; k += 1) {
              x0 = Math.min(x0, offs[k][0]);
              y0 = Math.min(y0, offs[k][1]);
              x1 = Math.max(x1, offs[k][0] + exts[k][0]);
              y1 = Math.max(y1, offs[k][1] + exts[k][1]);
            }
            const gid = 9000 + grouped;
            out += '<p:grpSp><p:nvGrpSpPr><p:cNvPr id="' + gid + '" name="' + keyOf[i] + '"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
              + '<p:grpSpPr><a:xfrm><a:off x="' + x0 + '" y="' + y0 + '"/><a:ext cx="' + (x1 - x0) + '" cy="' + (y1 - y0) + '"/>'
              + '<a:chOff x="' + x0 + '" y="' + y0 + '"/><a:chExt cx="' + (x1 - x0) + '" cy="' + (y1 - y0) + '"/></a:xfrm></p:grpSpPr>'
              + inner + '</p:grpSp>';
            idxs.forEach((v) => { handled[v] = true; });
            const lastB = blocks[idxs[idxs.length - 1]];
            pos = lastB.index + lastB[0].length;
            grouped += 1;
            local += 1;
          } else {
            out += b[0];
            pos = b.index + b[0].length;
          }
        } else {
          out += b[0];
          pos = b.index + b[0].length;
        }
      }
      out += xml.slice(pos);
      if (local) zip.file(slides[si], out);
    }
  } catch (e) {
    console.warn('[装饰组] 成组跳过：' + e.message);
  }

  fs.writeFileSync(file, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
  return { charts_scanned: charts.length, chart_categories_fixed: catFixed, gradients_written: gradFixed, transitions_written: transFixed, groups_written: grouped };
}

function parseArgs(argv) {
  const a = { candidate: 'A', out: null, plan: null, imagesDir: null, effectsDir: null };
  for (let i = 2; i < argv.length; i += 1) {
    const k = argv[i];
    if (k === '--plan') a.plan = argv[++i];
    else if (k === '--candidate') a.candidate = String(argv[++i]).toUpperCase();
    else if (k === '--out') a.out = argv[++i];
    else if (k === '--images-dir') a.imagesDir = argv[++i];
    else if (k === '--effects-dir') a.effectsDir = argv[++i];
    else if (k === '--help' || k === '-h') {
      console.log('用法：node scripts/build_pptx.js --plan <plan.json> --candidate A|B --out <deck.pptx>');
      process.exit(0);
    }
  }
  if (!a.plan) throw new Error('缺少 --plan 参数');
  a.out = a.out || path.join('output', `deck_${a.candidate}.pptx`);
  return a;
}

function resolveAsset(rel, extraDir) {
  if (!rel) return null;
  const cands = path.isAbsolute(rel) ? [rel] : [rel, extraDir ? path.join(extraDir, path.basename(rel)) : null].filter(Boolean);
  for (const c of cands) if (c && fs.existsSync(c)) return c;
  return null;
}

function masterFor(slide) {
  return MASTERS[slide.slide_type] || 'CONTENT_NAV';
}

/** 读取 PNG / JPEG 的像素尺寸（用于"图片宽度不足时渐变填补"判断）；无法识别时返回 null */
function readImageSize(file) {
  try {
    const buf = fs.readFileSync(file);
    if (buf.length > 24 && buf.toString('ascii', 1, 4) === 'PNG') {
      return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
    }
    if (buf[0] === 0xFF && buf[1] === 0xD8) {
      let i = 2;
      while (i < buf.length - 9) {
        if (buf[i] !== 0xFF) { i += 1; continue; }
        const marker = buf[i + 1];
        const len = buf.readUInt16BE(i + 2);
        if (marker >= 0xC0 && marker <= 0xCF && marker !== 0xC4 && marker !== 0xC8 && marker !== 0xCC) {
          return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
        }
        i += 2 + len;
      }
    }
  } catch (e) { /* 忽略 */ }
  return null;
}

const EMU = 914400;
/** 记录一个"应为渐变填充"的矩形：先用实色+透明度兜底绘制，随后由 XML 后处理替换为真实 gradFill */
function gradientRect(slide, pptx, report, spec) {
  const { x, y, w, h, angle, stops, fallbackColor, fallbackTransparency } = spec;
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color: fallbackColor, transparency: fallbackTransparency === undefined ? 60 : fallbackTransparency },
    line: { color: fallbackColor, width: 0 },
  });
  report.gradients.push({
    order: report._current || 0,
    emu: { x: Math.round(x * EMU), y: Math.round(y * EMU), w: Math.round(w * EMU), h: Math.round(h * EMU) },
    angle: angle === undefined ? 90 : angle,
    stops,
  });
}

/** 定义五个母版（导航栏框架、页码位置、背景色都来自视觉系统） */
function defineMasters(pptx, vs, nav, navEnabled) {
  const C = vs.colors;
  const navFrame = [];
  if (navEnabled !== false && nav.mode === 'sidebar') {
    navFrame.push({ rect: { x: 0, y: 0, w: nav.sideWidthIn, h: cfg.canvas.height_in, fill: { color: cfg.toHex(C.background) }, line: { color: cfg.toHex(C.primary), width: 0.75 } } });
  }
  pptx.defineSlideMaster({ title: 'COVER', background: { color: cfg.toHex(C.primary) }, objects: [] });
  pptx.defineSlideMaster({ title: 'SECTION', background: { color: cfg.toHex(C.primary) }, objects: [] });
  pptx.defineSlideMaster({ title: 'CLOSING', background: { color: cfg.toHex(C.primary) }, objects: [] });
  pptx.defineSlideMaster({ title: 'CONTENT_NAV', background: { color: cfg.toHex(C.background) }, objects: navFrame });
  pptx.defineSlideMaster({ title: 'DATA', background: { color: cfg.toHex(C.background) }, objects: navFrame });
}

/** 章节导航：当前章节高亮 */
function drawNavigation(slide, pptx, nav, sections, current) {
  if (!nav.enabled || !sections || !sections.length) return;
  const list = sections.slice(0, 6);
  if (nav.mode === 'top') {
    const w = (cfg.canvas.width_in - 1.6) / list.length;
    list.forEach((name, i) => {
      const active = name === current;
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.8 + i * w, y: 0.06, w: w - 0.12, h: nav.topHeightIn - 0.12,
        fill: { color: active ? nav.activeColor : nav.inactiveColor }, line: { color: active ? nav.activeColor : nav.inactiveColor, width: 0 },
      });
      slide.addText(String(name).slice(0, 6), {
        x: 0.8 + i * w, y: 0.06, w: w - 0.12, h: nav.topHeightIn - 0.12,
        fontSize: nav.titlePt, fontFace: vs_font(vs_cache), color: active ? nav.textActive : nav.textInactive,
        align: 'center', valign: 'middle', margin: 0, bold: active,
      });
    });
    return;
  }
  const barH = Math.min(0.62, (cfg.canvas.height_in - 1.6) / list.length);
  list.forEach((name, i) => {
    const y = 0.75 + i * (barH + 0.12);
    const active = name === current;
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.14, y, w: nav.sideWidthIn - 0.28, h: barH,
      fill: { color: active ? nav.activeColor : nav.inactiveColor }, line: { color: active ? nav.activeColor : nav.inactiveColor, width: 0 },
    });
    slide.addText(String(name).slice(0, 6), {
      x: 0.14, y, w: nav.sideWidthIn - 0.28, h: barH,
      fontSize: nav.titlePt, fontFace: vs_font(vs_cache), color: active ? nav.textActive : nav.textInactive,
      align: 'center', valign: 'middle', margin: 0, bold: active,
    });
  });
}
let _cardIdxSeq = 0;   // v9.0 卡片序号带计数（objectName=CARDINDEXn，便于检测）
let _cardSeq = 0;      // v9.0 卡片打标（objectName=CARDn，供 XML 后处理加投影）
let vs_cache = null;
function vs_font(system) {
  return cfg.resolveFont(system && system.fonts ? system.fonts.body : undefined, system);
}

function addTextEl(slide, el, vs, dark) {
  // v8.9 去 AI 感：支持富文本 runs（个别重点字放大：runs[i].fontSize 高于正文 ≥1.4 倍）
  const _content = Array.isArray(el.runs) && el.runs.length
    ? el.runs.map((r) => ({
        text: String(r.text || ''),
        options: {
          fontSize: Number(r.fontSize || el.font_pt),
          bold: !!r.bold,
          italic: !!r.italic,
          color: cfg.resolveToken(r.color || el.color || (dark ? 'FFFFFF' : 'text'), vs),
        },
      }))
    : String(el.text || '');
  slide.addText(_content, {
    
    x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in,
    fontSize: el.font_pt,
    fontFace: cfg.resolveFont(el.font, vs),
    color: cfg.resolveToken(el.color || (dark ? 'FFFFFF' : 'text'), vs),
    bold: !!el.bold,
    italic: !!el.italic,
    align: el.align || 'left',
    valign: el.valign || 'top',
    margin: 0,
    lineSpacingMultiple: cfg.thresholds.line_height_ratio || 1.3,
    isTextBox: true,
    rotate: el.rotation === undefined ? 0 : Number(el.rotation),
  });
}

/**
 * v8.7 装饰组：1 个计划元素 → 多个基础图元。
 * 每个图元用 objectName 打标（DSET#<页号>#<组名>#<序号>），构建后由 XML 后处理包成真实 <p:grpSp> 组。
 */
let decoration_cache = null;
function loadDecorationSets() {
  if (decoration_cache) return decoration_cache;
  const dir = path.join(__dirname, '..', 'assets', 'decoration-sets');
  const out = {};
  if (fs.existsSync(dir)) {
    for (const f of fs.readdirSync(dir)) {
      if (!/\.json$/.test(f) || f === 'index.json') continue;
      try {
        const j = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
        if (j && j.id && Array.isArray(j.shapes)) out[j.id] = j;
      } catch (e) { /* 跳过坏文件 */ }
    }
  }
  decoration_cache = out;
  return out;
}

/** v8.7 组件：计划级 components 里定义的形状组，跨页复用；打标 CMP# 后由 XML 后处理包成 <p:grpSp> */
/** v8.9 创意度档位：优先 design_brief.creative_level，其次 config 默认；未知档位回落 off */
function creativeLevel(plan) {
  const conf = (cfg.config && cfg.config.creative_level) || {};
  const lv = (plan && plan.design_brief && plan.design_brief.creative_level) || conf.default || 'off';
  return ((conf.levels || {})[lv]) ? lv : 'off';
}

function addComponentEl(slide, pptx, el, vs, report, plan, slideId) {
  const comps = plan.components || {};
  const comp = comps[el.component_id || el.id];
  if (!comp || !Array.isArray(comp.shapes)) {
    (report.components_missing = report.components_missing || []).push({ slide_id: slideId, component_id: el.component_id });
    return false;
  }
  const seq = (report._cmpSeq = (report._cmpSeq || 0) + 1);
  const tag = 'CMP#' + slideId + '#' + (el.component_id || el.id) + '#' + seq;
  comp.shapes.forEach((sh, i) => {
    const type = (pptx.ShapeType && pptx.ShapeType[sh.shape_type]) || pptx.ShapeType.rect;
    const fill = cfg.resolveToken(sh.fill || 'accent', vs);
    const opts = { x: Number(el.x_in) + Number(sh.x_in || 0), y: Number(el.y_in) + Number(sh.y_in || 0),
                   w: sh.w_in, h: sh.h_in, objectName: tag + '#' + i };
    // v8.9 创意度开关：卡片圆角由档位决定（off = 0.04in，与既有行为一致）
    if (sh.shape_type === 'roundRect') {
      const _lv = creativeLevel(plan);
      const _r = (((cfg.config.creative_level || {}).levels || {})[_lv] || {}).card_radius_in;
      if (typeof _r === 'number') opts.rectRadius = _r;
    }
    if (sh.rotation) opts.rotate = Number(sh.rotation);
    if (sh.shape_type === 'line') {
      opts.line = { color: cfg.resolveToken(sh.line_color || sh.fill || 'accent', vs), width: sh.line_width_pt || 1.0 };
    } else {
      opts.fill = { color: fill };
      if (sh.fill_transparency !== undefined) opts.fill.transparency = sh.fill_transparency;
      opts.line = sh.line_color ? { color: cfg.resolveToken(sh.line_color, vs), width: sh.line_width_pt || 1 } : { color: fill, width: 0 };
    }
    slide.addShape(type, Object.assign({}, opts));
  });
  report.components_used = (report.components_used || 0) + 1;
  report.component_shapes = (report.component_shapes || 0) + comp.shapes.length;
  return true;
}

function addDecorationSetEl(slide, pptx, el, vs, report, slideId) {
  const set = loadDecorationSets()[el.set_id || el.set];
  if (!set) {
    (report.decoration_missing = report.decoration_missing || []).push({ slide_id: slideId, set_id: el.set_id || el.set });
    return false;
  }
  const tag = 'DSET#' + slideId + '#' + set.id;
  (set.shapes || []).forEach((sh, i) => {
    const type = (pptx.ShapeType && pptx.ShapeType[sh.shape_type]) || pptx.ShapeType.rect;
    const fill = cfg.resolveToken(sh.fill || 'accent', vs);
    const opts = { x: sh.x_in, y: sh.y_in, w: sh.w_in, h: sh.h_in, objectName: tag + '#' + i };
    if (sh.rotation) opts.rotate = Number(sh.rotation);
    if (sh.shape_type === 'line') {
      opts.line = { color: cfg.resolveToken(sh.line_color || sh.fill || 'accent', vs), width: sh.line_width_pt || 1.0 };
    } else {
      opts.fill = { color: fill };
      if (sh.fill_transparency !== undefined) opts.fill.transparency = sh.fill_transparency;
      opts.line = sh.line_color ? { color: cfg.resolveToken(sh.line_color, vs), width: sh.line_width_pt || 1 } : { color: fill, width: 0 };
    }
    slide.addShape(type, Object.assign({}, opts));
  });
  report.decoration_sets_used += 1;
  report.decoration_shapes += (set.shapes || []).length;
  return true;
}

function addShapeEl(slide, pptx, el, vs) {
  const type = (pptx.ShapeType && pptx.ShapeType[el.shape_type]) || pptx.ShapeType.rect;
  const fill = cfg.resolveToken(el.fill || 'accent', vs);
  // v8.7 卡片样式：卡片类形状（非装饰、非标题）按视觉系统 card_style 施加半透明底与细描边
  const cs = vs.card_style || {};
  // v9.0.2 并入（补丁包）：COMPOSITION# 是构图背板（衬底），不做卡片样式、不加序号带
  const _isBoard = String(el.object_name || '').startsWith('COMPOSITION#');
  const cardLike = !_isBoard && ['rect', 'roundRect'].includes(el.shape_type) && !['decoration', 'title', 'subtitle'].includes(el.role || '');
  if (cardLike && cs.fill_alpha !== undefined && el.fill_transparency === undefined) {
    el = Object.assign({}, el, { fill_transparency: 100 - Number(cs.fill_alpha) });
  }
  if (cardLike && String(cs.border || '').indexOf('hairline') >= 0 && !el.line_color) {
    el = Object.assign({}, el, { line_color: 'accent', line_width_pt: 0.75 });
  }
  const opts = { x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in };
  if (el.rotation) opts.rotate = Number(el.rotation);
  if (el.flipH) opts.flipH = true;
  if (el.shape_type === 'line') {
    opts.line = { color: cfg.resolveToken(el.line_color || el.fill || 'accent', vs), width: el.line_width_pt || 1.5 };
  } else {
    opts.fill = { color: fill };
    if (el.fill_transparency !== undefined) opts.fill.transparency = el.fill_transparency;
    opts.line = el.line_color ? { color: cfg.resolveToken(el.line_color, vs), width: el.line_width_pt || 1 } : { color: fill, width: 0 };
  }
  if (el.object_name) opts.objectName = String(el.object_name);
  else if (cardLike) opts.objectName = 'CARD' + (++_cardSeq);   // v9.0：卡片打标，供后处理加投影
  slide.addShape(type, Object.assign({}, opts));
  // v9.0 卡片精致度：左上角序号带（细描边卡片专属，规格"左上角序号带设计感"）
  if (cardLike && cs.corner_index) {
    const _accent = cfg.resolveToken('accent', vs);
    slide.addShape(pptx.ShapeType.rect, {
      x: Number(el.x_in) + 0.12, y: Number(el.y_in) + 0.12, w: 0.5, h: 0.1,
      fill: { color: _accent }, line: { color: _accent, width: 0 },
      objectName: 'CARDINDEX' + (++_cardIdxSeq),
    });
  }
}

function addImageEl(slide, el, extraDir) {
  const p = resolveAsset(el.image_path, extraDir);
  if (!p) return false;
  slide.addImage({ path: p, x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in });
  return true;
}

/**
 * v5.5 图片适配：按原始比例放置，宽度不足时不拉伸、不裁切，
 * 两侧用"图片边缘主色 → 页面背景色"的渐变矩形填补（渐变由 XML 后处理写成真实 gradFill）。
 */
function addImageFitEl(slide, pptx, el, extraDir, report, vs) {
  const p = resolveAsset(el.image_path, extraDir);
  if (!p) return false;
  const size = readImageSize(p);
  const boxAspect = el.w_in / el.h_in;
  if (!size || !size.w || !size.h) {
    slide.addImage({ path: p, x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in });
    return true;
  }
  // v8.9 跨客户端兼容修复：无论图片比框更宽还是更窄，一律按原始宽高比放置（contain），
  // 两侧留白补渐变——不再把框尺寸直接交给图片（此前"图片更宽"分支会在 Office 2016 / Mac 上被拉伸）。
  const imgAspect = size.w / size.h;
  const imgW = Math.min(el.w_in, el.h_in * imgAspect);
  const imgH = imgW / imgAspect;
  const sideW = (el.w_in - imgW) / 2;
  const imgX = el.x_in + sideW;
  const edge = cfg.toHex(vs.colors.secondary);
  const bg = cfg.toHex(vs.colors.background);
  gradientRect(slide, pptx, report, {
    x: el.x_in, y: el.y_in, w: sideW, h: el.h_in, angle: 0,
    stops: [{ pos: 0, color: bg, alpha: 100 }, { pos: 100, color: edge, alpha: 100 }],
    fallbackColor: edge, fallbackTransparency: 20,
  });
  gradientRect(slide, pptx, report, {
    x: imgX + imgW, y: el.y_in, w: sideW, h: el.h_in, angle: 180,
    stops: [{ pos: 0, color: bg, alpha: 100 }, { pos: 100, color: edge, alpha: 100 }],
    fallbackColor: edge, fallbackTransparency: 20,
  });
  slide.addImage({ path: p, x: imgX, y: el.y_in + Math.max(0, (el.h_in - imgH) / 2), w: imgW, h: imgH });
  report.image_fill = (report.image_fill || 0) + 1;
  return true;
}

function addChartEl(slide, pptx, el, vs) {
  const c = el.chart || {};
  const map = {
    column: { type: pptx.ChartType.bar, barDir: 'col' },
    bar: { type: pptx.ChartType.bar, barDir: 'bar' },
    line: { type: pptx.ChartType.line },
    pie: { type: pptx.ChartType.pie },
    doughnut: { type: pptx.ChartType.doughnut },
  };
  const spec = map[c.chart_type] || map.column;
  const labels = (c.labels || []).map(String);
  const data = (c.series || []).map((s) => ({ name: s.name || '系列', labels, values: (s.values || []).map(Number) }));
  const font = cfg.resolveFont(undefined, vs);
  slide.addChart(spec.type, data, {
    
    x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in,
    barDir: spec.barDir,
    // v5.5 图表配色：单系列用中性灰，被 highlight_index 指定的重点数据点用强调色；多系列用调色板
    chartColors: (c.highlight_index !== undefined
      ? labels.map((_, i) => cfg.toHex(i === Number(c.highlight_index) ? vs.colors.accent : vs.colors.text_light))
      : ((c.series || []).length > 1 ? (vs.chart_palette || [vs.colors.secondary]) : [vs.colors.secondary]).map(cfg.toHex)),
    showLegend: c.show_legend !== false,
    showValue: !!c.show_value,
    legendFontFace: font, legendFontSize: 11, legendColor: cfg.toHex(vs.colors.text),
    catAxisLabelFontFace: font, catAxisLabelFontSize: 11, catAxisLabelColor: cfg.toHex(vs.colors.text),
    valAxisLabelFontFace: font, valAxisLabelFontSize: 10, valAxisLabelColor: cfg.toHex(vs.colors.text_light),
    dataLabelFontFace: font, dataLabelFontSize: 10,
    dataLabelColor: (c.chart_type === 'pie' || c.chart_type === 'doughnut') ? 'FFFFFF' : cfg.toHex(vs.colors.text),
    showTitle: false,
    fill: cfg.toHex(vs.colors.background),
    // v5.5 图表口径：百分比数据标签 / 百分比数值轴（数据标签用 Caption 层级、轴标题用 H4）
    dataLabelFormatCode: c.show_percent ? '0"%"' : undefined,
    valAxisLabelFormatCode: c.axis_percent ? '0"%"' : undefined,
    border: { pt: 0, color: cfg.toHex(vs.colors.background) },
    catGridLine: { style: 'none' }, valGridLine: { style: 'dash', color: cfg.toHex(vs.colors.text_light), size: 0.5 },
  });
}

function addTableEl(slide, el, vs) {
  const t = el.table || {};
  const rows = (t.rows || []).map((row, ri) => (row || []).map((cell) => ({
    text: String(cell == null ? '' : cell),
    options: {
      fontSize: el.font_pt || 11,
      fontFace: cfg.resolveFont(undefined, vs),
      color: ri === 0 && t.header_row !== false ? 'FFFFFF' : cfg.toHex(vs.colors.text),
      bold: ri === 0 && t.header_row !== false,
      fill: ri === 0 && t.header_row !== false
        ? { color: cfg.toHex(vs.colors.primary) }
        : { color: ri % 2 === 0 ? cfg.toHex(vs.colors.background) : cfg.toHex(vs.colors.background) },
      align: ri === 0 ? 'center' : (typeof cell === 'number' ? 'right' : 'left'),
      valign: 'middle',
      margin: 0.05,
    },
  })));
  slide.addTable(rows, {
    
    x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in,
    colW: t.col_widths_in && t.col_widths_in.length ? t.col_widths_in : undefined,
    rowH: el.h_in / Math.max(1, rows.length),
    border: { type: 'solid', pt: 0.5, color: cfg.toHex(vs.colors.text_light) },
    fontFace: cfg.resolveFont(undefined, vs),
  });
}

function addIconEl(slide, pptx, el, vs, library) {
  const icon = cfg.findIcon(el.icon, library);
  if (!icon) return false;
  const box = { x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in };
  icon.shapes.forEach((p) => {
    const sx = p.x / 100, sy = p.y / 100, sw = p.w / 100, sh = p.h / 100;
    const type = (pptx.ShapeType && pptx.ShapeType[p.shape]) || pptx.ShapeType.rect;
    const color = cfg.resolveToken(p.fill === 'background' ? 'background' : p.fill, vs);
    const opts = {
      x: box.x + sx * box.w, y: box.y + sy * box.h, w: sw * box.w, h: sh * box.h,
      fill: { color },
      line: { color, width: 0 },
    };
    if (p.rotation) opts.rotate = Number(p.rotation);
    if (p.flipH) opts.flipH = true;
    slide.addShape(type, Object.assign({}, opts));
  });
  return true;
}

function addFormulaEl(slide, el, vs, dark) {
  slide.addText(String(el.text || ''), {
    
    x: el.x_in, y: el.y_in, w: el.w_in, h: el.h_in,
    fontSize: el.font_pt || 13,
    fontFace: cfg.resolveFont(undefined, vs),
    color: cfg.resolveToken(el.color || (dark ? 'FFFFFF' : 'text'), vs),
    align: el.align || 'left', valign: el.valign || 'middle', margin: 0, italic: false,
  });
  if (el.style === 'omml_todo') {
    slide.addText('（此公式为复杂排版，需在 PowerPoint 公式编辑器中替换）', {
      x: el.x_in, y: el.y_in + el.h_in, w: el.w_in, h: 0.22,
      fontSize: 9, color: cfg.resolveToken('text_light', vs), fontFace: cfg.resolveFont(undefined, vs), margin: 0,
    });
  }
}

async function build(plan, candidate, out, args) {
  let vs;
  try {
    vs = cfg.loadVisualSystem((plan.design_brief || {}).visual_system);
  } catch (e) {
    console.error(`[构建中止] ${e.message}`);
    process.exit(2);
  }
  vs_cache = vs;
  const deckTitle = String((plan.brief_intent || {}).deck_title || '');
  const nav = cfg.navigationSpec(vs);
  const planNavMode = String((plan.design_brief || {}).navigation_mode || '');
  // v8.9 导航范围：design_brief.navigation_scope 优先，其次配置默认；逐页 show_navigation 可覆盖
  const navScope = String((plan.design_brief || {}).navigation_scope || nav.scope || 'sparse');
  // v8.9 导航总开关：计划级 navigation_enabled（布尔）优先，其次包级 config.navigation.enabled
  const navEnabled = (typeof (plan.design_brief || {}).navigation_enabled === 'boolean')
    ? plan.design_brief.navigation_enabled
    : nav.enabled !== false;
  nav.enabled = navEnabled; // v9.0.1：计划级结果写回，母版侧栏底板与导航条目判定必须同源（默认关闭后尤其关键）
  const seenSection = {};
  if (planNavMode && planNavMode !== nav.mode) nav.mode = planNavMode; // v8.7：导航模式以计划声明为准
  const library = cfg.loadIconLibrary();
  const stylePreset = cfg.resolveStyle((plan.brief_intent || {}).style_preference || vs.image_style);

  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: LAYOUT_NAME, width: cfg.canvas.width_in, height: cfg.canvas.height_in });
  pptx.layout = LAYOUT_NAME;
  pptx.author = 'smart-ppt-designer';
  pptx.company = 'smart-ppt-designer skill package';
  pptx.title = (plan.brief_intent || {}).deck_title || '未命名演示文稿';
  defineMasters(pptx, vs, nav, navEnabled);
  pptx.theme = { headFontFace: cfg.resolveFont(undefined, vs), bodyFontFace: cfg.resolveFont(undefined, vs) };

  const report = {
    candidate: candidate.candidate_id,
    visual_system: vs.__key,
    style_rationale: (plan.design_brief || {}).style_rationale || null,
    navigation: navEnabled ? nav.mode : 'disabled',
    nav_scope: navScope, nav_enabled: navEnabled, nav_pages: [],
    sections: (plan.design_brief || {}).sections || [],
    slides: [], notes_count: 0, images_used: 0, images_fallback: [], effects_used: 0, effects_fallback: [],
    decoration_sets_used: 0, decoration_shapes: 0, decoration_missing: [],
    components_used: 0, component_shapes: 0, components_missing: [],
    charts: 0, tables: 0, icons: 0, gradients: [], masters: Object.values(MASTERS).filter((v, i, s) => s.indexOf(v) === i),
  };

  const darkMode = vs.mode === 'dark';

  for (const s of candidate.slides || []) {
    report._current = (report.slides || []).length;
    const isCoverLike = ['cover', 'toc', 'section_divider', 'closing'].includes(s.slide_type);
    // v9.0.6 本机适配（红线 28，用户 2026-11-08 指定）：封面强制 AI 书法体
    // 缺图 / 文件不存在 / 仍用系统字主标 → 直接抛错，不产出残稿；不可关闭、不可降级
    if (s.slide_type === 'cover' && (cfg.cover_title || {}).enforced) {
      const els0 = Array.isArray(s.elements) ? s.elements : [];
      const isCallig = (e) => e && (e.type === 'image' || e.type === 'effect') &&
        /calligraphy|shufa|书法/i.test(String(e.template || e.image_path || e.effect_path || ''));
      const hasCallig = els0.some(isCallig);
      const textTitle = els0.find((e) => e && e.type === 'text' &&
        (e.role === 'title' || /书法|calligraphy/i.test(String(e.name || ''))));
      let missingFile = null;
      for (const e of els0) {
        if (!isCallig(e)) continue;
        const ip = e.image_path || e.effect_path;
        if (ip && !require('fs').existsSync(require('path').resolve(args.imagesDir || '.', ip))) {
          missingFile = ip; break;
        }
      }
      if (!hasCallig || textTitle || missingFile) {
        const why = !hasCallig ? '封面没有 AI 书法主标图'
          : missingFile ? ('书法图文件不存在：' + missingFile)
          : '封面主标仍是系统字体文本框（不得用系统字冒充书法）';
        throw new Error('[FATAL] 封面强制 AI 书法体（cover_title.enforced=true）：' + why
          + '。请先用生图插件生成透明底书法 PNG 并回填，再构建；本配置不可降级、不可关闭。');
      }
    }
    const slide = pptx.addSlide(masterFor(s));
    const hasImageEl = Array.isArray(s.elements) && s.elements.some((e) => e && e.type === 'image');
    let bgDesc = '母版底色';

    // 1) 整页背景图（封面/章节/结尾）
    const bgImage = isCoverLike && s.image_required && s.image_type !== 'concept_illustration'
      ? resolveAsset(s.image_path, args.imagesDir)
      : null;
    if (bgImage) {
      slide.addImage({ path: bgImage, x: 0, y: 0, w: cfg.canvas.width_in, h: cfg.canvas.height_in });
      // v5.5 高级封面：大字压图 + 整页"上部浅、下部深"的渐变蒙版（保证白字对比度 ≥ 4.5:1）
      gradientRect(slide, pptx, report, {
        x: 0, y: 0, w: cfg.canvas.width_in, h: cfg.canvas.height_in,
        angle: 90,
        // v9.0.2 并入（补丁包）：封面蒙版可配置（cover_mask；亮场浅色低透明 / 深场原深色蒙版）
        ...(() => {
          const cm = cfg.cover_mask || {};
          const light = cm.mode === 'light';
          const color = light ? (cm.color || 'FFFFFF') : cfg.toHex(vs.colors.primary);
          const def = light
            ? [{ pos: 0, alpha: 20 }, { pos: 30, alpha: 14 }, { pos: 55, alpha: 16 }, { pos: 100, alpha: 26 }]
            : [{ pos: 0, alpha: 78 }, { pos: 30, alpha: 74 }, { pos: 55, alpha: 80 }, { pos: 100, alpha: 92 }];
          const stops = (cm.stops && cm.stops.length ? cm.stops : def)
            .map((x) => ({ pos: x.pos, color, alpha: x.alpha }));
          return { stops, fallbackColor: color, fallbackTransparency: light ? 16 : 80 };
        })(),
      });
      report.images_used += 1;
      bgDesc = '整页配图 + 整页渐变蒙版（上部浅 / 下部深）';
    } else if (isCoverLike) {
      // v9.0.2 并入（补丁包）：亮场封面纯色降级取视觉系统 background，深场仍取 primary
      const solid = ((cfg.cover_mask || {}).mode === 'light')
        ? cfg.toHex(vs.colors.background)
        : cfg.toHex(vs.colors.primary);
      slide.addShape(pptx.ShapeType.rect, {
        x: 0, y: 0, w: cfg.canvas.width_in, h: cfg.canvas.height_in,
        fill: { color: solid }, line: { color: solid, width: 0 },
      });
      bgDesc = `纯色降级 #${solid}`;
      if (s.image_required) report.images_fallback.push({ slide_id: s.slide_id, reason: s.image_path ? '图片文件缺失' : '无 image_path（生图/图库不可用）', level: '纯色背景' });
    }

    // 2) 概念页插图（模型显式给了 image 元素则用元素坐标）
    if (s.image_required && s.image_type === 'concept_illustration' && !isCoverLike && !hasImageEl) {
      const p = resolveAsset(s.image_path, args.imagesDir);
      if (p) {
        slide.addImage({ path: p, x: 7.1, y: 1.6, w: 5.6, h: 4.4 });
        report.images_used += 1;
      } else {
        report.images_fallback.push({ slide_id: s.slide_id, reason: '概念插图缺失', level: '无插图' });
      }
    }

    // 3) 章节导航（v8.9：按 scope 与逐页 show_navigation 决定，避免每页都出现侧栏）
    let _drawNav;
    if (typeof s.show_navigation === 'boolean') {
      _drawNav = s.show_navigation;          // 优先级最高：逐页声明
    } else if (!navEnabled) {
      _drawNav = false;                       // 其次：计划级总开关（关闭 = 全篇不画）
    } else if (navScope === 'none') {
      _drawNav = false;
    } else if (navScope === 'full') {
      _drawNav = !isCoverLike;
    } else { // sparse（默认）：只画每章的首个内容页；章节页不画（左侧留给 section-rail 装饰轨道）
      if (!isCoverLike) {
        const _k = String(s.section_name || '');
        _drawNav = !seenSection[_k];
        if (_drawNav) seenSection[_k] = true;
      } else {
        _drawNav = false;
      }
    }
    if (_drawNav) drawNavigation(slide, pptx, nav, report.sections, s.section_name);
    report.nav_pages.push({ slide_id: s.slide_id, nav: _drawNav });

    // 3.5) 章节过渡页：超大半透明章节编号（L2 装饰层）+ 装饰线（v5.5）
    if (s.slide_type === 'section_divider') {
      const num = s.section_number !== undefined ? s.section_number : report.slides.filter((x) => x.slide_type === 'section_divider').length + 1;
      const numText = String(num).padStart(2, '0');
      slide.addText(numText, {
        x: cfg.canvas.width_in - 4.2, y: 0.4, w: 3.8, h: 2.6,
        fontSize: 120, fontFace: cfg.resolveFont(undefined, vs), color: 'FFFFFF',
        bold: true, align: 'right', valign: 'middle', margin: 0, transparency: 72,
      });
      slide.addShape(pptx.ShapeType.rect, {
        x: 0.9, y: 5.25, w: 3.2, h: 0.06,
        fill: { color: cfg.toHex(vs.colors.accent) }, line: { color: cfg.toHex(vs.colors.accent), width: 0 },
      });
      report.section_numbers = (report.section_numbers || []).concat([{ slide_id: s.slide_id, number: numText }]);
    }

    // 4)+5) 图层顺序绘制（v5.2 多图层堆叠：L1 背景 → L2 装饰 → L3 内容 → L4 标题）
    // 背景层（L1）已在上方由 image_path / 母版处理；这里把特效（默认 L2，z=12）与元素按 z_index 升序统一排序后绘制，
    // 保证装饰永远在内容与标题之下（红线第 11 条）。
    let rendered = 0;
    const drawItems = [];
    for (const ef of s.effects || []) {
      drawItems.push({ z: Number(ef.z_index !== undefined ? ef.z_index : 12), kind: 'effect', data: ef });
    }
    for (const el of s.elements || []) {
      drawItems.push({ z: Number(el.z_index !== undefined ? el.z_index : 20), kind: 'element', data: el });
    }
    drawItems.sort((a, b) => a.z - b.z);
    const layerCounts = { L2: 0, L3: 0, L4: 0 };
    for (const item of drawItems) {
      const z = item.z;
      if (z >= 30) layerCounts.L4 += 1;
      else if (z >= 20) layerCounts.L3 += 1;
      else if (z >= 10) layerCounts.L2 += 1;

      if (item.kind === 'effect') {
        const ef = item.data;
        const template = cfg.findEffectTemplate(ef.template) || {};
        const p = resolveAsset(ef.effect_path, args.effectsDir);
        if (p) {
          slide.addImage({ path: p, x: ef.x_in, y: ef.y_in, w: ef.w_in, h: ef.h_in });
          report.effects_used += 1;
        } else {
          if (ef.on_fail === 'solid_title_bar' || template.fallback) {
            slide.addShape(pptx.ShapeType.rect, {
              x: ef.x_in, y: ef.y_in + 0.25, w: 0.1, h: Math.max(0.3, ef.h_in - 0.5),
              fill: { color: cfg.toHex(vs.colors.accent) }, line: { color: cfg.toHex(vs.colors.accent), width: 0 },
            });
          }
          report.effects_fallback.push({ slide_id: s.slide_id, template: ef.template, level: '原生降级' });
        }
        continue;
      }

      const el = item.data;
      try {
        if (el.type === 'text') { addTextEl(slide, el, vs, isCoverLike); rendered += 1; }
        else if (el.type === 'shape') { addShapeEl(slide, pptx, el, vs); rendered += 1; }
        else if (el.type === 'chart') { addChartEl(slide, pptx, el, vs); report.charts += 1; rendered += 1; }
        else if (el.type === 'table') { addTableEl(slide, el, vs); report.tables += 1; rendered += 1; }
        else if (el.type === 'icon') { if (addIconEl(slide, pptx, el, vs, library)) { report.icons += 1; rendered += 1; } }
        else if (el.type === 'image') { if (addImageFitEl(slide, pptx, el, args.imagesDir, report, vs)) { report.images_used += 1; rendered += 1; } else { report.images_fallback.push({ slide_id: s.slide_id, reason: '页面内图片缺失', level: '跳过' }); } }
        else if (el.type === 'formula') { addFormulaEl(slide, el, vs, isCoverLike); rendered += 1; }
        else if (el.type === 'decoration_set') { if (addDecorationSetEl(slide, pptx, el, vs, report, s.slide_id)) { rendered += 1; } }
        else if (el.type === 'component') { if (addComponentEl(slide, pptx, el, vs, report, plan, s.slide_id)) { rendered += 1; } }
      } catch (err) {
        report.slides.push({ slide_id: s.slide_id, error: `${el.type} 元素渲染失败：${err.message}` });
      }
    }
    report.layers = report.layers || { L2_items: 0, L3_items: 0, L4_items: 0, slides_missing_z: 0 };
    report.layers.L2_items += layerCounts.L2;
    report.layers.L3_items += layerCounts.L3;
    report.layers.L4_items += layerCounts.L4;
    if ((s.elements || []).some((e) => !e || e.z_index === undefined)) {
      report.layers.slides_missing_z += 1;
    }

    if (rendered === 0) {
      const pt = s.slide_type === 'cover' ? (vs.fonts.title_size ? vs.fonts.title_size[1] : 32) : s.slide_type === 'section_divider' ? (vs.fonts.section_size ? vs.fonts.section_size[1] : 24) : (vs.fonts.body_size ? vs.fonts.body_size[1] + 2 : 16);
      slide.addText(String(s.claim || `第 ${s.slide_id} 页`), {
        x: 1.38, y: isCoverLike ? 2.9 : 0.42, w: 11.45, h: isCoverLike ? 1.5 : 0.95,
        fontSize: pt, fontFace: cfg.resolveFont(undefined, vs), color: cfg.toHex(isCoverLike ? 'FFFFFF' : vs.colors.text),
        bold: true, align: 'left', valign: 'middle', margin: 0, lineSpacingMultiple: 1.2,
      });
      rendered += 1;
    }

    // 6) 页脚（v5.5 页脚规范：底部左侧项目/团队名 + 右侧页码，10–11pt，位置固定；封面用信息行替代）
    const fc = cfg.config.footer || {};
    if (fc.enabled !== false && s.slide_type !== 'cover') {
      const footPt = fc.left_pt || 10;
      slide.addText(deckTitle, {
        x: 1.38, y: cfg.canvas.height_in - 0.45, w: 7.0, h: 0.3,
        fontSize: footPt, fontFace: cfg.resolveFont(undefined, vs), color: cfg.resolveToken(fc.left_color || 'text_light', vs),
        align: 'left', valign: 'middle', margin: 0,
      });
      slide.addText(String(s.slide_id), {
        x: cfg.canvas.width_in - 1.1, y: cfg.canvas.height_in - 0.45, w: 0.5, h: 0.3,
        fontSize: fc.right_pt || 10, fontFace: cfg.resolveFont(undefined, vs), color: cfg.resolveToken(fc.left_color || 'text_light', vs),
        align: 'right', valign: 'middle', margin: 0,
      });
    }

    // 7) 讲者备注（红线第 14 条：每页必须有）
    const notes = String(s.notes || '').trim();
    slide.addNotes(notes || `页面主张：${s.claim || ''}\n（警告：页面计划未提供完整 notes，建议补齐）`);
    if (notes) report.notes_count += 1;

    report.slides.push({
      slide_id: s.slide_id, slide_type: s.slide_type, master: masterFor(s), layout_template: s.layout_template,
      card_used: s.card_used, section_name: s.section_name || null, background: bgDesc,
      rendered_elements: rendered, has_notes: !!notes,
    });
  }

  fs.mkdirSync(path.dirname(out), { recursive: true });
  await pptx.writeFile({ fileName: out });
  report.xml_post_process = await postProcessXml(out, report);
  return report;
}

async function main() {
  const args = parseArgs(process.argv);
  const plan = JSON.parse(fs.readFileSync(args.plan, 'utf8'));
  const candidate = (plan.candidates || []).find((c) => c.candidate_id === args.candidate);
  if (!candidate) throw new Error(`页面计划里没有候选方案 ${args.candidate}`);
  const report = await build(plan, candidate, args.out, args);
  console.log(`[build] 方案 ${args.candidate} → ${args.out}`);
  console.log(`  视觉系统：${report.visual_system}（不设默认，按内容检索选定）｜选择理由：${report.style_rationale || '未填写'}｜导航：${report.navigation}｜章节 ${report.sections.length} 个`);
  console.log(`  页数 ${report.slides.length}｜讲者备注 ${report.notes_count}/${report.slides.length}｜配图 ${report.images_used} 张｜特效 ${report.effects_used} 处｜原生图表 ${report.charts} 个｜原生表格 ${report.tables} 个｜图标 ${report.icons} 个`);
  if (report.layers) console.log(`  图层：L2 装饰 ${report.layers.L2_items}｜L3 内容 ${report.layers.L3_items}｜L4 标题 ${report.layers.L4_items}｜缺 z_index 的页 ${report.layers.slides_missing_z}`);
  if (report.xml_post_process) {
    const ppx = report.xml_post_process;
    console.log(`  XML 后处理：图表分类修正 ${ppx.chart_categories_fixed}/${ppx.charts_scanned}｜渐变填充写入 ${ppx.gradients_written} 处｜淡入转场写入 ${ppx.transitions_written} 页｜装饰组建组 ${ppx.groups_written} 处`);
  }
  if (report.decoration_sets_used) console.log(`  装饰组：${report.decoration_sets_used} 组 / ${report.decoration_shapes} 个图元`);
  if (report.components_used) console.log(`  组件复用：${report.components_used} 次 / ${report.component_shapes} 个图元`);
  {
    let _pl = null;
    try { _pl = JSON.parse(fs.readFileSync(args.plan, 'utf8')); } catch (e) { _pl = null; }
    const _lv = creativeLevel(_pl);
    const _conf = (cfg.config.creative_level || {});
    const _label = (((_conf.levels || {})[_lv]) || {}).label || '';
    console.log(`  创意度：${_lv}${_label ? '（' + _label + '）' : ''}｜默认档 ${_conf.default || 'off'}`);
  }
  if (report.section_numbers) console.log(`  章节编号：${report.section_numbers.map((x) => `第${x.slide_id}页=${x.number}`).join('、')}`);
  if (report.image_fill) console.log(`  图片渐变填补：${report.image_fill} 处`);
  if (report.nav_pages) {
    const _on = report.nav_pages.filter((x) => x.nav).length;
    console.log(`  卡片精致度：序号带 ${_cardIdxSeq} 个｜投影写入 ${report.card_shadow_pages || 0} 页`);
    console.log(`  导航：${report.nav_enabled ? '开启' : '关闭'}｜范围 ${report.nav_scope}｜带栏 ${_on}/${report.nav_pages.length} 页（关闭用 design_brief.navigation_enabled=false；逐页可用 slides[].show_navigation 覆盖）`);
  }
  if (report.font_stats) {
    const _fs = report.font_stats;
    console.log(`  字体声明：latin ${_fs.latin} / ea ${_fs.ea} / cs ${_fs.cs}（跨客户端兼容；PptxGenJS 已自带 ea，兜底补 ${report.font_declared} 页——见 references/compatibility.md）`);
  }
  if (report.images_fallback.length) console.log(`  配图降级：${report.images_fallback.map((f) => `第${f.slide_id}页(${f.level})`).join('、')}`);
  if (report.effects_fallback.length) console.log(`  特效降级：${report.effects_fallback.map((f) => `第${f.slide_id}页(${f.template})`).join('、')}`);
  const rc = path.join(path.dirname(args.out), 'build_report.json');
  fs.writeFileSync(rc, JSON.stringify({ plan: args.plan, out: args.out, generated_at: new Date().toISOString(), ...report }, null, 2), 'utf8');
  console.log(`  构建报告：${rc}`);
  return 0;
}

main().then((c) => process.exit(c)).catch((e) => { console.error(`[FAIL] ${e && e.message ? e.message : e}`); process.exit(1); });