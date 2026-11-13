#!/usr/bin/env node
/**
 * generate_effects.js —— 视觉特效素材（烫金标题 / 发光装饰 / 纹样边框 / 科技粒子）清单与回填
 *
 * 红线第 9 条：烫金、发光、渐变文字等效果**统一用生图 PNG 作装饰层**，
 * 禁止用 PptxGenJS 硬做；本脚本同样不自实现生图（第 7 条），只产出清单与回填路径。
 * 装饰层必须在文字层之下（build_pptx.js 已按 背景 → 特效 → 蒙版 → 文字 顺序绘制）。
 *
 * 用法：
 *   node scripts/generate_effects.js --plan output/plan.json --candidate A --emit output/effect_requests.json
 *   node scripts/generate_effects.js --plan output/plan.json --candidate A --fill output/effects
 *   node scripts/generate_effects.js --plan output/plan.json --candidate A --list
 */
const fs = require('fs');
const path = require('path');
const cfg = require('../assets/pptxgenjs-config.js');

const EXT = ['.png'];
const DEFAULT_DIR = 'output/effects';

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
      console.log('用法：node scripts/generate_effects.js --plan <plan.json> --candidate A|B [--emit x.json | --fill dir | --list]');
      process.exit(0);
    }
  }
  if (!a.plan) throw new Error('缺少 --plan 参数');
  return a;
}

function expand(template, argsObj) {
  let s = String(template || '');
  Object.entries(argsObj || {}).forEach(([k, v]) => {
    s = s.split(`{${k}}`).join(String(v));
  });
  return s.replace(/\{[a-z_]+\}/g, '').replace(/，{2,}/g, '，').trim();
}

/** 特效目标文件名：effect_{template}_{slide_id}.png */
function effectName(template, slideId) {
  return `effect_${template}_${slideId}.png`;
}

function collect(plan, cand, args) {
  const vs = cfg.loadVisualSystem((plan.design_brief || {}).visual_system);
  const slideList = (cand.slides || []).filter((s) => Array.isArray(s.effects) && s.effects.length);
  const filtered = args.onlySlide ? slideList.filter((s) => s.slide_id === args.onlySlide) : slideList;
  const items = [];
  for (const s of filtered) {
    for (const ef of s.effects) {
      const tpl = cfg.findEffectTemplate(ef.template);
      if (!tpl) continue;
      const promptArgs = Object.assign({ color_hint: vs.__key, blank_position: '画面左侧' }, ef.prompt_args || {});
      items.push({
        slide_id: s.slide_id,
        template: ef.template,
        label: tpl.label,
        transparent: tpl.transparent !== false,
        size: tpl.size,
        prompt: expand(tpl.prompt_template, promptArgs),
        target_name: effectName(ef.template, s.slide_id),
        on_fail: ef.on_fail || tpl.fallback,
      });
    }
  }
  return { vs, items };
}

function emit(plan, cand, args) {
  const { vs, items } = collect(plan, cand, args);
  const payload = {
    _note: '特效素材待生图清单。由 DSH 调用生图插件；透明底素材返回实底时按失败处理（改用原生降级）。',
    tier: 1,
    tool: cfg.image.tool,
    visual_system: vs.__key,
    max_per_deck: cfg.config.effects.max_per_deck,
    requests: items.map((i) => Object.assign({}, i, { target_path: path.join(DEFAULT_DIR, i.target_name) })),
  };
  const out = args.emit || path.join(DEFAULT_DIR, 'effect_requests.json');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(payload, null, 2), 'utf8');
  console.log(`[emit] 特效请求 ${items.length} 项（预算上限 ${cfg.config.effects.max_per_deck}）`);
  items.forEach((i) => console.log(`  - 第${i.slide_id}页 ${i.template}（${i.label}）透明=${i.transparent} ${i.size[0]}×${i.size[1]} → ${i.target_name}`));
  console.log(`[emit] 清单：${out}`);
  if (items.length > cfg.config.effects.max_per_deck) console.warn(`[warn] 特效 ${items.length} 项超过预算 ${cfg.config.effects.max_per_deck}`);
  return items;
}

function fill(plan, cand, args) {
  const dir = args.fill || DEFAULT_DIR;
  const planDir = path.dirname(args.plan);
  let filled = 0, missing = 0;
  const rows = [];
  for (const s of cand.slides || []) {
    for (const ef of s.effects || []) {
      if (args.onlySlide && s.slide_id !== args.onlySlide) continue;
      const name = effectName(ef.template, s.slide_id);
      const candidates = EXT.map((e) => path.join(dir, name.replace(/\.png$/, e)));
      const found = candidates.find((p) => fs.existsSync(p));
      if (found) {
        ef.effect_path = path.relative(planDir, found).split(path.sep).join('/');
        filled += 1;
        rows.push({ slide_id: s.slide_id, template: ef.template, status: 'filled', effect_path: ef.effect_path });
      } else {
        ef.effect_path = null;
        missing += 1;
        const _isCallig = /calligraphy|书法/i.test(String(ef.template || ''));
        rows.push({ slide_id: s.slide_id, template: ef.template, status: 'missing',
          next: _isCallig && (cfg.cover_title || {}).enforced
            ? '【阻断】封面强制 AI 书法：无降级路径，必须重新生图（validate_plan 会报 error、build_pptx 会退出）'
            : '原生降级（' + (ef.on_fail || 'solid_title_bar') + '）' });
      }
    }
  }
  fs.writeFileSync(args.plan, JSON.stringify(plan, null, 2) + '\n', 'utf8');
  console.log(`[fill] 特效已回填 ${filled} 处，缺失 ${missing} 处（缺失处将走原生降级实现）`);
  rows.forEach((r) => console.log(`  - 第${r.slide_id}页 ${r.template}：${r.status === 'filled' ? r.effect_path : r.next}`));
  return rows;
}

function list(plan, cand) {
  let total = 0;
  for (const s of cand.slides || []) {
    const n = (s.effects || []).length;
    total += n;
    if (n) console.log(`  第${s.slide_id}页：${s.effects.map((e) => `${e.template}${e.effect_path ? ' ✓' : '（待生成）'}`).join('、')}`);
  }
  console.log(`方案 ${cand.candidate_id} 特效合计 ${total} 处（预算上限 ${cfg.config.effects.max_per_deck}）`);
}

function main() {
  const args = parseArgs(process.argv);
  const plan = JSON.parse(fs.readFileSync(args.plan, 'utf8'));
  const cand = (plan.candidates || []).find((c) => c.candidate_id === args.candidate);
  if (!cand) throw new Error(`页面计划里没有候选方案 ${args.candidate}`);
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