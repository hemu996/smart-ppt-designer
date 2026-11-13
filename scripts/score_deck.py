#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成后自我评分与最弱页定位（规格 v8.7：8 个分项，含「国赛对齐度」）

评分是**执行门**，不是质量判决：低于 `config.scoring.pass_score`（默认 75）时应重写最弱
`rewrite_weakest_n`（默认 2）页，最多 `max_rewrite_rounds`（默认 2）轮。

用法：
    python scripts/score_deck.py --plan output/plan.json --candidate A --deck output/deck.pptx
    python scripts/score_deck.py --plan output/plan.json --candidate A --deck output/deck.pptx --json output/score.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INNER = ["concept", "content", "data_chart"]


def run_detect(deck: Path) -> dict:
    tmp = Path(tempfile.mkdtemp()) / "detect.json"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "detect_layout.py"), str(deck),
                    "--json", str(tmp)], capture_output=True, text=True)
    if not tmp.exists():
        return {}
    return json.loads(tmp.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--candidate", default="A")
    ap.add_argument("--deck", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()

    cfg = json.loads((ROOT / "assets" / "config.json").read_text(encoding="utf-8"))
    sc = cfg.get("scoring") or {}
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    cand = next((c for c in plan.get("candidates", []) if c.get("candidate_id") == a.candidate), None)
    if cand is None:
        raise SystemExit(f"页面计划里找不到候选 {a.candidate}")
    slides = cand.get("slides") or []
    db = plan.get("design_brief") or {}
    d = run_detect(Path(a.deck))
    issues = [i for i in (d.get("issues") or []) if i.get("level") in ("error", "warning")]
    errs = [i for i in issues if i.get("level") == "error"]
    warns = [i for i in issues if i.get("level") == "warning"]
    native = d.get("native") or {}
    n = len(slides) or 1

    def inner(s):
        return s.get("slide_type") in INNER

    detail, total = {}, 0.0

    # 1) 结构完整 15
    ok = sum(bool(x) for x in (db.get("visual_system"), db.get("style_rationale"),
                               db.get("density_mode"), db.get("sections"), db.get("navigation_mode")))
    detail["结构完整(15)"] = round(15 * ok / 5, 1)
    total += detail["结构完整(15)"]

    # 2) 原生深度 15：备注页数 + 至少 1 个原生图表/表格（有数据页时）
    notes_ok = 1 if (native.get("notes_nonempty") or 0) >= n else (native.get("notes_nonempty") or 0) / n
    has_obj = 1 if ((native.get("charts") or 0) + (native.get("tables") or 0)) > 0 else 0
    detail["原生深度(15)"] = round(15 * (0.6 * notes_ok + 0.4 * has_obj), 1)
    total += detail["原生深度(15)"]

    # 3) 排版质量 15：error 每次 -5、warning 每次 -1.5，下限 0
    detail["排版质量(15)"] = round(max(0, 15 - 5 * len(errs) - 1.5 * len(warns)), 1)
    total += detail["排版质量(15)"]

    # 4) 视觉层级 10：内页有 title 且有唯一最大字号
    good = 0
    for s in slides:
        if not inner(s):
            continue
        els = [e for e in (s.get("elements") or []) if isinstance(e, dict)]
        sizes = [(e.get("font_pt") or 0) for e in els if e.get("type") == "text"]
        titles = [e for e in els if e.get("role") == "title"]
        mx = max(sizes) if sizes else 0
        if titles and mx and sum(1 for x in sizes if x == mx) == 1:
            good += 1
    inner_n = sum(1 for s in slides if inner(s)) or 1
    detail["视觉层级(10)"] = round(10 * good / inner_n, 1)
    total += detail["视觉层级(10)"]

    # 5) 叙事与正文 10：claim 齐备 + 行动标题合规 + 正文无 AI 味
    title_bl = {str(x) for x in ((cfg.get("narrative") or {}).get("title_blacklist") or [])}
    min_chars = int((cfg.get("narrative") or {}).get("action_title_min_chars", 8))
    cliches = [str(x) for x in ((cfg.get("narrative") or {}).get("cliche_title_patterns") or []) if str(x)]
    bsc = cfg.get("body_style") or {}
    ai_flavor = [str(x) for x in (bsc.get("ai_flavor_patterns") or []) if str(x)]
    escalation = [str(x) for x in (bsc.get("escalation_patterns") or []) if str(x)]
    esc_warn = int(bsc.get("escalation_per_page_warn", 2))
    intent_all = plan.get("brief_intent") or {}
    ctx_all = " ".join([str(intent_all.get("deck_title") or ""), str(intent_all.get("communication_goal") or ""),
                        str(intent_all.get("audience") or ""), " ".join(str(x) for x in (db.get("sections") or []))])
    esc_exempt = bool(bsc.get("escalation_exempt_in_context", True)) and \
        any(str(k) for k in (bsc.get("context_exempt_keywords") or []) if str(k) and str(k) in ctx_all)
    ok_n = 0
    for s in slides:
        if not inner(s):
            continue
        t = next((str(e.get("text") or "").strip() for e in (s.get("elements") or [])
                  if isinstance(e, dict) and e.get("role") == "title"), "")
        body = " ".join(str(e.get("text") or "") for e in (s.get("elements") or [])
                        if isinstance(e, dict) and e.get("type") == "text")
        esc_hit = len([w for w in escalation if w in body])
        ai_hit = any(w in body for w in ai_flavor) or (esc_hit >= esc_warn and not esc_exempt)
        if (str(s.get("claim") or "").strip() and t and t not in title_bl and len(t) >= min_chars
                and not any(c in t for c in cliches) and not ai_hit):
            ok_n += 1
    detail["叙事与正文(10)"] = round(10 * ok_n / inner_n, 1)
    total += detail["叙事与正文(10)"]

    # 6) 密度模式 10
    dm = db.get("density_mode")
    floor = int(((cfg.get("density_modes") or {}).get("vivid") or {}).get("min_elements_per_content_page", 6))
    ceil = int(((cfg.get("density_modes") or {}).get("concise") or {}).get("max_elements_per_content_page", 5))
    hit = 0
    for s in slides:
        if not inner(s):
            continue
        k = len([e for e in (s.get("elements") or []) if isinstance(e, dict)])
        if dm == "vivid" and k >= floor:
            hit += 1
        elif dm == "concise" and k <= ceil:
            hit += 1
    detail["密度模式(10)"] = round(10 * hit / inner_n, 1) if dm else 0.0
    total += detail["密度模式(10)"]

    # 7) 参考依据 5
    detail["参考依据(5)"] = 5.0 if len(str(db.get("style_rationale") or "").strip()) >= 12 else 0.0
    total += detail["参考依据(5)"]

    # 8) 国赛对齐度 20：按 config.gsl_alignment.targets 量产物，逐项输出差距
    gsl_t = (cfg.get("gsl_alignment") or {}).get("targets") or {}
    gsl_detail, deck_stats = {}, {}
    try:
        import importlib
        _ar = importlib.import_module("analyze_reference")
        _res = _ar.analyse_deck(Path(a.deck), "deck")
    except Exception as e:  # noqa: BLE001
        _res = None
        gsl_detail["_error"] = f"{type(e).__name__}: {e}"
    if _res:
        sm = _res.get("summary") or {}
        rows = _res.get("slides") or []
        # v8.7：按「计划的 slide_type」判定大页（封面 / 章节过渡 / 结尾），章节页不再被误计入内容页
        _plan_big = {"cover", "section_divider", "closing"}
        big_rows, content_rows = [], []
        for _i, _r in enumerate(rows):
            _st = str((slides[_i].get("slide_type") if _i < len(slides) else "") or "")
            (big_rows if _st in _plan_big else content_rows).append(_r)

        def _avg(rws, key):
            return round(sum(float(r.get(key) or 0) for r in rws) / len(rws), 1) if rws else 0.0

        content_avg = _avg(content_rows, "形")
        content_min = min([float(r.get("形") or 0) for r in content_rows], default=0.0)
        big_avg = _avg(big_rows, "形")
        groups_avg = float(sm.get("avg_groups") or 0)
        pics_avg = float(sm.get("avg_pics") or 0)
        colors_avg = float(sm.get("avg_colors") or 0)
        max_pt = max([float(r.get("最大字号") or 0) for r in big_rows], default=0.0)
        _mx = [float(r.get("最大字号") or 0) for r in rows if r.get("最大字号")]
        _mn = [float(r.get("最小字号") or 0) for r in rows if r.get("最小字号")]
        span = round(max(_mx) / min(_mn), 1) if _mx and _mn and min(_mn) > 0 else 0.0
        deck_stats = {"pages": len(rows), "content_avg_shapes": content_avg, "big_avg_shapes": big_avg,
                      "groups_per_page": groups_avg, "pics_per_page": pics_avg,
                      "colors_per_page": colors_avg, "big_max_font_pt": max_pt, "font_span_x": span}

        def _ratio(actual, target, mode):
            if isinstance(target, (list, tuple)) and len(target) == 2:
                lo, hi = float(target[0]), float(target[1])
                if lo <= actual <= hi:
                    return 1.0
                if actual <= 0:
                    return 0.0
                return max(0.0, min(actual / lo if actual < lo else hi / actual, 1.0))
            t = float(target or 0)
            if not t:
                return 0.0
            return max(0.0, min(actual / t, 1.0)) if mode == "min" else max(0.0, min(t / actual, 1.0))

        checks = [
            ("内容页形/页均值", content_avg, gsl_t.get("content_shapes_per_page_avg_min", 55), "min"),
            ("内容页单页形下限", content_min, gsl_t.get("content_shapes_per_page_min", 50), "min"),
            ("封面/章节页形/页", big_avg, gsl_t.get("cover_section_shapes_per_page_min", 40), "min"),
            ("组/页", groups_avg, gsl_t.get("groups_per_page_min", 3), "min"),
            ("图/页", pics_avg, gsl_t.get("pics_per_page", [1, 2]), "band"),
            ("色数/页", colors_avg, gsl_t.get("colors_per_page_max", 12), "max"),
            ("封面/章节页最大字号", max_pt, gsl_t.get("cover_section_max_font_pt_min", 187), "min"),
            ("字号跨度", span, gsl_t.get("font_span_x_min", 5.7), "min"),
        ]
        # 参考项（info，不计分）：内容页留白率 = 1 - 非装饰元素面积和 / 内容区面积
        _adv = cfg.get("advanced_design") or {}
        _ws_target = float(_adv.get("whitespace_ratio_min", 0.35))
        _ws = [1.0 - sum(max(0.0, float(e.get("w_in") or 0)) * max(0.0, float(e.get("h_in") or 0))
                         for e in (s.get("elements") or [])
                         if e.get("type") not in ("decoration_set", "image")) / (11.45 * 6.55)
               for s in slides if s.get("slide_type") not in ("cover", "section_divider", "closing")]
        if _ws:
            _wsv = round(sum(_ws) / len(_ws), 3)
            gsl_detail["内容页留白率"] = {"实测": _wsv, "目标": f"≥{_ws_target}",
                                       "达成": round(min(_wsv / _ws_target, 1.0), 2) if _ws_target else 0.0}

        per = 20.0 / len(checks)
        acc = 0.0
        for nm, actual, target, mode in checks:
            r = _ratio(actual, target, mode)
            acc += per * r
            gsl_detail[nm] = {"实测": round(actual, 1), "目标": target, "达成": round(r, 2)}
        detail["国赛对齐度(20)"] = round(acc, 1)
    else:
        detail["国赛对齐度(20)"] = 0.0
    total += detail["国赛对齐度(20)"]


    # 最弱页：先按 detect 的 error/warning 命中页，再按元素数偏离
    weak = {}
    for i in issues:
        p = i.get("slide")
        if p:
            weak[int(p)] = weak.get(int(p), 0) + (3 if i.get("level") == "error" else 1)
    for s in slides:
        if not inner(s):
            continue
        k = len([e for e in (s.get("elements") or []) if isinstance(e, dict)])
        dev = abs(k - floor) if dm == "vivid" else abs(k - 4)
        weak[s.get("slide_id")] = weak.get(s.get("slide_id"), 0) + (1 if dev >= 3 else 0)
    weakest = [{"slide": k, "weight": v} for k, v in sorted(weak.items(), key=lambda x: -x[1])][:int(sc.get("rewrite_weakest_n", 2))]

    # v9.0.2 评委审核四维度（规格 v9.3 L668）：视觉 AI 味 / 内容 AI 味 / 布局混乱 / 元素太少
    REVIEW = {}
    _HAND = ("hand-drawn-lines", "stamp-seal", "sticky-note", "paper-tape", "hand-arrow")
    _dsets, _hand_used = set(), False
    for s in slides:
        if not inner(s):
            continue
        for e in (s.get("elements") or []):
            if isinstance(e, dict) and str(e.get("type") or "") == "decoration_set":
                _sid = str(e.get("set_id") or "")
                _dsets.add(_sid)
                if _sid in _HAND:
                    _hand_used = True
    if not _dsets:
        REVIEW["视觉 AI 味"] = "关注：内容页未引用任何装饰组，版面易显 AI 味"
    elif not _hand_used:
        REVIEW["视觉 AI 味"] = ("关注：未使用手工感装饰（%d 组常规装饰）——建议掺入 1-2 处手工感组（%s）"
                                % (len(_dsets), "/".join(_HAND)))
    elif len(_dsets) < 3:
        REVIEW["视觉 AI 味"] = "正常：已用手工感装饰，但装饰组种类偏少（%d 组）" % len(_dsets)
    else:
        REVIEW["视觉 AI 味"] = "正常：手工感装饰 + %d 组装饰，多样性足够" % len(_dsets)

    _AI_WORDS = ("赋能", "打造", "构建", "引领", "未来可期", "我们坚信")
    _hit_words = []
    for s in slides:
        if not inner(s):
            continue
        for e in (s.get("elements") or []):
            if not isinstance(e, dict) or str(e.get("type") or "") != "text":
                continue
            if str(e.get("role") or "") in ("title", "caption"):
                continue
            _txt = str(e.get("text") or "")
            for _w in _AI_WORDS:
                if _w in _txt:
                    _hit_words.append(_w)
    REVIEW["内容 AI 味"] = ("正常：正文未出现空泛套话" if not _hit_words
                        else "关注：正文出现空泛词 %s——党建/政务/乡村振兴类属规范表达，科技/商业类建议改写"
                             % sorted(set(_hit_words)))

    _lf = cfg.get("layout_fallback") or {}
    _colmax = int(_lf.get("max_col_bands", 8))
    _btol = float(_lf.get("band_tolerance_in", 0.3))
    _messy = []
    for s in slides:
        if not inner(s):
            continue
        _xs = sorted(float(e.get("x_in") or 0) for e in (s.get("elements") or [])
                     if isinstance(e, dict) and str(e.get("role") or "") not in ("decoration", "background")
                     and not (isinstance(e.get("z_index"), (int, float)) and not isinstance(e.get("z_index"), bool)
                              and 10 <= float(e.get("z_index") or 0) < 20))
        _bands, _prev = 0, None
        for _x in _xs:
            if _prev is None or _x - _prev > _btol:
                _bands += 1
            _prev = _x
        if _bands > _colmax:
            _messy.append((s.get("slide_id"), _bands))
    REVIEW["布局混乱"] = ("正常：各内容页元素横向对齐到少数列带" if not _messy
                     else "关注：%d 页元素列带过多 %s——建议回归到 2-4 列区块" % (len(_messy), _messy[:4]))

    _few = []
    if dm == "vivid":
        _lo_e = int(((cfg.get("density_modes") or {}).get("vivid") or {}).get("min_elements_per_content_page", 6))
        for s in slides:
            if not inner(s):
                continue
            _k = len([e for e in (s.get("elements") or []) if isinstance(e, dict)])
            if _k < _lo_e:
                _few.append((s.get("slide_id"), _k))
        REVIEW["元素太少"] = ("正常：内容页元素量达标" if not _few
                         else "关注：%d 页元素少于耀眼版下限 %d：%s" % (len(_few), _lo_e, _few[:4]))

    score = round(total, 1)
    out = {"deck": a.deck, "candidate": a.candidate, "score": score,
           "pass_score": sc.get("pass_score", 75), "passed": score >= sc.get("pass_score", 75),
           "detail": detail, "detect": {"error": len(errs), "warning": len(warns)},
           "notes_nonempty": native.get("notes_nonempty"), "pages": n,
           "gsl_detail": gsl_detail, "deck_stats": deck_stats,
           "weakest_pages": weakest, "review_dimensions": REVIEW,
           "suggestion": ("达标：可进入人工终审。" if score >= sc.get("pass_score", 75)
                          else f"未达标：按 rewrite_weakest_n={sc.get('rewrite_weakest_n',2)} 重写上述最弱页，"
                               f"最多 {sc.get('max_rewrite_rounds',2)} 轮。")}
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"自我评分：{score} / 100（通过线 {out['pass_score']}）→ {'达标' if out['passed'] else '未达标'}")
    for k, v in detail.items():
        print(f"  {k:16s} {v}")
    print(f"  检测：error {len(errs)}｜warning {len(warns)}｜备注页 {native.get('notes_nonempty')}/{n}")
    if gsl_detail and "_error" not in gsl_detail:
        print("  国赛对齐度：" + "｜".join(f"{k} {v['实测']}（目标 {v['目标']}，达成 {v['达成']}）"
                                           for k, v in gsl_detail.items()))
    print(f"  最弱页：{weakest}")
    print("  评委审核维度：")
    for _rk, _rv in REVIEW.items():
        print(f"    - {_rk}：{_rv}")
    print(f"  {out['suggestion']}")


if __name__ == "__main__":
    main()