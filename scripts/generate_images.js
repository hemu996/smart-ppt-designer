#!/usr/bin/env node
/**
 * generate_images.js —— 配图清单生成与路径回填（工作流第 8 步，v5.1）
 *
 * 红线：本脚本**不实现任何生图能力**（第 7 条）。它只做三件事：
 *   1) 从页面计划筛出 image_required=true 的页，按当前**视觉系统**的风格预设拼 prompt；
 *   2) 导出待生图清单（image_requests.json），由 DSH 按 integrations/dsh-image.md 调用生图插件；
 *   3) 把 output/images/ 里落盘的图片路径回填到 image_path（失败则留空，走三级降级）。
 *
 * 三级降级：千问生图（本脚本） → 免费图库（search_photos.js） → 纯色背景（build_pptx.js 自动处理）
 *
 * 用法：
 *   node scripts/generate_images.js --plan output/plan.json --candidate A --emit output/image_requests.json
 *   node scripts/generate_images.js --plan output/plan.json --candidate A --fill output/images
 *   node scripts/generate_images.js --plan output/plan.json --candidate A --list
 *   node scripts/generate_images.js --plan output/plan.json --candidate A --emit out.json --only-slide 5
 */
const fs = require('fs');
const path = require('path');
const cfg = require('../assets/pptxgenjs-config.js');

const EXT = ['.png', '.jpg', '.jpeg', '.webp'];

function parseArgs(argv) {
  const a = { candidate: 'A', plan: null, emit: null, fill: null, onlySlide: null, list: false };
  for (let i = 2; i < argv.length; i += 1) {
    const k = argv[i];
    if (k === '--plan') a.plan = argv[++i];
    else if (k === '--candidate') a.candidate = String(argv[++i]).toUpperCase();
    else if (k === '--emit') a.emit = argv[++i];
    else if (k === '--fill') a.fill = argv[++i];
    else if (k === '--only-slide') a.onlySlide = Number(argv[++i]);
    else if (k === '--list') a.list = true;
    else if (k === '--help' || k === '-h') {
      console.log('用法：node scripts/generate_images.js --plan <plan.json> --candidate A|B [--emit x.json | --fill dir | --list]');
      process.exit(0);
    }
  }
  if (!a.plan) throw new Error('缺少 --plan 参数');
  return a;
}

