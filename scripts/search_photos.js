#!/usr/bin/env node
/**
 * search_photos.js —— 免费图库（Pexels / Pixabay）：配图三级降级中的**第二级**
 *
 * 只在生图不可用、或用户明确要用图库图时使用；仅用于**背景与氛围类**图片
 * （封面/章节页/结尾页），不得用于数据、流程、结构表达。
 *
 * 凭证：只从环境变量读取（PEXELS_API_KEY / PIXABAY_API_KEY），**不写进任何文件**。
 * 无 Key 时跳过本级并输出提示，流程继续走向三级（纯色背景）。
 *
 * 用法：
 *   node scripts/search_photos.js --plan output/plan.json --candidate A --fill output/photos
 *   node scripts/search_photos.js --plan output/plan.json --candidate A --dry-run
 *   node scripts/search_photos.js --plan output/plan.json --candidate A --query-map output/photo_queries.json --fill output/photos
 *
 * 检索词：优先用 --query-map（{ "1": "abstract blue business background", "4": "..." }）；
 * 未提供时按 image_type 生成英文兜底检索词。
 */
const fs = require('fs');
const path = require('path');
const cfg = require('../assets/pptxgenjs-config.js');

const DEFAULT_DIR = 'output/photos';
const TIMEOUT_MS = 20000;

const FALLBACK_QUERY = {
  cover_visual: 'abstract minimal business background blue gradient',
  section_background: 'minimal abstract background soft gradient',
  concept_illustration: 'flat vector illustration concept minimal',
  closing_background: 'calm minimal background soft light',
};

function parseArgs(argv) {
  const a = { candidate: 'A', plan: null, fill: null, queryMap: null, dryRun: false, onlySlide: null };
  for (let i = 2; i < argv.length; i += 1) {
    const k = argv[i];
    if (k === '--plan') a.plan = argv[++i];
    else if (k === '--candidate') a.candidate = String(argv[++i]).toUpperCase();
    else if (k === '--fill') a.fill = argv[++i];
    else if (k === '--query-map') a.queryMap = argv[++i];
    else if (k === '--only-slide') a.onlySlide = Number(argv[++i]);
    else if (k === '--dry-run') a.dryRun = true;
    else if (k === '--help' || k === '-h') {
      console.log('用法：node scripts/search_photos.js --plan <plan.json> --candidate A|B [--fill dir] [--query-map x.json] [--dry-run]');
      process.exit(0);
    }
  }
  if (!a.plan) throw new Error('缺少 --plan 参数');
  return a;
}

function apiKey(provider) {
  const envName = (cfg.config.photos.api_key_env || {})[provider];
  return envName ? process.env[envName] : undefined;
}

async function fetchJson(url, headers) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { headers, signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(t);
  }
}

async function download(url, outPath) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, buf);
    return buf.length;
  } finally {
    clearTimeout(t);
  }
}

async function searchPexels(query) {
  const key = apiKey('pexels');
  if (!key) return null;
  const url = `https://api.pexels.com/v1/search?query=${encodeURIComponent(query)}&per_page=8&orientation=${cfg.config.photos.orientation || 'landscape'}`;
  const data = await fetchJson(url, { Authorization: key });
  const minW = cfg.config.photos.min_width || 1600;
  const photo = (data.photos || []).find((p) => (p.width || 0) >= minW) || (data.photos || [])[0];
  if (!photo) return null;
  return {
    provider: 'pexels',
    url: (photo.src && (photo.src.large2x || photo.src.original || photo.src.large)) || null,
    page_url: photo.url,
    author: photo.photographer,
    license: 'Pexels License（免费商用，无需署名但建议标注来源）',
  };
}

