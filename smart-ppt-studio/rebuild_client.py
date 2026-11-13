# -*- coding: utf-8 -*-
"""重建 smart-ppt-studio 的 client.js（v2：正则替换，根治固定字符串失效）。

v1 的问题：用 src.replace("Array.from({ length: 19 }...") 这类**固定字符串**做替换。
一旦某次重建把值改成别的新值，下次就再也匹配不上，但脚本仍打印"已重建"——
静默失败，导致红线/命令条数长期与数据脱节（实测 28 条只显示 21）。

v2 改法：
  · 用正则匹配 `length: N` 中的数字，替换成实际条数（与当前值无关）
  · 每个替换都校验命中次数，0 次直接报错退出，不静默
  · 新增 9.0.2 新能力（布局库 / 相似度 / 视觉母题）进 commands 与文案
  · 生成指令注入用户既定偏好（封面 AI 书法 / 亮底禁金 / 渐变蒙版）
"""
import json, io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:/文档/deepseek-harness/default-workspace/smart-ppt-studio'
data = json.load(io.open(os.path.join(P, 'data', 'styles.json'), encoding='utf-8'))
VER = data['version']
NR, NS, NC = len(data['red_lines']), len(data['workflow']), len(data['commands'])
NE = len(data.get('effects') or [])
NT = len(data.get('templates') or [])
NTA = sum(1 for x in (data.get('templates') or []) if x.get('available'))
print(f'版本 {VER} | 红线 {NR} | 工作流 {NS} | 命令 {NC} | 风格 {data["style_count"]} | 动效 {NE} | 模板 {NT}(可用 {NTA})')

src = io.open(os.path.join(P, 'client.js'), encoding='utf-8').read()


def sub_count(pattern, repl, label, expect=1):
    """正则替换并校验命中次数，0 命中视为失败。

    字符串替换统一包成 lambda：避免 Windows 路径里的反斜杠被 re 当成替换串
    转义吃掉（v9.0.6 模板索引含 D:\\下载\\...，曾导致 client.js 出现八进制转义）。
    """
    global src
    fn = repl if callable(repl) else (lambda m, s=repl: s)
    src, n = re.subn(pattern, fn, src, count=expect, flags=re.S)
    if n != expect:
        sys.exit('!! 替换失败 [%s]: 期望 %d 处，实际 %d 处' % (label, expect, n))
    print('  [ok] %-22s %d 处' % (label, n))


# ---------- 1) STYLE_DATA 字面量 ----------
blob = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
sub_count(r'const STYLE_DATA = \{.*?\};\n', 'const STYLE_DATA = ' + blob + ';\n', 'STYLE_DATA')

