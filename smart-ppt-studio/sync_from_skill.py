# -*- coding: utf-8 -*-
"""从已安装的 smart-ppt-designer 实时抽取数据，生成侧边栏插件的 data/styles.json。

v2 改进：
  · 命令不再只从 SKILL.md 抽 —— 追加扫描 scripts/ 目录，
    自动为「SKILL.md 里没写但包里存在」的脚本补一条标准命令（9.0.2 新增的两个布局脚本就是这样漏的）
  · 版本号正则支持三段（9.0.2）
  · 抽取用户既定偏好（封面 AI 书法 / 亮底禁金 / 渐变蒙版）注入插件文案
"""
import json, io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

SKILL = r'C:/Users/34787/.dsh/skills/smart-ppt-designer'
PLUG = r'D:/文档/deepseek-harness/default-workspace/smart-ppt-studio'
skill_md = io.open(os.path.join(SKILL, 'SKILL.md'), encoding='utf-8').read()

# ---------- 版本号 ----------
vm = re.search(r'smart-ppt-designer v([0-9]+(?:\.[0-9]+){1,2})', skill_md)
VERSION = vm.group(1) if vm else '8.3'
print('技能版本:', VERSION)

# ---------- 风格库 ----------
idx = json.load(io.open(os.path.join(SKILL, 'assets/style-index.json'), encoding='utf-8'))
styles = []
for s in idx['styles']:
    styles.append({
        'name': s.get('name', ''), 'label': s.get('label', ''),
        'keywords': s.get('keywords', []), 'built_in': bool(s.get('built_in')),
        'mode': s.get('mode', 'light'), 'colors': s.get('colors', {}),
        'confidence': s.get('confidence', ''), 'system_json': s.get('system_json', ''),
        'card': s.get('card') or '', 'originals': s.get('originals', []) or [],
    })
print('风格:', len(styles))

# ---------- 红线 ----------
sec3 = re.search(r'## 3\..*?\n(.*?)\n## 4\.', skill_md, re.S)
red = []
if sec3:
    for ln in sec3.group(1).splitlines():
        m = re.match(r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*$', ln)
        if m:
            red.append((int(m.group(1)), m.group(2).strip()))
red.sort()
print('红线:', len(red))

# ---------- 工作流 ----------
sec6 = re.search(r'## 6\..*?\n(.*?)\n## 7\.', skill_md, re.S)
steps = []
if sec6:
    for ln in sec6.group(1).splitlines():
        m = re.match(r'\s*(\d+)\.\s*(.+?)\s*$', ln)
        if m:
            steps.append((int(m.group(1)), m.group(2).strip()))
steps.sort()
print('工作流步骤:', len(steps))

# ---------- 命令（SKILL.md + scripts/ 目录补全） ----------
cmds = []
for ln in skill_md.splitlines():
    t = ln.strip()
    if t.startswith(('python scripts/', 'node scripts/')):
        cmds.append(t)

# 扫描 scripts/ 目录，补 SKILL.md 没列出的脚本
SEEN = set()
for c in cmds:
    m = re.search(r'scripts/([\w.]+\.(?:py|js))', c)
    if m:
        SEEN.add(m.group(1))

sd = os.path.join(SKILL, 'scripts')
EXTRA_USAGE = {
    'build_layout_library.py': 'python scripts/build_layout_library.py            # 生成常见布局特征库',
    'check_layout_similarity.py': 'python scripts/check_layout_similarity.py --plan output/plan.json --candidate A --strict',
    'find_asset.py': 'python scripts/find_asset.py <关键词…> --list',
}
added = []
if os.path.isdir(sd):
    for f in sorted(os.listdir(sd)):
        if not f.endswith(('.py', '.js')) or f in SEEN:
            continue
        if f in EXTRA_USAGE:
            usage = EXTRA_USAGE[f]
        elif f.endswith('.py'):
            usage = 'python scripts/' + f
        else:
            usage = 'node scripts/' + f
        added.append(usage)
cmds.extend(added)
print('命令:', len(cmds), '（从 scripts/ 补全 %d 条）' % len(added))
for a in added:
    print('   +', a)

# ---------- 用户既定偏好（从技能包 config 读，不硬编码） ----------
prefs = {}
cfg_path = os.path.join(SKILL, 'assets', 'config.json')
if os.path.isfile(cfg_path):
    cfg = json.load(io.open(cfg_path, encoding='utf-8'))
    ct = cfg.get('cover_title') or {}
    cb = cfg.get('cover_mask') or {}
    prefs = {
        'cover_title_mode': ct.get('mode', ''),
        'cover_prompt': ct.get('prompt_template', ''),
        'cover_colors': ct.get('color_by_background', {}),
        'cover_mask_mode': cb.get('mode', ''),
        'image_tool': (cfg.get('image') or {}).get('tool', ''),
    }
print('偏好:', {k: (str(v)[:40] if not isinstance(v, dict) else list(v.keys())) for k, v in prefs.items()})

# ---------- 视觉母题（9.0.2 新增规范，抽示例进插件） ----------
motifs = []
mf = os.path.join(SKILL, 'references', 'visual-motifs.md')
if os.path.isfile(mf):
    mt = io.open(mf, encoding='utf-8').read()
    # 取 §二 示例代码块里的 "name": "xxx"
    for nm in re.findall(r'"name"\s*:\s*"([^"]{1,12})"', mt):
        if nm not in motifs:
            motifs.append(nm)
    # 兜底：从正文括号里的举例抽
    if not motifs:
        m2 = re.search(r'（例：([^）]+)）', mt)
        if m2:
            motifs = [x.strip() for x in re.split(r'[、/]', m2.group(1)) if x.strip()][:5]
print('视觉母题:', motifs)

# ---------- 动效配方库（9.0.3 新增，给侧边栏展示用） ----------
# 数据直接从技能包的 10 份 spec.json 现读，不手写，新增效果会自动进侧栏
effects = []
# 分级直接调用技能包的 list_effects.py，保持唯一数据源（不在插件里另写一套）
_TIER = {}
try:
    import importlib.util
    _sp = os.path.join(SKILL, 'scripts', 'list_effects.py')
    _spec = importlib.util.spec_from_file_location('_le', _sp)
    _le = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_le)
    _TIER = {k: (v[0], v[1]) for k, v in _le.TIER.items()}
    _TLAB = _le.TIER_LABEL
