/**
 * PptxGenJS 全局配置模块（v5.1）
 * 提供：配置读取、视觉系统、颜色 token、字体白名单、图标库、布局模板、导航参数。
 * 用法：const cfg = require('../assets/pptxgenjs-config.js')
 */
const fs = require('fs');
const path = require('path');

const ASSETS_DIR = __dirname;

function readJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(ASSETS_DIR, rel), 'utf8'));
}

const config = readJson('config.json');
const imageStyles = readJson('image-styles.json');

/** pptxgenjs 颜色不带 '#'，统一归一化 */
function toHex(color) {
  if (!color) return undefined;
  return String(color).replace(/^#/, '').toUpperCase();
}

/** 字体白名单过滤：不在白名单内的一律回落（红线：禁止自由选字体） */
function resolveFont(fontName, system) {
  const list = config.fonts.whitelist;
  if (fontName && list.includes(fontName)) return fontName;
  if (system && system.fonts && list.includes(system.fonts.body)) return system.fonts.body;
  return config.fonts.default_cn;
}

/** 生图提示词风格（仅影响生图 prompt，不参与整稿配色/字体）：优先显式值，其次视觉系统的 image_style；都缺时用 minimal 并标记 */
function resolveStyle(styleKey) {
  if (styleKey && imageStyles[styleKey]) return imageStyles[styleKey];
  const fallback = Object.keys(imageStyles).find((k) => !k.startsWith('_')) || 'minimal';
  return Object.assign({}, imageStyles[fallback], {
    _fallback_used: true, _fallback_from: styleKey || null,
    _note: '未指定生图提示词风格，已用 minimal 兜底；仅影响生图提示，不影响整稿视觉系统',
  });
}

function resolveImageSize(imageType) {
  const sizes = config.image.sizes;
  const px = sizes[imageType] || sizes.concept_illustration;
  return { width: px[0], height: px[1] };
}

function safeArea() {
  const c = config.canvas;
  const m = c.margin_in;
  return {
    x: m.left,
    y: m.top,
    w: +(c.width_in - m.left - m.right).toFixed(3),
    h: +(c.height_in - m.top - m.bottom).toFixed(3),
  };
}

/** 读取一套视觉系统（v5.6：不设默认，未指定或不存在一律报错，不做兜底回落） */
function loadVisualSystem(name) {
  const dir = config.visual_system.dir.replace(/^assets\//, '');
  const key = String(name === undefined || name === null ? '' : name).trim();
  let avail = [];
  // 个人风格库（v8.2）：assets/personal-styles/，与内置系统同 schema，一并列出与查找
  for (const d of [dir, 'personal-styles']) {
    try {
      avail.push(...fs.readdirSync(path.join(ASSETS_DIR, d))
        .filter((f) => f.endsWith('.json'))
        .map((f) => f.replace(/\.json$/, '')));
    } catch (e) { /* 目录缺失时跳过，由下面的报错提示 */ }
  }
  avail = [...new Set(avail)].sort();
  if (!key) {
    throw new Error(`未指定视觉系统：请在 design_brief.visual_system 明确选择一套（不设默认，不做回落）。`
      + `可选：${avail.join(' / ')}｜检索：python scripts/find_style.py <内容关键词>`);
  }
  const file = path.join(ASSETS_DIR, dir, `${key}.json`);
  const personal = path.join(ASSETS_DIR, 'personal-styles', `${key}.json`);
  const target = fs.existsSync(file) ? file : (fs.existsSync(personal) ? personal : null);
  if (!target) {
    throw new Error(`视觉系统不存在：${key}。可选：${avail.join(' / ')}`
      + `｜检索：python scripts/find_style.py <内容关键词>｜不要回落默认风格`);
  }
  const vs = JSON.parse(fs.readFileSync(target, 'utf8'));
  vs.__key = key;
  return vs;
}

/** 颜色 token → 十六进制；非 token 视为已是色值 */
function resolveToken(token, system) {
  if (!token) return undefined;
  const t = String(token);
  if (system && system.colors && system.colors[t]) return toHex(system.colors[t]);
  if (/^[0-9A-Fa-f]{6}$/.test(t) || /^#[0-9A-Fa-f]{6}$/.test(t)) return toHex(t);
  const themeMap = {
    primary: config.theme.primary,
    secondary: config.theme.accent,
    accent: config.theme.accent,
    background: config.theme.background,
    surface: config.theme.surface || config.theme.background,
    card: config.theme.card || config.theme.background,
    text: config.theme.text,
    text_light: config.theme.muted,
  };
  const resolved = themeMap[t] || (system && system.colors && system.colors[t]) || t;
  if (!/^#?[0-9A-Fa-f]{6}$/.test(String(resolved))) {
    console.warn(`[token] 未知取值 token ${t}，回落 accent（请用视觉系统颜色键或 6 位色值）`);
    return toHex(config.theme.accent);
  }
  return toHex(resolved);
}

/** 视觉系统字号区间 */
function fontRange(system, role) {
  const f = (system && system.fonts) || {};
  const map = {
    title: f.title_size,
    section: f.section_size,
    module: f.body_size ? [f.body_size[1] + 2, f.body_size[1] + 4] : undefined,
    body: f.body_size,
    caption: f.caption_size,
    metric: f.metric_size,
  };
  return map[role] || undefined;
}

function loadIconLibrary() {
  return readJson(config.icons.library.replace(/^assets\//, ''));
}

function findIcon(name, library) {
  return (library.icons || {})[name];
}

function findLayoutTemplate(name) {
  const file = path.join(ASSETS_DIR, config.layout_templates.dir.replace(/^assets\//, ''), `${name}.json`);
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null;
}

function findEffectTemplate(name) {
  const file = path.join(ASSETS_DIR, config.effects.templates_dir.replace(/^assets\//, ''), `${name}.json`);
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null;
}

/** 导航参数：合并视觉系统与全局配置 */
function navigationSpec(system) {
  const nav = config.navigation || {};
  const vsNav = (system && system.navigation) || {};
  return {
    enabled: nav.enabled !== false,
    mode: vsNav.mode || nav.mode || 'sidebar',
    scope: vsNav.scope || nav.scope || 'sparse',
    sideWidthIn: nav.side_width_in || 1.18,
    topHeightIn: nav.top_height_in || 0.59,
    activeColor: toHex(vsNav.active_color || config.theme.accent),
    inactiveColor: toHex(vsNav.inactive_color || nav.inactive_color || 'C9D3DD'),
    textActive: toHex(vsNav.text_active || 'FFFFFF'),
    textInactive: toHex(vsNav.text_inactive || '5B6B7C'),
    titlePt: nav.title_pt || 11,
  };
}

module.exports = {
  config,
  imageStyles,
  theme: config.theme,
  canvas: config.canvas,
  fonts: config.fonts,
  thresholds: config.layout_thresholds,
  image: config.image,
  cover_mask: config.cover_mask,
  cover_title: config.cover_title,
  toHex,
  resolveFont,
  resolveStyle,
  resolveImageSize,
  safeArea,
  loadVisualSystem,
  resolveToken,
  fontRange,
  loadIconLibrary,
  findIcon,
  findLayoutTemplate,
  findEffectTemplate,
  navigationSpec,
};