async function searchPixabay(query) {
  const key = apiKey('pixabay');
  if (!key) return null;
  const url = `https://pixabay.com/api/?key=${key}&q=${encodeURIComponent(query)}&image_type=photo&orientation=${cfg.config.photos.orientation === 'landscape' ? 'horizontal' : 'all'}&per_page=8`;
  const data = await fetchJson(url);
  const minW = cfg.config.photos.min_width || 1600;
  const hit = (data.hits || []).find((h) => (h.imageWidth || 0) >= minW) || (data.hits || [])[0];
  if (!hit) return null;
  return {
    provider: 'pixabay',
    url: hit.largeImageURL || hit.webformatURL,
    page_url: hit.pageURL,
    author: hit.user,
    license: 'Pixabay License（免费商用，建议标注来源）',
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const plan = JSON.parse(fs.readFileSync(args.plan, 'utf8'));
  const cand = (plan.candidates || []).find((c) => c.candidate_id === args.candidate);
  if (!cand) throw new Error(`页面计划里没有候选方案 ${args.candidate}`);
  if ((cfg.config.photos || {}).enabled === false) {
    console.log('[info] config.json 的 photos.enabled = false，跳过图库层');
    return 0;
  }

  const qmap = args.queryMap ? JSON.parse(fs.readFileSync(args.queryMap, 'utf8')) : {};
  const targets = (cand.slides || []).filter((s) => s.image_required === true
    && (!s.image_path || String(s.image_path).trim() === '')
    && (args.onlySlide ? s.slide_id === args.onlySlide : true));

  if (!targets.length) {
    console.log('[info] 没有待补配图的页（均已生图或无 image_required），无需调用图库');
    return 0;
  }

  const hasKey = ['pexels', 'pixabay'].some((p) => apiKey(p));
  const dir = args.fill || DEFAULT_DIR;
  const planDir = path.dirname(args.plan);
  let filled = 0, missing = 0;
  const records = [];

  for (const s of targets) {
    const query = qmap[String(s.slide_id)] || qmap[s.image_type] || FALLBACK_QUERY[s.image_type] || FALLBACK_QUERY.section_background;
    if (args.dryRun || !hasKey) {
      records.push({ slide_id: s.slide_id, query, status: args.dryRun ? 'dry-run' : 'skipped-no-key' });
      missing += 1;
      continue;
    }
    let hit = null, err = null;
    for (const provider of ['pexels', 'pixabay']) {
      try {
        hit = provider === 'pexels' ? await searchPexels(query) : await searchPixabay(query);
        if (hit) break;
      } catch (e) { err = e; }
    }
    if (!hit || !hit.url) {
      records.push({ slide_id: s.slide_id, query, status: 'not-found', error: err ? err.message : null });
      missing += 1;
      continue;
    }
    const outName = `slide_${s.slide_id}_${s.image_type}.${hit.url.includes('.png') ? 'png' : 'jpg'}`;
    const outPath = path.join(dir, outName);
    try {
      const bytes = await download(hit.url, outPath);
      s.image_path = path.relative(planDir, outPath).split(path.sep).join('/');
      s.photo_source = { provider: hit.provider, page_url: hit.page_url, author: hit.author, license: hit.license };
      filled += 1;
      records.push({ slide_id: s.slide_id, query, status: 'filled', image_path: s.image_path, bytes, source: s.photo_source });
    } catch (e) {
      records.push({ slide_id: s.slide_id, query, status: 'download-failed', error: e.message });
      missing += 1;
    }
  }

  if (!args.dryRun && hasKey) {
    fs.writeFileSync(args.plan, JSON.stringify(plan, null, 2) + '\n', 'utf8');
    const recFile = path.join(dir, 'photo_sources.json');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(recFile, JSON.stringify({ generated_at: new Date().toISOString(), records }, null, 2), 'utf8');
    console.log(`[fill] 图库回填 ${filled} 页，未命中/失败 ${missing} 页（这些页将走三级：纯色背景）`);
    console.log(`[fill] 来源与授权记录：${recFile}`);
  } else if (!hasKey) {
    console.log('[info] 未配置 PEXELS_API_KEY / PIXABAY_API_KEY → 跳过二级降级（免费图库）');
    console.log('       三级降级为纯色背景，由 build_pptx.js 自动处理，流程不中断。');
  }
  records.forEach((r) => console.log(`  - 第${r.slide_id}页 [${r.status}] query="${r.query}"`));
  return 0;
}

main().then((c) => process.exit(c)).catch((e) => { console.error(`[FAIL] ${e && e.message ? e.message : e}`); process.exit(1); });