except Exception as _e:
    print('[warn] 读分级失败，星级留空:', _e)
    _TLAB = {}
_MOTION = {}
try:
    _mrf = os.path.join(SKILL, 'assets', 'motion-recipes.json')
    _MOTION = {r['id']: r for r in json.load(io.open(_mrf, encoding='utf-8'))['recipes']}
except Exception as _e:
    print('[warn] 读 motion-recipes.json 失败:', _e)
eff_root = os.path.join(SKILL, 'subskills', 'ppt-effects', 'effects')
for sd in sorted(os.listdir(eff_root)) if os.path.isdir(eff_root) else []:
    sf = os.path.join(eff_root, sd, 'spec.json')
    if not os.path.isfile(sf):
        continue
    d = json.load(io.open(sf, encoding='utf-8'))
    m = d.get('materials') or {}
    variants = m.get('variants') or {}
    req = m.get('requirement') or ''
    if not req and variants:
        req = '；'.join('%s：%s' % (k, (v.get('requirement') or v.get('note') or '').strip())
                      for k, v in variants.items() if isinstance(v, dict))
    mn, mx = m.get('min'), m.get('max')
    if mn is None and variants:
        lo = [v.get('min') for v in variants.values() if isinstance(v, dict) and v.get('min') is not None]
        hi = [v.get('max') for v in variants.values() if isinstance(v, dict) and v.get('max') is not None]
        if lo: mn = min(lo)
        if hi: mx = max(hi)
    pics = '0（纯版式）' if mn == 0 else (str(mn) if mx is None or mn == mx else '%s–%s' % (mn, mx))
    pages = ''
    mm = re.search(r'(\d+)\s*页', d.get('summary') or '')
    if mm: pages = mm.group(1) + ' 页'
    effects.append({
        'id': d.get('id', ''), 'name': d.get('name', ''),
        'tier': _TIER.get(d.get('id',''), (0,''))[0],
        'tier_label': _TLAB.get(_TIER.get(d.get('id',''), (0,''))[0], '—'),
        'tier_reason': _TIER.get(d.get('id',''), (0,''))[1],
        'overlayable': _MOTION.get(d.get('id',''), {}).get('overlayable'),
        'route_key': ('template-clone' if _MOTION.get(d.get('id',''), {}).get('route') == 'template-clone'
                      else 'overlay'),
        'motion_layer': _MOTION.get(d.get('id',''), {}).get('layer'),
        'min_slides': (_MOTION.get(d.get('id',''), {}).get('continuation') or {}).get('min_slides'),
        'summary': (d.get('summary') or '').replace('\n', ' '),
        'pages': pages, 'pics': pics,
        'requirement': (req or '见 spec.json').replace('\n', ' '),
        'preview': d.get('preview', ''),
        'variants': list(variants.keys()),
        'dir': 'subskills/ppt-effects/effects/' + sd,
    })
print('动效配方:', len(effects), '条')

# ---- v9.0.6 模板填充模式：从技能包的「用户模板索引」抽取（只登记，不复制原文件）
# 与官方 references/user-templates.md 口径一致：先读索引、按需只读 1 份，不得整体读取。
templates = []
try:
    _tpl_idx = os.path.join(SKILL, 'assets', 'user-templates', 'index.json')
    _td = json.load(io.open(_tpl_idx, encoding='utf-8'))
    for _t in _td.get('templates', []):
        _p = _t.get('path') or ''
        templates.append({
            'id': _t.get('id', ''),
            'name': _t.get('name', ''),
            'style_tags': _t.get('style_tags') or [],
            'keywords': _t.get('keywords') or [],
            'pages': _t.get('pages'),
            'aspect': _t.get('aspect', ''),
            'size_mb': _t.get('size_mb'),
            'theme_fonts': _t.get('theme_fonts') or [],
            'theme_colors': _t.get('theme_colors') or [],
            'format': _t.get('format', 'pptx'),
            'path': _p,
            'available': bool(_p) and os.path.isfile(_p),
        })
except Exception as _e:
    print('[warn] 读用户模板索引失败:', _e)
print('用户模板:', len(templates), '份（本机可用 %d）' % sum(1 for x in templates if x['available']))

out = {
    'version': VERSION,
    'note': idx.get('_note', ''),
    'style_count': len(styles),
    'styles': styles,
    'red_lines': [t for _, t in red],
    'workflow': [t for _, t in steps],
    'commands': cmds,
    'preferences': prefs,
    'motifs': motifs,
    'effects': effects,
    'templates': templates,
    'template_mode_default': 'free',
}
dst = os.path.join(PLUG, 'data', 'styles.json')
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(out, io.open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('写出:', dst, os.path.getsize(dst), 'bytes')