# ---------- 2) ZH / EN 字典 ----------
def build(lang):
    zh = lang == 'zh'
    d = {}
    d['meta.title'] = 'PPT 设计台' if zh else 'PPT Studio'
    d['meta.description'] = (
        f'把 smart-ppt-designer {VER} 技能包带进左侧栏：检索 {data["style_count"]} 套视觉系统、'
        f'速查 {NR} 条红线与 {NS} 步工作流；可选风格自由生成，或从 {NT} 份模板里挑一份照着做。' if zh else
        f'Brings smart-ppt-designer {VER} into the left sidebar: browse {data["style_count"]} visual systems, '
        f'check {NR} red lines and the {NS}-step workflow; pick a style, or follow one of {NT} user templates.')
    d['nav'] = d['title'] = 'PPT 设计台' if zh else 'PPT Studio'
    d['subtitle'] = (f'smart-ppt-designer {VER} · 风格库与工作台' if zh
                     else f'smart-ppt-designer {VER} · Style library and workbench')
    if zh:
        d.update({
            'tab.styles': '风格库', 'tab.rules': '红线与规范', 'tab.workflow': '工作流',
            'tab.commands': '脚本命令', 'tab.effects': '动效配方', 'tab.templates': '模板填充',
            'templates.count': f'共 {NT} 份用户模板 · 本机可用 {NTA} 份 · 默认自由生成',
            'templates.hint': '已有满意的版式？选一份「照着做」——只替换文字/数据/图片，母版与版式不动。'
                             '生成前会先问封面字体「保持原样 / 升级书法烫金」；红线 28 封面 AI 书法强制仍生效。',
            'templates.mode.free': '自由生成（选风格）', 'templates.mode.fill': '模板填充（照模板做）',
            'templates.modeHint': '两种模式生成前必问；默认是自由生成。',
            'templates.search': '搜索模板名称 / 风格标签 / 关键词',
            'templates.available': '本机可用', 'templates.missing': '原文件不在本机',
            'templates.pages': '页数', 'templates.aspect': '画幅', 'templates.tags': '风格标签',
            'templates.fonts': '主题字体', 'templates.colors': '主题色',
            'templates.pick': '用这份模板做 PPT', 'templates.none': '不用模板，自由生成', 'templates.preview': '生成指令预览',
            'templates.selectHint': '点击任一份模板查看页数/风格/配色，再一键生成指令',
            'templates.empty': '没有匹配的模板，试试更短的关键词。',
            'templates.path': '原文件',
            'templates.coverAsk': '封面字体：保持原样 / 升级书法烫金（生成时会问）',
            'effects.count': f'共 {NE} 条动效配方 · 默认关闭，做 PPT 时任选一条',
            'effects.hint': f'任选一条（或「不用，走常规构建」）。v9.0.7 起 {NE} 条全部可融入：默认 overlay 叠加——主链正常出稿后叠动画内核，不换链/不加页/页数无关；★ 只是参考不是默认。',
            'effects.pick': '用这条做 PPT', 'effects.none': '不用，走常规构建',
            'effects.pics': '需要图片', 'effects.pages': '页数', 'effects.req': '素材硬门槛',
            'effects.variant': '分档',
            'effects.tier': '高级感',
            'effects.goal': '目标：增加高级感，优先复杂、一下到位的动效；但选哪条由你定，★ 只是参考不是默认。',
            'effects.integration': '接入方式',
            'search.placeholder': '按名称或关键词检索风格，例如：国潮、医疗、乡村振兴、科技',
            'filter.all': '全部', 'filter.light': '亮场', 'filter.dark': '暗场',
            'filter.builtin': '内置', 'filter.extracted': '参考稿提取',
            'styles.count': f'共 {data["style_count"]} 套视觉系统 · 不设默认风格',
            'select.hint': '点击风格卡片看配色；若已有满意的版式，去「模板填充」tab 挑一份照着做',
            'style.system': '视觉系统', 'style.mode': '明暗模式', 'style.source': '来源',
            'style.confidence': '置信度', 'style.keywords': '内容关键词',
            'style.palette': '配色', 'style.rationale': '风格理由（style_rationale）',
            'style.card': '风格卡片', 'style.originals': '参考原稿',
            'style.noDefault': f'红线 {NR}：风格不设默认。必须写明 style_rationale，判断不出时先问用户；脚本不会回落默认风格。',
            'action.copy': '复制生成指令', 'action.copied': '已复制，回到会话粘贴发送即可',
            'action.copyFailed': '复制失败，请手动选中下方文本',
            'prompt.title': '生成指令预览',
            'prompt.hint': '以下指令会带上你选中的风格与理由，交给 smart-ppt-designer 技能执行。',
            'rules.title': '硬边界（红线，违反即返工）',
            'workflow.title': f'{NS} 步工作流（规格 v{VER}）',
            'commands.title': '标准脚本命令',
            'commands.hint': '在技能包根目录执行；生图一级 image_generate，失败退免费图库，再退纯色背景。',
            'commands.motifHint': '视觉母题（选 3–5 种整份复用，1 主 2–4 次；详见 references/visual-motifs.md）',
            'about.title': '关于这个插件',
            'about.body': f'数据源为已安装的 smart-ppt-designer {VER}（assets/style-index.json 与 SKILL.md 实时抽取）。'
                          '本插件只做检索、速查与指令拼装，不修改技能包文件，也不替代生成流程。',
            'styles.empty': '没有匹配的风格，试试更短的关键词。',
            'style.filesUnit': '份',
            'style.darkWarn': '你此前偏好明亮、不要深色底；暗场风格请先确认。',
        })
    else:
        d.update({
            'tab.styles': 'Styles', 'tab.rules': 'Red lines', 'tab.workflow': 'Workflow',
            'tab.commands': 'Scripts', 'tab.effects': 'Motion recipes', 'tab.templates': 'Template fill',
            'templates.count': f'{NT} user templates · {NTA} available locally · free generation by default',
            'templates.hint': 'Already have a layout you like? Pick one and we will only replace text/data/images, keeping the master and layout.',
            'templates.mode.free': 'Free generation (pick a style)', 'templates.mode.fill': 'Template fill (follow a template)',
            'templates.modeHint': 'Ask before generating; free generation is the default.',
            'templates.search': 'Search template name / style tag / keyword',
            'templates.available': 'available', 'templates.missing': 'source missing',
            'templates.pages': 'Pages', 'templates.aspect': 'Aspect', 'templates.tags': 'Style tags',
            'templates.fonts': 'Theme fonts', 'templates.colors': 'Theme colors',
            'templates.pick': 'Build with this template', 'templates.none': 'No template — free generation', 'templates.preview': 'Prompt preview',
            'templates.selectHint': 'Select a template to see pages/style/palette, then compose the prompt',
            'templates.empty': 'No matching template; try a shorter keyword.',
            'templates.path': 'Source',
            'templates.coverAsk': 'Cover font: keep original / upgrade to AI calligraphy (asked at build time)',
            'effects.count': f'{NE} motion recipes · off by default, pick one when building a deck',
            'effects.hint': f'Pick one (or \'None, standard build\'). Since v9.0.7 all {NE} fit the normal build: overlay mode adds motion after the main chain, no pipeline switch, no extra pages, page count irrelevant.',
            'effects.pick': 'Build with this', 'effects.none': 'None — standard build',
            'effects.pics': 'Images', 'effects.pages': 'Pages', 'effects.req': 'Material requirements',
            'effects.variant': 'Variants',
            'effects.tier': 'Premium',
            'effects.goal': 'Goal: a more premium deck — complex, single-morph effects first. You choose; ★ is a hint, not a default.',
            'effects.integration': 'Integration',
            'search.placeholder': 'Search styles by name or keyword, e.g. heritage, medical, tech',
            'filter.all': 'All', 'filter.light': 'Light', 'filter.dark': 'Dark',
            'filter.builtin': 'Built-in', 'filter.extracted': 'From references',
            'styles.count': f'{data["style_count"]} visual systems · no default style',
            'select.hint': 'Select a style card, or go to the Template fill tab to follow an existing deck',
            'style.system': 'Visual system', 'style.mode': 'Mode', 'style.source': 'Source',
            'style.confidence': 'Confidence', 'style.keywords': 'Keywords',
            'style.palette': 'Palette', 'style.rationale': 'Style rationale',
            'style.card': 'Style card', 'style.originals': 'Source decks',
            'style.noDefault': f'Red line {NR}: no default style. A style_rationale is mandatory; when undecided, ask the user.',
            'action.copy': 'Copy generation prompt', 'action.copied': 'Copied — paste it into the conversation',
            'action.copyFailed': 'Copy failed; select the text below manually',
            'prompt.title': 'Prompt preview',
            'prompt.hint': 'This prompt carries your chosen style and rationale to the smart-ppt-designer skill.',
            'rules.title': 'Hard boundaries (red lines)',
            'workflow.title': f'{NS}-step workflow (spec v{VER})',
            'commands.title': 'Standard scripts',
            'commands.hint': 'Run from the skill package root; images go to image_generate, then free photo libraries, then a solid background.',
            'commands.motifHint': 'Visual motifs (pick 3–5 per deck: 1 primary + 2–4 secondary; see references/visual-motifs.md)',
            'about.title': 'About this plugin',
            'about.body': f'Data is extracted live from the installed smart-ppt-designer {VER} '
                          '(assets/style-index.json and SKILL.md). This plugin only browses, checks and composes prompts.',
            'styles.empty': 'No matching style; try a shorter keyword.',
            'style.filesUnit': 'files',
            'style.darkWarn': 'You previously preferred bright, non-dark backgrounds; confirm before using a dark system.',
        })
    for i, txt in enumerate(data['red_lines'], 1):
        d[f'rule.{i}'] = txt
    for i, txt in enumerate(data['workflow'], 1):
        d[f'step.{i}'] = txt
    for i, txt in enumerate(data['commands'], 1):
        d[f'cmd.{i}'] = txt
    return d


