#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材体检：检查技能包依赖的素材是否就位，缺失时打印可执行的补充指引。

用途（规格 v9.9）：把技能包拷给别人后，**不会缺功能，但可能缺素材**——
用户模板原文件（95 份 / 7.3 GB）、随附字体（84 个）、精简包排除掉的参考原文件与样本 pptx/pdf。
本脚本把这些缺失一次性列清楚，并给出「放到哪个目录 / 跑哪条命令」的补充方式。

设计约束：
- **只提醒，不阻断**：默认退出码 0；加 `--strict` 才在有关键缺失时返回 1。
- 不修改任何文件，只读。

用法：
    python scripts/check_assets.py                 # 体检并打印结果与补充指引
    python scripts/check_assets.py --strict        # 有关键缺失时退出码 1（CI/脚本可用）
    python scripts/check_assets.py --json out.json # 结果另存 JSON
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count_glob(pattern: str) -> int:
    return len(glob.glob(str(ROOT / pattern), recursive=True))


def load_json(rel: str):
    try:
        return json.load(io.open(ROOT / rel, encoding='utf-8'))
    except Exception:
        return None


def check_user_templates() -> dict:
    idx = load_json('assets/user-templates/index.json')
    fx = load_json('assets/user-templates/fonts-index.json')
    t_total = t_ok = 0
    t_sources = []
    if idx:
        t_total = int(idx.get('count') or len(idx.get('templates') or []))
        for t in idx.get('templates') or []:
            if os.path.exists(str(t.get('path') or '')):
                t_ok += 1
            else:
                src = t.get('source_dir')
                if src and src not in t_sources:
                    t_sources.append(src)
    f_total = f_ok = 0
    if fx:
        f_total = int(fx.get('count') or len(fx.get('fonts') or []))
        f_ok = sum(1 for f in fx.get('fonts') or [] if os.path.exists(str(f.get('path') or '')))
    return {'index_present': idx is not None, 'fonts_index_present': fx is not None,
            'templates_total': t_total, 'templates_present': t_ok,
            'fonts_total': f_total, 'fonts_present': f_ok,
            'missing_source_dirs': t_sources}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true', help='有关键缺失时返回退出码 1')
    ap.add_argument('--json', dest='json_out', default=None, help='结果另存 JSON')
    a = ap.parse_args()

    ut = check_user_templates()
    refs = count_glob('assets/templates/references/**/*')
    samples = count_glob('assets/sample-ppts/*.pptx') + count_glob('assets/sample-ppts/*.pdf')
    style_idx = (ROOT / 'assets/style-index.json').exists()
    skills = (ROOT / 'SKILL.md').exists()

    results, gaps = [], []

    def add(level, item, detail, fix=''):
        results.append({'level': level, 'item': item, 'detail': detail, 'fix': fix})
        if level in ('missing', 'warn'):
            gaps.append(results[-1])

    # 1) 包本体的关键文件（缺失即安装不完整）
    add('ok' if skills and style_idx else 'missing', '包本体',
        'SKILL.md %s｜style-index.json %s' % ('在' if skills else '缺', '在' if style_idx else '缺'),
        '重新解压技能包压缩包；确认解压到了 smart-ppt-designer/ 根目录')

    # 2) 用户模板索引（轻量，应随包分发）
    if not ut['index_present']:
        add('missing', '用户模板索引', 'assets/user-templates/index.json 不存在',
            '从完整包中取回；或跑 python scripts/index_user_templates.py 重建')
    elif ut['templates_total'] and ut['templates_present'] < ut['templates_total']:
        miss = ut['templates_total'] - ut['templates_present']
        add('warn', '用户模板原文件',
            '索引 %d 份，本机找到 %d 份，缺 %d 份' % (ut['templates_total'], ut['templates_present'], miss),
            '把模板放回原目录（%s），或把模板放到新目录后跑：'
            'python scripts/index_user_templates.py --source "<你的模板目录>"'
            % ('／'.join(ut['missing_source_dirs']) or '原素材目录'))
    else:
        add('ok', '用户模板原文件', '索引 %d 份，本机全部就位' % ut['templates_total'])

    # 3) 随附字体（只登记不安装）
    if ut['fonts_total'] and ut['fonts_present'] < ut['fonts_total']:
        add('warn', '随附字体',
            '清单 %d 个，本机找到 %d 个（字体只登记不安装，缺了不影响功能）'
            % (ut['fonts_total'], ut['fonts_present']),
            '如需使用清单中的字体，自行确认授权后安装；不需要可忽略')
    elif ut['fonts_total']:
        add('ok', '随附字体', '清单 %d 个，本机全部在' % ut['fonts_total'])

    # 4) 参考原文件与样本（精简包会排除，属预期缺失）
    if refs == 0:
        add('warn', '参考稿原文件', 'assets/templates/references/ 为空',
            '用**完整包**覆盖安装；或只把参考原文件放进 assets/templates/references/')
    else:
        add('ok', '参考稿原文件', 'asset/templates/references 下 %d 个文件' % refs)
    if samples == 0:
        add('warn', '样本 PPT', 'assets/sample-ppts/ 下没有 pptx/pdf',
            '用**完整包**覆盖安装；精简包有意排除样本原文件，只影响「参考样本」类任务')
    else:
        add('ok', '样本 PPT', 'assets/sample-ppts/ 下 %d 个 pptx/pdf' % samples)


    # 6) v9.0.6 动画素材库引擎（43 种动画要生效必须有这个 fork）

    # 7) v9.0.6-r4 工作区素材编目（432 份，封面人物替换法的检索来源）
    cat = ROOT / 'assets/ppt-assets-catalog.json'
    if not cat.exists():
        add('missing', '素材分类目录', 'assets/ppt-assets-catalog.json 不存在',
            '重跑素材编目脚本；缺了 find_asset.py --kind ppt_asset 会检索不到任何素材')
    else:
        try:
            n = len(json.loads(cat.read_text(encoding='utf-8')).get('items', []))
            add('ok', '素材分类目录', '已编目 %d 份（工作区 ppt-assets）' % n)
        except Exception:
            add('missing', '素材分类目录', '文件存在但 JSON 解析失败',
                '重跑素材编目脚本修复')

    # 8) v9.0.6-r4 封面人物替换法规范
    persona = ROOT / 'references/cover-persona-swap.md'
    add('ok' if persona.exists() else 'missing', '封面人物替换法',
        'references/cover-persona-swap.md %s' % ('在' if persona.exists() else '缺'),
        '从补丁包取回该规范；模板封面人物不对时按五步法处理')

    # 9) v9.0.6-r5 文档一致性：SKILL 命令块条数 == 侧边栏 styles.json 命令条数
    #    只读检查，不修改任何文件；不一致只提醒，避免再次出现"侧栏 29 / SKILL 27"漂移
    try:
        sk = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        n_skill = len(re.findall(r'^(?:python|node) scripts/', sk, re.M))
        # 侧边栏 styles.json 不在技能包内（可能跨盘），按候选路径找；找不到就跳过
        plug = None
        cands = [
            ROOT.parent.parent / 'default-workspace' / 'smart-ppt-studio' / 'data' / 'styles.json',
            Path(r'D:\文档\deepseek-harness\default-workspace\smart-ppt-studio\data\styles.json'),
        ]
        for c in cands:
            if c.exists():
                plug = c; break
        if plug is None:
            add('ok', '命令数一致性', '未找到侧边栏数据，跳过（不影响包内自检）')
        else:
            n_plug = len(json.loads(plug.read_text(encoding='utf-8')).get('commands', []))
            if n_skill == n_plug:
                add('ok', '命令数一致性', 'SKILL %d 条 == 侧栏 %d 条' % (n_skill, n_plug))
            else:
                add('warn', '命令数一致性',
                    'SKILL %d 条 ≠ 侧栏 %d 条（差 %d）' % (n_skill, n_plug, n_plug - n_skill),
                    '在 smart-ppt-studio 跑 sync_from_skill.py + rebuild_client.py 重新同步')
    except Exception as e:
        add('warn', '命令数一致性', '检查跳过：%s' % str(e)[:60], '手动核对 SKILL.md 命令块')

    # ---- 输出 ----
    print('=' * 68)
    print('smart-ppt-designer 素材体检')
    print('=' * 68)
    icon = {'ok': '[OK]  ', 'warn': '[提醒]', 'missing': '[缺失]'}
    for r in results:
        print('%s %-12s %s' % (icon.get(r['level'], '     '), r['item'], r['detail']))
    if gaps:
        print('-' * 68)
        print('需要补充的项（只提醒，不阻断）：')
        for r in gaps:
            print('  · %s：%s' % (r['item'], r['fix']))
        print('-' * 68)
        print('补充完可再跑一次本脚本复核；完整说明见 INSTALL.md')
    else:
        print('-' * 68)
        print('素材齐备，可直接使用。')

    if a.json_out:
        json.dump({'results': results, 'gaps': len(gaps), 'user_templates': ut},
                  io.open(a.json_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('结果已写入 %s' % a.json_out)

    if a.strict and any(r['level'] == 'missing' for r in results):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())