function readPlan(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function pickCandidate(plan, id) {
  const list = plan.candidates || [];
  const c = list.find((x) => x.candidate_id === id);
  if (!c) throw new Error(`页面计划里没有候选方案 ${id}`);
  return c;
}

function context(plan) {
  const vs = cfg.loadVisualSystem((plan.design_brief || {}).visual_system);
  const styleKey = (plan.brief_intent || {}).style_preference || vs.image_style || 'business';
  return { vs, styleKey, style: cfg.resolveStyle(styleKey) };
}

function subjectOf(slide) {
  const raw = String(slide.claim || '').replace(/[\s、，,。.：:；;！!？?（）()【】\[\]「」"']/g, '');
  return (raw.replace(/^第[一二三四五六七八九十百\d]+[部分章节]/, '').slice(0, 24) || '商务演示主题');
}

function buildPrompt(style, slide, imageType) {
  const subject = subjectOf(slide);
  const tail = '画面内不出现任何文字，不出现写实人物';
  switch (imageType) {
    case 'cover_visual':
      return `${style.style_prompt}，${subject}，${style.background_prompt}，左侧大面积留白，适合叠加白色标题，${tail}`;
    case 'section_background':
      return `${style.style_prompt}，${subject}的概念意境，${style.background_prompt}，低饱和度，适合叠加白色标题，${tail}`;
    case 'concept_illustration':
      return `${style.illustration_prompt || style.style_prompt}，${subject}的示意，浅底，右侧大面积留白，${tail}`;
    case 'closing_background':
      return `${style.style_prompt}，收束、留白、简洁，${style.background_prompt}，${tail}`;
    default:
      return `${style.style_prompt}，${subject}，${style.background_prompt}，${tail}`;
  }
}

function emit(plan, cand, args) {
  const { vs, styleKey, style } = context(plan);
  const slides = (cand.slides || []).filter((s) => s.image_required === true);
  const filtered = args.onlySlide ? slides.filter((s) => s.slide_id === args.onlySlide) : slides;
  const items = filtered.map((s) => {
    const size = cfg.resolveImageSize(s.image_type);
    const name = `slide_${s.slide_id}_${s.image_type}.png`;
    return {
      slide_id: s.slide_id,
      slide_type: s.slide_type,
      image_type: s.image_type,
      size: [size.width, size.height],
      prompt: (s.image_prompt || '').trim() || buildPrompt(style, s, s.image_type),
      prompt_source: (s.image_prompt || '').trim() ? 'plan' : 'generated',
      target_path: path.join(args.fill || cfg.image.output_dir, name),
      target_name: name,
    };
  });
  const payload = {
    _note: '待生图清单（一级）。由 DSH 按 integrations/dsh-image.md 逐项调用生图插件；本文件由 generate_images.js --emit 生成，不要手改。',
    tier: 1,
    tool: cfg.image.tool,
    visual_system: vs.__key,
    style: styleKey,
    style_label: style.label,
    retry: cfg.image.retry,
    on_failure: cfg.image.on_failure,
    fallback_chain: ['复用本稿既有图（封面/章节图，最优先）', 'AI 按本页主题补图（须融入三判据）', '免费图库（scripts/search_photos.js）', '纯色背景（最后兜底）'],
    patch_policy: '缺图先补图，不直接退纯色：优先复用本稿原图；无原图则按本页 claim 生成，且必须与封面同色系/同质感/同留白方位，补完并排目检。见 references/image-strategy.md §一',
    requests: items,
  };
  const out = args.emit || path.join(cfg.image.output_dir, 'image_requests.json');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(payload, null, 2), 'utf8');
  console.log(`[emit] 视觉系统 ${vs.__key}｜风格 ${styleKey}（${style.label}）｜生图请求 ${items.length} 项`);
  items.forEach((i) => console.log(`  - 第${i.slide_id}页 ${i.image_type} ${i.size[0]}×${i.size[1]} → ${i.target_name}`));
  console.log(`[emit] 清单：${out}`);
  if (items.length > cfg.image.max_images_per_deck) console.warn(`[warn] 生图 ${items.length} 张超过预算 ${cfg.image.max_images_per_deck}`);
  return items;
}

function fill(plan, cand, args) {
  const dir = args.fill || cfg.image.output_dir;
  const slides = (cand.slides || []).filter((s) => s.image_required === true);
  const filtered = args.onlySlide ? slides.filter((s) => s.slide_id === args.onlySlide) : slides;
  const planDir = path.dirname(args.plan);
  let filled = 0, missing = 0;
  const out = [];
  for (const s of filtered) {
    const cands = EXT.map((e) => path.join(dir, `slide_${s.slide_id}_${s.image_type}${e}`));
    let found = cands.find((p) => fs.existsSync(p));
    if (!found && fs.existsSync(dir)) {
      const extra = fs.readdirSync(dir).filter((f) => f.startsWith(`slide_${s.slide_id}_`) && EXT.includes(path.extname(f).toLowerCase()));
      if (extra.length) found = path.join(dir, extra[0]);
    }
    if (found) {
      s.image_path = path.relative(planDir, found).split(path.sep).join('/');
      for (const el of s.elements || []) if (el && el.type === 'image' && !el.image_path) el.image_path = s.image_path;
      filled += 1;
      out.push({ slide_id: s.slide_id, status: 'filled', image_path: s.image_path });
    } else {
      s.image_path = null;
      missing += 1;
      out.push({ slide_id: s.slide_id, status: 'missing', next: '先复用本稿既有图 → 按本页主题 AI 补图（须融入）→ 图库 → 纯色兜底' });
    }
  }
  fs.writeFileSync(args.plan, JSON.stringify(plan, null, 2) + '\n', 'utf8');
  console.log(`[fill] 已回填 ${filled} 页，缺图 ${missing} 页（缺图页先复用本稿原图 / AI 按主题补图，最后才纯色兜底）`);
  out.forEach((r) => console.log(`  - 第${r.slide_id}页：${r.status === 'filled' ? r.image_path : '未找到图片 → ' + r.next}`));
  return out;
}

function list(plan, cand) {
  const { vs, styleKey, style } = context(plan);
  console.log(`方案 ${cand.candidate_id}：${(cand.slides || []).length} 页｜视觉系统 ${vs.__key}｜风格 ${styleKey}（${style.label}）`);
  for (const s of cand.slides || []) {
    const img = s.image_required ? `图片=${s.image_type}${s.image_path ? ' ✓' : '（待生成）'}` : '无图';
    console.log(`  第${s.slide_id}页 [${s.slide_type}] ${s.layout_template} 卡片=${s.card_used}｜${img}｜${s.claim}`);
  }
}

function main() {
  const args = parseArgs(process.argv);
  const plan = readPlan(args.plan);
  const cand = pickCandidate(plan, args.candidate);
  if (args.list) return list(plan, cand), 0;
  if (args.fill) return fill(plan, cand, args), 0;
  return emit(plan, cand, args), 0;
}

try {
  process.exit(main());
} catch (err) {
  console.error(`[FAIL] ${err.message}`);
  process.exit(1);
}