zh, en = build('zh'), build('en')
for name, obj in (('ZH', zh), ('EN', en)):
    sub_count(r'const ' + name + r' = \{.*?\};\n',
              'const ' + name + ' = ' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ';\n',
              name + ' 字典')

# ---------- 3) 条数：正则替换 N，不再依赖具体旧值 ----------
# 命令页
sub_count(r"(function CommandsView\(props\) \{.*?Array\.from\(\{\s*length:\s*)\d+(\s*\})",
          lambda m: m.group(1) + str(NC) + m.group(2), '命令条数')
# 红线页 / 工作流页（Panel 里的两处）
sub_count(r"(tab === 'rules'.*?Array\.from\(\{\s*length:\s*)\d+(\s*\})",
          lambda m: m.group(1) + str(NR) + m.group(2), '红线条数')
sub_count(r"(tab === 'workflow'.*?Array\.from\(\{\s*length:\s*)\d+(\s*\})",
          lambda m: m.group(1) + str(NS) + m.group(2), '工作流条数')

# ---------- 4) 复制失败要有回显 ----------
if 'setCopyFailed' not in src:
    # copy() 里 setCopied(false) 改为同时设置失败提示
    src = src.replace("} else { setCopied(false); }", "} else { setCopied(false); setCopyFailed(true); }")
    src = src.replace("} catch (e) { setCopied(false); }", "} catch (e) { setCopied(false); setCopyFailed(true); }")
    # 加 state
    src = src.replace("const [copied, setCopied] = React.useState(false);",
                      "const [copied, setCopied] = React.useState(false);\n      const [copyFailed, setCopyFailed] = React.useState(false);")
    # 成功时清失败
    src = src.replace("setCopied(true);", "setCopied(true); setCopyFailed(false);")
    # 手动改动 rationale/prompt 时清失败
    src = src.replace("setRationale(e.target.value); setCopied(false);",
                      "setRationale(e.target.value); setCopied(false); setCopyFailed(false);")
    # 渲染失败提示（放在 copied 状态后面）
    src = src.replace(
        "copied ? h('span', { key: 'ok', className: 'spps-btn-status' }, t('action.copied')) : null,",
        "copied ? h('span', { key: 'ok', className: 'spps-btn-status' }, t('action.copied')) : null,\n"
        "            copyFailed ? h('span', { key: 'fail', className: 'spps-warn' }, t('action.copyFailed')) : null,")
    print('  [ok] 复制失败回显')

io.open(os.path.join(P, 'client.js'), 'w', encoding='utf-8').write(src)
print('\nclient.js 已重建（v2 正则版）')
