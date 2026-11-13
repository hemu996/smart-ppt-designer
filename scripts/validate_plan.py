#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面计划 + 知识库 + 资产引用校验器（工作流第 7 步，v5.1）。

用法：
    python scripts/validate_plan.py output/plan.json --knowledge knowledge
    python scripts/validate_plan.py output/plan.json --json output/validate_report.json

只做静态校验：不启动 PowerPoint、不构建 PPTX、不调 COM。退出码：
    0 = 通过（可能含 warning / info）
    1 = 存在 error
    2 = 计划文件无法读取或不是合法 JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "assets" / "config.json"
DEFAULT_KNOWLEDGE = ROOT / "knowledge"

# v9.0.6（官方 v9.9 前置功能）：用户模板索引懒加载缓存 / 动画素材库缓存
_USER_TPL_CACHE: dict = {}
_ANIM_LIB_CACHE: dict = {}

RELATION_TYPES = ["比较", "流程", "层级", "因果", "时间", "并列"]
CARD_RELATION_TYPES = RELATION_TYPES + ["通用"]
GOALS = ["告知", "说服", "汇报", "推广", "教学"]
STYLES = ["business", "tech", "humanities", "minimal"]
SLIDE_TYPES = ["cover", "toc", "section_divider", "concept", "content", "data_chart", "closing"]
INNER_TYPES = ["concept", "content", "data_chart"]
IMAGE_TYPES = ["cover_visual", "section_background", "concept_illustration", "closing_background"]
ELEMENT_TYPES = ["text", "shape", "chart", "table", "icon", "image", "formula", "decoration_set", "component"]
SHAPE_TYPES = ["rect", "roundRect", "ellipse", "line", "chevron", "triangle", "pentagon", "diamond"]
CHART_TYPES = ["column", "bar", "line", "pie", "doughnut"]
ALIGNS = ["left", "center", "right"]
VALIGNS = ["top", "middle", "bottom"]
NAV_MODES = ["sidebar", "top"]
MIN_RATIONALE_CHARS = 30
MAX_CLAIM_CHARS = 40
MAX_TABLE_ROWS = 6
MAX_TABLE_COLS = 5
MAX_ICONS_PER_SLIDE = 4


class Reporter:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.infos: list[dict] = []

    def error(self, path: str, msg: str) -> None:
        self.errors.append({"path": path, "message": msg})

    def warn(self, path: str, msg: str) -> None:
        self.warnings.append({"path": path, "message": msg})

    def info(self, path: str, msg: str) -> None:
        self.infos.append({"path": path, "message": msg})

    def dump(self) -> dict:
        return {
            "errors": self.errors, "warnings": self.warnings, "infos": self.infos,
            "counts": {"error": len(self.errors), "warning": len(self.warnings), "info": len(self.infos)},
        }


def user_template_index() -> dict:
    """v9.0.6 用户模板索引（懒加载 + 缓存），用于 fill 模式的模板存在性判定。"""
    if "data" not in _USER_TPL_CACHE:
        p = ROOT / "assets" / "user-templates" / "index.json"
        try:
            with open(p, encoding="utf-8") as f:
                _USER_TPL_CACHE["data"] = json.load(f)
        except Exception:
            _USER_TPL_CACHE["data"] = {}
    return _USER_TPL_CACHE["data"]


def load_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[warn] 无法读取配置 {path}：{exc}，使用内置默认值", file=sys.stderr)
        return {
            "canvas": {"width_in": 13.333, "height_in": 7.5},
            "fonts": {"whitelist": [], "min_pt": 10},
            "layout_thresholds": {"tolerance_in": 0.02},
            "image": {"max_images_per_deck": 5, "max_image_ratio": 0.333, "min_images_per_deck": 3},
            "visual_system": {"dir": "assets/visual-systems"},
            "layout_templates": {"dir": "assets/layout-templates"},
            "icons": {"library": "assets/icon-library/icons.json"},
            "effects": {"max_per_deck": 3},
            "deck_rules": {"candidates_per_round": 2, "min_slides": 3},
        }


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def scan_cards(knowledge_dir: Path, rep: Reporter) -> dict:
    cards: dict[str, dict] = {}
    cards_dir = (knowledge_dir / "cards").resolve()
    if not cards_dir.is_dir():
        rep.error("knowledge/cards", f"卡片目录不存在：{cards_dir}")
        return cards
    for md in sorted(cards_dir.glob("*.md")):
        if md.name.startswith("_"):
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        rel = f"knowledge/cards/{md.name}"
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        if not m:
            rep.error(rel, "缺少 YAML frontmatter（id/name/relation_type）")
            continue
        fm = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        cid = fm.get("id", "").strip()
        if not cid:
            rep.error(rel, "frontmatter 缺少 id")
            continue
        if cid != md.stem:
            rep.error(rel, f"id 与文件名不一致：id={cid}，文件名={md.stem}")
        if cid in cards:
            rep.error(rel, f"卡片 id 重复：{cid}")
        rt = fm.get("relation_type", "").strip()
        if rt not in CARD_RELATION_TYPES:
            rep.error(rel, f"relation_type 非法或缺失：{rt!r}，应为 {CARD_RELATION_TYPES}")
        if not fm.get("name"):
            rep.error(rel, "frontmatter 缺少 name")
        body = text[m.end():]
        if "适用条件" not in body:
            rep.error(rel, "缺少『适用条件』段落")
        if "反例" not in body:
            rep.error(rel, "缺少『反例（禁止使用）』段落（红线：卡片不能只写外观描述）")
        cards[cid] = {"relation_type": rt, "path": rel}
    if not cards:
        rep.error("knowledge/cards", "没有任何可用设计卡片")
    return cards


_LAYOUT_LIB_CACHE: dict = {}


def layout_patterns() -> list:
    """v9.0.2 常见布局特征库（模板校验兜底的依据），懒加载 + 缓存"""
    if "data" not in _LAYOUT_LIB_CACHE:
        p = ROOT / "assets/layout-patterns/common-layouts.json"
        try:
            with open(p, encoding="utf-8") as _f:
                _LAYOUT_LIB_CACHE["data"] = json.load(_f).get("patterns") or []
        except Exception:
            _LAYOUT_LIB_CACHE["data"] = []
    return _LAYOUT_LIB_CACHE["data"]


def load_assets(cfg: dict, rep: Reporter) -> dict:
    vs_dir = ROOT / cfg.get("visual_system", {}).get("dir", "assets/visual-systems")
    lt_dir = ROOT / cfg.get("layout_templates", {}).get("dir", "assets/layout-templates")
    icon_file = ROOT / cfg.get("icons", {}).get("library", "assets/icon-library/icons.json")
    out = {"visual_systems": {}, "layout_templates": {}, "icons": {}, "systems_data": {}, "decoration_sets": {}}
    # 视觉系统 + 个人风格库（v8.2：个人风格与内置同 schema，一并可引用）
    personal_dir = ROOT / "assets" / "personal-styles"
    for d in (vs_dir, personal_dir):
        for f in sorted(d.glob("*.json")):
            j = read_json(f)
            if not isinstance(j, dict) or "colors" not in j:
                rep.error(f"{d.relative_to(ROOT).as_posix()}/{f.name}", "视觉系统文件缺少 colors")
                continue
            name = j.get("system_name", f.stem)
            if name in out["visual_systems"] and d is personal_dir:
                rep.info(f"assets/personal-styles/{f.name}", f"个人风格 {name} 覆盖同名内置系统（按设计允许）")
            out["visual_systems"][name] = f.name
            out["systems_data"][name] = j
    if not out["visual_systems"]:
        rep.error("assets/visual-systems", "没有任何视觉系统可用")
    for f in sorted(lt_dir.glob("*.json")):
        d = read_json(f)
        if isinstance(d, dict) and d.get("name"):
            out["layout_templates"][d["name"]] = d
    if not out["layout_templates"]:
        rep.error("assets/layout-templates", "没有任何布局模板可用")
    ds_dir = ROOT / str((cfg.get("decoration_sets", {}) or {}).get("dir", "assets/decoration-sets"))
    for f in sorted(ds_dir.glob("*.json")):
        j = read_json(f)
        if isinstance(j, dict) and j.get("id"):
            out["decoration_sets"][j["id"]] = j
    if not out["decoration_sets"]:
        rep.error("assets/decoration-sets", "没有任何装饰组可用")
    icons = read_json(icon_file)
    if isinstance(icons, dict) and isinstance(icons.get("icons"), dict):
        out["icons"] = icons
    else:
        rep.error("assets/icon-library/icons.json", "图标库缺失或结构错误")
    return out


def num(rep: Reporter, path: str, val, name: str) -> bool:
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        rep.error(path, f"{name} 必须是数字，当前 {val!r}")
        return False
    return True


def in_zone(el: dict, template: dict | None) -> bool:
    if not template:
        return True
    for z in template.get("zones", {}).values():
        if (el["x_in"] >= z["x_in"] - 0.35 and el["y_in"] >= z["y_in"] - 0.35
                and el["x_in"] + el["w_in"] <= z["x_in"] + z["w_in"] + 0.35
                and el["y_in"] + el["h_in"] <= z["y_in"] + z["h_in"] + 0.35):
            return True
    return False


def validate_elements(spath: str, elements, cfg: dict, vs: dict, icons: dict, template: dict | None, rep: Reporter, slide_type: str | None = None, decoration_sets: dict | None = None, components: dict | None = None) -> None:
    canvas = cfg.get("canvas", {})
    width, height = float(canvas.get("width_in", 13.333)), float(canvas.get("height_in", 7.5))
    tol = float(cfg.get("layout_thresholds", {}).get("tolerance_in", 0.02))
    min_pt = float(cfg.get("fonts", {}).get("min_pt", 10))
    whitelist = cfg.get("fonts", {}).get("whitelist", [])
    frange = (vs.get("fonts") or {}) if isinstance(vs, dict) else {}
    icon_count = 0

    if not isinstance(elements, list):
        rep.error(spath, "elements 必须是数组")
        return

    # v8.9 构图两硬约束的材料（在下方循环里收集）
    _comp = cfg.get("composition") or {}
    _comp_boxes = []

    _card_sig = {}

    z_dec, z_content, z_title = [], [], []
    for idx, el in enumerate(elements):
        epath = f"{spath}.elements[{idx}]"
        if not isinstance(el, dict):
            rep.error(epath, "元素必须是对象")
            continue
        etype = el.get("type")
        if etype not in ELEMENT_TYPES:
            rep.error(epath, f"type 非法：{etype!r}，应为 {ELEMENT_TYPES}")
        if etype == "component":
            _cid = el.get("component_id")
            _comps = components or {}
            if _cid not in _comps:
                rep.error(epath, f"组件不存在：{_cid!r}（计划 components 里可选：{sorted(_comps)}）")
            elif not (_comps[_cid].get("shapes") or []):
                rep.error(epath, f"组件 {_cid!r} 没有 shapes")
        if etype == "decoration_set":
            _sid = el.get("set_id") or el.get("set")
            _ds = decoration_sets or {}
            if _sid not in _ds:
                rep.error(epath, f"装饰组不存在：{_sid!r}（可选：{sorted(_ds)}）")
            elif el.get("role") != "decoration":
                rep.warn(epath, f"装饰组建议 role=decoration（当前 {el.get('role')!r}）")



    # v5.2 多图层堆叠：每个元素必须声明 z_index（整数 ≥ 0）
        z = el.get("z_index")
        if z is None:
            rep.error(epath, "缺少 z_index（红线第 11 条：每页元素必须分层）")
        elif not isinstance(z, int) or isinstance(z, bool) or z < 0:
            rep.error(epath, f"z_index 必须是 ≥ 0 的整数，当前 {z!r}")
        else:
            role = el.get("role")
            if etype == "decoration_set" and not (10 <= z <= 19):
                rep.error(epath, f"装饰组必须放在 L2 装饰层（z_index 10–19），当前 {z}")
            if role == "decoration":
                z_dec.append(z)
            elif role == "title":
                z_title.append(z)
            else:
                z_content.append(z)

        # v8.9 去 AI 感：统计同页卡片形态与尺寸的重复度（判定"卡片全一样"）
        if etype in ("shape", "component") and str(el.get("role") or "") in ("content", "module", ""):
            try:
                _sig = (str(el.get("shape_type") or ("component:" + str(el.get("component_id")) if etype == "component" else "")),
                        round(float(el["w_in"]), 2), round(float(el["h_in"]), 2))
                _card_sig[_sig] = _card_sig.get(_sig, 0) + 1
            except (KeyError, TypeError, ValueError):
                pass

        # v8.9 构图约束材料：几何 / 层级（装饰组不参与叠压配对）
        if _comp and etype != "decoration_set":
            try:
                _bx = (float(el["x_in"]), float(el["y_in"]), float(el["w_in"]), float(el["h_in"]),
                       int(el.get("z_index")), str(el.get("role") or ""))
                _comp_boxes.append((idx, _bx))
            except (KeyError, TypeError, ValueError):
                pass

        box = {}
        ok_box = True
        for key in ("x_in", "y_in", "w_in", "h_in"):
            if key not in el or not num(rep, epath, el.get(key), key):
                rep.error(epath, f"缺少或非法的坐标字段 {key}")
                ok_box = False
                continue
            box[key] = float(el[key])
        if ok_box:
            if box["w_in"] <= 0 or box["h_in"] <= 0:
                rep.error(epath, f"w_in/h_in 必须为正：{box['w_in']}, {box['h_in']}")
            if box["x_in"] < -tol or box["y_in"] < -tol:
                rep.error(epath, f"起点越界：x={box['x_in']}, y={box['y_in']}")
            if box["x_in"] + box["w_in"] > width + tol:
                rep.error(epath, f"横向越界：x+w={box['x_in'] + box['w_in']:.3f} > {width}")
            if box["y_in"] + box["h_in"] > height + tol:
                rep.error(epath, f"纵向越界：y+h={box['y_in'] + box['h_in']:.3f} > {height}")
            if template and etype != "decoration_set" and not in_zone(box, template):
                rep.warn(epath, f"元素不在布局模板 {template.get('name')} 的任何 zone 内（x={box['x_in']}, y={box['y_in']}），请确认是否刻意偏离")

        if el.get("focus") is not None and not isinstance(el.get("focus"), bool):
            rep.error(epath, f"focus 必须是布尔值（用于声明视觉焦点），当前 {el.get('focus')!r}")

        if etype == "text":
            if not str(el.get("text", "")).strip():
                rep.error(epath, "text 元素缺少文本")
            if "font_pt" not in el or not num(rep, epath, el.get("font_pt"), "font_pt"):
                rep.error(epath, "text 元素缺少 font_pt")
            elif float(el["font_pt"]) < min_pt:
                rep.error(epath, f"字号低于下限：{el['font_pt']} < {min_pt}")
            font = el.get("font")
            if font and whitelist and font not in whitelist:
                rep.warn(epath, f"字体 {font!r} 不在白名单，构建时回落")
            role = el.get("role")
            rng = None
            if role == "title":
                if slide_type == "cover":
                    rng = frange.get("title_size", [36, 44])
                elif slide_type == "section_divider":
                    rng = frange.get("section_size", [28, 32])
                elif slide_type == "closing":
                    rng = frange.get("section_size", [28, 32])
                else:
                    rng = frange.get("page_title_size", [20, 24])
            elif role == "metric":
                rng = frange.get("metric_size")
            elif role in ("module_title", "subtitle"):
                rng = frange.get("module_size", [16, 18])
            elif role == "body":
                rng = frange.get("body_size")
            elif role == "caption":
                rng = frange.get("caption_size", [10, 11])
            elif role == "label":
                rng = frange.get("body_size", [12, 14])
            if role == "title" and slide_type in ("cover", "toc", "section_divider", "closing"):
                _dom = frange.get("display_size") or [120, 287]
                rng = [rng[0], max(rng[1], _dom[1])]
            if rng and isinstance(el.get("font_pt"), (int, float)) and not (rng[0] - 1 <= el["font_pt"] <= rng[1] + 2):
                rep.warn(epath, f"字号 {el['font_pt']}pt 越出视觉系统 {role} 区间 {rng}")
        elif etype == "shape":
            if el.get("shape_type") not in SHAPE_TYPES:
                rep.error(epath, f"shape_type 非法：{el.get('shape_type')!r}，应为 {SHAPE_TYPES}")
        elif etype == "chart":
            c = el.get("chart")
            if not isinstance(c, dict):
                rep.error(epath, "chart 元素缺少 chart 对象")
                continue
            if c.get("chart_type") not in CHART_TYPES:
                rep.error(epath, f"chart_type 非法：{c.get('chart_type')!r}")
            labels = c.get("labels")
            series = c.get("series")
            if not isinstance(labels, list) or not labels:
                rep.error(epath, "chart.labels 必须是非空数组")
            elif any(re.fullmatch(r"\d+", str(x).strip()) for x in labels):
                rep.error(epath, "chart.labels 出现纯数字占位（如 1/2/3）——分类必须是业务名（首轮视觉校验的必改项）")
            if not isinstance(series, list) or not series:
                rep.error(epath, "chart.series 必须是非空数组")
            elif isinstance(labels, list):
                hi = c.get("highlight_index")
                if hi is not None and (not isinstance(hi, int) or isinstance(hi, bool) or not (0 <= hi < len(labels))):
                    rep.error(epath, f"chart.highlight_index 必须是 0–{len(labels) - 1} 的整数，当前 {hi!r}")
                for si, s in enumerate(series):
                    if not isinstance(s, dict):
                        rep.error(f"{epath}.series[{si}]", "series 项必须是对象")
                        continue
                    if not s.get("name"):
                        rep.warn(f"{epath}.series[{si}]", "series 缺少 name（图例会用默认名）")
                    vals = s.get("values")
                    if not isinstance(vals, list):
                        rep.error(f"{epath}.series[{si}]", "series.values 必须是数组")
                    elif len(vals) != len(labels):
                        rep.error(f"{epath}.series[{si}]", f"labels 与 values 长度不等：{len(labels)} vs {len(vals)}")
        elif etype == "table":
            t = el.get("table")
            if not isinstance(t, dict):
                rep.error(epath, "table 元素缺少 table 对象")
                continue
            rows = t.get("rows")
            if not isinstance(rows, list) or not rows:
                rep.error(epath, "table.rows 必须是非空二维数组")
            else:
                if len(rows) > MAX_TABLE_ROWS:
                    rep.error(epath, f"表格行数 {len(rows)} 超过上限 {MAX_TABLE_ROWS}")
                widths = {len(r) for r in rows if isinstance(r, list)}
                if len(widths) > 1:
                    rep.error(epath, f"表格各行列数不一致：{sorted(widths)}")
                for r in rows:
                    if not isinstance(r, list):
                        rep.error(epath, "table.rows 每行必须是数组")
                        break
                if widths and max(widths) > MAX_TABLE_COLS:
                    rep.error(epath, f"表格列数 {max(widths)} 超过上限 {MAX_TABLE_COLS}")
            if not (t.get("col_widths_in") or []):
                rep.warn(epath, "table 未给 col_widths_in，列宽将按均分处理")
        elif etype == "icon":
            icon_count += 1
            name = el.get("icon")
            if name not in (icons.get("icons") or {}):
                rep.error(epath, f"图标不存在：{name!r}（见 assets/icon-library/icons.json）")
            if not el.get("color"):
                rep.warn(epath, "icon 未指定 color token，将使用 accent")
        elif etype == "image":
            if not el.get("image_path"):
                rep.warn(epath, "image 元素没有 image_path，构建时将跳过")
            else:
                # v8.9 跨客户端兼容：框比例与源图比例偏差过大时提示（构建会按原始比例 contain 摆放，框内可能留边）
                try:
                    from PIL import Image as _PILImage
                    _ip = ROOT / str(el["image_path"])
                    if _ip.exists():
                        with _PILImage.open(_ip) as _im:
                            _ar = float(_im.width) / float(_im.height) if _im.height else 0.0
                        _bar = float(el["w_in"]) / float(el["h_in"])
                        if _ar > 0 and _bar > 0 and abs(_ar - _bar) / _ar > 0.15:
                            rep.info(epath, f"图片框比例 {_bar:.2f} 与源图 {_ar:.2f} 偏差 >15%："
                                             f"构建按原始比例 contain 摆放（不拉伸），框内会留边并补渐变")
                except Exception:
                    pass
        elif etype == "formula":
            if not str(el.get("text", "")).strip():
                rep.error(epath, "formula 元素缺少 text")
            if el.get("style") == "omml_todo":
                rep.info(epath, "复杂排版公式：将由人工在 PowerPoint 公式编辑器中替换（诚实边界）")
    if icon_count > MAX_ICONS_PER_SLIDE:
        rep.warn(spath, f"单页图标 {icon_count} 个 > 建议上限 {MAX_ICONS_PER_SLIDE}")

    # 多图层堆叠的层序硬约束：装饰层不得高于内容层（否则装饰会遮挡文字）
    # v8.9 去 AI 感：同页出现 3 个及以上"形态+尺寸完全相同"的卡片 → 提示混用形态与大小
    _rep_sig = [k for k, v in _card_sig.items() if v >= 3]
    if _rep_sig:
        rep.warn(spath, "卡片同质化：本页有 " + "、".join(f"{k[1]}×{k[2]}in 的同类卡片 {_card_sig[k]} 张" for k in _rep_sig) +
                         " 形态与尺寸完全相同——建议混用直角/大圆角/描边款并区分大小（去 AI 感，见 references/composition.md §五）")

    # v8.9 页面构图两硬约束（error 级，仅在有 composition 配置时生效）
    if _comp and _comp_boxes:
        _page_area = width * height
        _excl = set(_comp.get("big_element_exclude_roles") or ["decoration", "background"])
        _need = float(_comp.get("min_big_element_area_ratio", 0.333))
        _ratios = [(b[3] * b[4] / _page_area) for _, b in _comp_boxes if b[5] not in _excl]
        if _ratios and max(_ratios) < _need:
            rep.error(spath, f"构图约束①大对比：本页最大内容元素只占页面 {max(_ratios):.1%} < 要求 {_need:.1%}"
                             f"（做法：给本页加一个占比 ≥1/3 的大块——背板 / 大图 / 大卡片）")
        _min_ov = int(_comp.get("min_overlap_pairs", 1))
        _min_area = float(_comp.get("min_overlap_area_in2", 0.15))
        _pairs = []
        for _i in range(len(_comp_boxes)):
            for _j in range(_i + 1, len(_comp_boxes)):
                a = _comp_boxes[_i][1]; b = _comp_boxes[_j][1]
                if a[5] == "decoration" or b[5] == "decoration":
                    continue
                ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
                oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                if ox > 0 and oy > 0 and ox * oy > _min_area and a[4] != b[4]:
                    _pairs.append((_comp_boxes[_i][0], _comp_boxes[_j][0]))
        if len(_pairs) < _min_ov:
            rep.error(spath, f"构图约束②层叠：本页前后叠压的元素对只有 {len(_pairs)} 对 < 要求 {_min_ov} 对"
                             f"（做法：让内容压在背板/色块/大图上，用 z_index 拉开前后关系）")

    if z_dec and z_content and max(z_dec) >= min(z_content):
        rep.error(spath, f"装饰层不得高于内容层：装饰 max z_index={max(z_dec)} ≥ 内容 min z_index={min(z_content)}（红线第 11 条）")
    for z in z_dec:
        if not (10 <= z <= 19):
            rep.warn(spath, f"装饰元素 z_index={z} 不在 L2 区间 10–19，请确认分层")
    for z in z_title:
        if z < 30:
            rep.warn(spath, f"标题元素 z_index={z} 低于 L4 起点 30，可能被内容层覆盖")


def validate_grid_focus_icons(spath: str, slide: dict, cfg: dict, vs: dict, rep: Reporter) -> None:
    """v5.5 三项专业规范：12 列网格贴合度、单页视觉焦点唯一、图标风格与尺寸一致。"""
    elements = [e for e in (slide.get("elements") or []) if isinstance(e, dict)]
    if not elements:
        return

    # 1) 网格贴合度（12 列；封面/章节/结尾为全幅页，不参与）
    grid = (vs.get("grid") or cfg.get("grid") or {})
    cols = int(grid.get("columns", 12))
    x0 = float(grid.get("content_x_in", cfg.get("grid", {}).get("content_x_in", 1.38)))
    cw = float(grid.get("content_w_in", cfg.get("grid", {}).get("content_w_in", 11.45)))
    tol = float(grid.get("tolerance_in", cfg.get("grid", {}).get("tolerance_in", 0.02))) + 0.23  # 允许 1/4 列内的偏差
    if slide.get("slide_type") not in ("cover", "section_divider", "closing"):
        col = cw / cols
        offs = []
        for i, el in enumerate(elements):
            x = el.get("x_in")
            if not isinstance(x, (int, float)):
                continue
            k = round((x - x0) / col)
            if 0 <= k <= cols and abs(x - (x0 + k * col)) > tol:
                offs.append((i, round(x, 3)))
        if offs:
            rep.info(spath, f"网格贴合：{len(offs)}/{len(elements)} 个元素偏离 12 列网格 1/4 列以上，例如 elements[{'、'.join(str(o[0]) for o in offs[:4])}]；建议对齐列边界")

    # 2) 视觉焦点唯一（v5.5 红线第 17 条）
    text_sizes = [(i, el.get("font_pt")) for i, el in enumerate(elements)
                  if el.get("type") == "text" and isinstance(el.get("font_pt"), (int, float))]
    metrics = [i for i, el in enumerate(elements) if el.get("role") == "metric"]
    explicit = [i for i, el in enumerate(elements) if el.get("focus") is True]
    if explicit:
        if len(explicit) > 1:
            rep.warn(spath, f"视觉焦点不唯一：有 {len(explicit)} 个元素被显式标记 focus")
    elif metrics:
        if len(metrics) > 1:
            rep.warn(spath, f"视觉焦点不唯一：同页有 {len(metrics)} 个 metric 元素，只应保留一个核心指标")
    elif text_sizes:
        mx = max(s for _, s in text_sizes)
        top = [i for i, s in text_sizes if s == mx]
        if len(top) > 1 and mx >= 20:
            rep.warn(spath, f"视觉焦点不唯一：{len(top)} 个元素同为最大字号 {mx}pt，应有一个明显更突出")
        elif mx < 20:
            rep.warn(spath, f"缺少视觉焦点：本页最大字号仅 {mx}pt（H3 下限 20pt），没有明确的重点")

    # 3) 图标风格与尺寸一致（v5.5 红线第 18 条）
    icons = [el for el in elements if el.get("type") == "icon"]
    if icons:
        deck_style = vs.get("icon_style", "solid")
        for i, el in enumerate(icons):
            if el.get("icon_style") and el.get("icon_style") != deck_style:
                rep.warn(f"{spath}.icons[{i}]", f"图标风格 {el['icon_style']!r} 与整份视觉系统 {deck_style!r} 不一致（不能线性/面性混搭）")
            color = el.get("color")
            if color not in (None, "secondary", "accent"):
                rep.warn(f"{spath}.icons[{i}]", f"图标颜色 {color!r} 与视觉系统辅助色（secondary/accent）不一致")
        sizes = {(round(float(el.get("w_in", 0)), 2), round(float(el.get("h_in", 0)), 2)) for el in icons}
        if len(sizes) > 1:
            rep.warn(spath, f"同页图标尺寸不统一：{sorted(sizes)}（同层级图标尺寸应一致）")


def validate_plan(plan: dict, cards: dict, cfg: dict, assets: dict, rep: Reporter) -> dict:
    stats = {"slides": 0, "images": 0, "effects": 0, "tables": 0, "charts": 0}
    canvas = cfg.get("canvas", {})
    image_cfg = cfg.get("image", {})
    max_images = int(image_cfg.get("max_images_per_deck", 5))
    min_images = int(image_cfg.get("min_images_per_deck", 3))
    max_ratio = float(image_cfg.get("max_image_ratio", 0.333))
    max_effects = int(cfg.get("effects", {}).get("max_per_deck", 3))
    min_slides = int(cfg.get("deck_rules", {}).get("min_slides", 3))

    intent = plan.get("brief_intent")
    if not isinstance(intent, dict):
        rep.error("brief_intent", "缺少 brief_intent 对象")
        intent = {}
    for key, allowed in (("communication_goal", GOALS), ("relation_type", RELATION_TYPES), ("style_preference", STYLES)):
        if intent.get(key) not in allowed:
            rep.error(f"brief_intent.{key}", f"取值非法或缺失：{intent.get(key)!r}，应为 {allowed}")
    if not str(intent.get("audience", "")).strip():
        rep.error("brief_intent.audience", "缺少受众描述")
    if not str(intent.get("deck_title", "")).strip():
        rep.warn("brief_intent.deck_title", "未填写演示稿标题")

    db = plan.get("design_brief")
    _nav_on = db.get("navigation_enabled") if isinstance(db, dict) else None
    if _nav_on is not None and not isinstance(_nav_on, bool):
        rep.error("design_brief.navigation_enabled", f"navigation_enabled 必须是布尔值，当前 {_nav_on!r}")
    _scope = db.get("navigation_scope") if isinstance(db, dict) else None
    if _scope is not None and str(_scope) not in ("full", "sparse", "none"):
        rep.error("design_brief.navigation_scope",
                  f"navigation_scope 非法：{_scope!r}（可选 full / sparse / none；默认 sparse）")
    if isinstance(db, dict) and "navigation_enabled" not in db:
        rep.info("design_brief.navigation_enabled",
               "未显式声明 navigation_enabled，按包级默认处理（v9.0.1 起默认关闭，即全篇不画导航）；要开请显式写 true")
    if not isinstance(db, dict):
        rep.error("design_brief", "缺少 design_brief 对象（v5.1 必填）")
        db = {}
    # v9.0.2 视觉母题（规格 v9.3 L258-266）：3-5 种装饰性母题，1 主 + 2-4 次
    # ---- v9.0.6（官方 v9.9 前置功能，段落级合并）----
    # 模板生成模式（free 自由生成 / fill 模板填充）
    _tm = db.get("template_mode") if isinstance(db, dict) else None
    if _tm is not None and str(_tm) not in ("free", "fill"):
        rep.error("design_brief.template_mode",
                  f"template_mode 非法：{_tm!r}（可选 free / fill；默认 free，生成前应先问用户）")
    _utv = db.get("user_template") if isinstance(db, dict) else None
    if isinstance(db, dict) and "template_mode" not in db:
        rep.info("design_brief.template_mode",
                 "未声明 template_mode，按包级默认 free（自由生成）处理；生成前应先问用户用自由生成还是模板填充")
    if str(_tm or "") == "fill":
        if not str(_utv or "").strip():
            rep.error("design_brief.user_template",
                      "template_mode=fill 时必须指定 user_template（索引 id 如 ut-012，或模板名）")
        else:
            _idx = user_template_index()
            _tpls = (_idx.get("templates") or []) if isinstance(_idx, dict) else []
            _key = str(_utv).strip()
            _hit = [t for t in _tpls
                    if _key in (str(t.get("id")), str(t.get("name")), str(t.get("path")))]
            if not _tpls:
                rep.warn("design_brief.user_template",
                         "本机没有用户模板索引：跑 python scripts/index_user_templates.py 生成，或改用 free")
            elif not _hit:
                rep.error("design_brief.user_template",
                          f"模板 {_key!r} 不在索引中（索引共 {len(_tpls)} 份）")
            elif not Path(str(_hit[0].get("path") or "")).exists():
                rep.warn("design_brief.user_template",
                         f"模板 {_key!r} 已在索引里，但原文件不在本机，按 check_assets.py 提示补充素材")
    elif str(_utv or "").strip():
        rep.warn("design_brief.user_template",
                 f"已指定 user_template={_utv!r}，但 template_mode 不是 fill：模板不会生效")

    _vmc = cfg.get("visual_motifs") or {}
    _vms = db.get("visual_motifs") if isinstance(db, dict) else None
    if _vms is None:
        rep.info("design_brief.visual_motifs",
                 "未声明视觉母题：建议按规格选定 3-5 种装饰性母题（1 主 + 2-4 次，只约束装饰元素），见 references/visual-motifs.md")
    elif not isinstance(_vms, list):
        rep.error("design_brief.visual_motifs", f"visual_motifs 必须是数组，当前 {type(_vms).__name__}")
    else:
        _lo = int(_vmc.get("min_count", 3))
        _hi = int(_vmc.get("max_count", 5))
        if not (_lo <= len(_vms) <= _hi):
            rep.error("design_brief.visual_motifs", f"母题数量应在 {_lo}-{_hi} 之间，当前 {len(_vms)}")
        _vm_names, _prim, _sec = [], 0, 0
        for _m in _vms:
            if not isinstance(_m, dict):
                rep.error("design_brief.visual_motifs", f"母题条目必须是对象，当前 {_m!r}")
                continue
            _nm = str(_m.get("name") or "").strip()
            if not _nm:
                rep.error("design_brief.visual_motifs", "母题条目缺少 name")
            elif _nm in _vm_names:
                rep.error("design_brief.visual_motifs", f"母题名称重复：{_nm!r}")
            else:
                _vm_names.append(_nm)
            _rl = str(_m.get("role") or "").strip()
            if _rl == "primary":
                _prim += 1
            elif _rl == "secondary":
                _sec += 1
            else:
                rep.error("design_brief.visual_motifs", f"母题 {_nm!r} 的 role 非法：{_rl!r}（应为 primary / secondary）")
        _pc = int(_vmc.get("primary_count", 1))
        if _prim != _pc:
            rep.error("design_brief.visual_motifs", f"主母题应恰好 {_pc} 个，当前 {_prim}")
        _sr = list(_vmc.get("secondary_range") or [2, 4])
        _slo, _shi = int(_sr[0]), int(_sr[1])
        if not (_slo <= _sec <= _shi):
            rep.error("design_brief.visual_motifs", f"次母题应在 {_slo}-{_shi} 之间，当前 {_sec}")
    # 不设默认风格（v5.6）：视觉系统必须显式指定且存在，并写明选择理由
    vs_name = db.get("visual_system")
    if not str(vs_name or "").strip():
        rep.error("design_brief.visual_system",
                  f"未指定视觉系统（不设默认风格）：请先 python scripts/find_style.py <内容关键词> 检索，"
                  f"再显式填写 system_name；无命中时读参考稿推导或先问用户。可选：{sorted(assets['visual_systems'])}")
    elif vs_name not in assets["visual_systems"]:
        rep.error("design_brief.visual_system",
                  f"视觉系统不存在：{vs_name!r}（可选：{sorted(assets['visual_systems'])}）")
    rationale = str(db.get("style_rationale") or "").strip()
    if len(rationale) < 12:
        rep.error("design_brief.style_rationale",
                  f"缺少风格选择理由（style_rationale 需 ≥12 字，当前 {len(rationale)} 字）：写清按什么内容依据、"
                  f"或哪份参考稿选的这套风格；判断不出时先问用户，不要回落默认")
    elif vs_name in assets["visual_systems"]:
        conf = str(((assets["systems_data"].get(vs_name) or {}).get("extraction") or {}).get("confidence", ""))
        if conf.startswith("low"):
            rep.warn("design_brief.visual_system",
                     f"所选风格 {vs_name} 为自动提取且置信度较低（{conf}）：使用前请核对 assets/style-cards/ 对应风格卡片")
    # 密度模式（规格 v7.5 二选一：concise 简洁版 / vivid 高级耀眼版）
    dm = db.get("density_mode")
    dm_modes = cfg.get("density_modes") or {}
    dm_keys = [k for k in dm_modes if not str(k).startswith("_")]
    if not dm:
        rep.warn("design_brief.density_mode",
                 f"未声明密度模式（规格要求二选一）：{dm_keys}（concise=简洁版，vivid=高级耀眼版）")
    elif dm not in dm_keys:
        rep.error("design_brief.density_mode", f"取值非法：{dm!r}，应为 {dm_keys}")
    elif dm == "vivid":
        # v8.0：耀眼版禁止大面积纯白/纯平背景（浅底系统需靠渐变/纹理/装饰纹样补层次）
        bg = str(((assets["systems_data"].get(vs_name) or {}).get("colors") or {}).get("background", "")).upper().lstrip("#")
        if bg in ("FFFFFF", "F8F9FA", "FBF7F0", "FFF8DC", "FDFAF5", "FBFAF7"):
            rep.info("design_brief.density_mode",
                     f"耀眼版要求背景不得纯白/纯平：所选系统 background=#{bg}，"
                     f"请补背景渐变、纹理或淡装饰纹样，不要留成纯色平面（红线 19）")

    # 叙事与篇幅（规格第七节：金字塔叙事 + 时长驱动页数）
    nar_cfg = cfg.get("narrative") or {}
    dur = intent.get("duration_min")
    if dur is not None:
        try:
            per_min = float(nar_cfg.get("pages_per_minute", 1.5))
            expect = float(dur) * per_min
            cands = plan.get("candidates") or []
            got = sum(len(c.get("slides") or []) for c in cands if isinstance(c, dict)) / max(1, len(cands))
            if expect and abs(got - expect) / expect > 0.3:
                rep.warn("brief_intent.duration_min",
                         f"时长 {dur} 分钟按 {per_min} 页/分钟约需 {expect:.0f} 页，"
                         f"当前候选平均 {got:.1f} 页，偏差超过 30%")
        except (TypeError, ValueError):
            rep.warn("brief_intent.duration_min", f"duration_min 取值非法：{dur!r}")

    if db.get("navigation_mode") not in NAV_MODES:
        rep.error("design_brief.navigation_mode", f"取值非法或缺失：{db.get('navigation_mode')!r}，应为 {NAV_MODES}")
    sections = db.get("sections")
    if not isinstance(sections, list) or not (2 <= len(sections) <= 6):
        rep.error("design_brief.sections", f"章节列表必须 2–6 项，当前 {sections if not isinstance(sections, list) else len(sections)}")
        sections = sections if isinstance(sections, list) else []
    vs = assets["systems_data"].get(vs_name, {})

    candidates = plan.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 2:
        rep.error("candidates", f"必须恰好 2 套候选方案，当前 {0 if not isinstance(candidates, list) else len(candidates)} 套")
        return stats

    sigs = []
    for ci, cand in enumerate(candidates):
        cpath = f"candidates[{ci}]"
        if not isinstance(cand, dict):
            rep.error(cpath, "候选方案必须是对象")
            continue
        if cand.get("candidate_id") not in ("A", "B"):
            rep.error(f"{cpath}.candidate_id", f"应为 'A' 或 'B'，当前 {cand.get('candidate_id')!r}")
        rationale = str(cand.get("rationale", "")).strip()
        if len(rationale) < MIN_RATIONALE_CHARS:
            rep.error(f"{cpath}.rationale", f"选型理由过短（{len(rationale)} 字 < {MIN_RATIONALE_CHARS}）")
        slides = cand.get("slides")
        if not isinstance(slides, list) or len(slides) < min_slides:
            rep.error(f"{cpath}.slides", f"至少 {min_slides} 页，当前 {0 if not isinstance(slides, list) else len(slides)}")
            continue

        sig = []
        seen, img_count, effect_count = [], 0, 0
        for si, s in enumerate(slides):
            spath = f"{cpath}.slides[{si}]"
            if not isinstance(s, dict):
                rep.error(spath, "页面必须是对象")
                continue
            sid = s.get("slide_id")
            if not isinstance(sid, int) or isinstance(sid, bool) or sid <= 0:
                rep.error(f"{spath}.slide_id", f"必须是正整数，当前 {sid!r}")
            elif sid in seen:
                rep.error(f"{spath}.slide_id", f"slide_id 重复：{sid}")
            elif seen and sid <= seen[-1]:
                rep.error(f"{spath}.slide_id", f"slide_id 必须升序，{sid} 不大于 {seen[-1]}")
            else:
                seen.append(sid)

            stype = s.get("slide_type")
            if stype not in SLIDE_TYPES:
                rep.error(f"{spath}.slide_type", f"非法：{stype!r}，应为 {SLIDE_TYPES}")
            lt = s.get("layout_template")
            if lt not in assets["layout_templates"]:
                rep.error(f"{spath}.layout_template", f"布局模板不存在：{lt!r}（可选：{sorted(assets['layout_templates'])}）")
            card = s.get("card_used")
            if card not in cards:
                rep.error(f"{spath}.card_used", f"卡片不存在：{card!r}（可选：{sorted(cards)}；检索用 python scripts/find_asset.py --kind card <信息关系>）")
            elif cards[card]["relation_type"] not in ("通用", intent.get("relation_type")):
                rep.info(f"{spath}.card_used", f"卡片 relation_type（{cards[card]['relation_type']}）与简报主关系（{intent.get('relation_type')}）不同：跨类型套用属正常")

            claim = str(s.get("claim", "")).strip()
            if not claim:
                rep.error(f"{spath}.claim", "缺少 claim")
            elif len(claim) > MAX_CLAIM_CHARS:
                rep.warn(f"{spath}.claim", f"claim 偏长（{len(claim)} 字 > {MAX_CLAIM_CHARS}）")

            # 行动标题（规格第七节）：内页标题必须是完整结论句，不能是"栏目名"
            if s.get("slide_type") in INNER_TYPES:
                t_text = ""
                for el in (s.get("elements") or []):
                    if isinstance(el, dict) and el.get("role") == "title":
                        t_text = str(el.get("text") or "").strip()
                        break
                bl = {str(x) for x in (nar_cfg.get("title_blacklist") or [])}
                min_chars = int(nar_cfg.get("action_title_min_chars", 8))
                if t_text and (t_text in bl or len(t_text) < min_chars):
                    rep.warn(f"{spath}.elements", f"标题像栏目名而不是结论句（{t_text[:16]!r}）：改成一句可执行的判断")
                cliches = [str(x) for x in (nar_cfg.get("cliche_title_patterns") or []) if str(x)]
                cliche_ok = [str(x) for x in (nar_cfg.get("cliche_exempt_patterns") or []) if str(x)]
                hit = next((p for p in cliches if p in t_text), "")
                if hit and any(x in t_text for x in cliche_ok):
                    rep.info(f"{spath}.elements", f"标题命中「{hit}」但含党建/政务正式政治表达：按规格 v8.6 不判为短剧金句")
                elif hit:
                    rep.warn(f"{spath}.elements", f"标题像短剧式金句（命中“{hit}”）：改成正式结论式表达，不要文学化/情绪化（规格 v8.4 红线第 21 条）")
                # 密度模式：vivid 的元素下限（红线 20：不得自动极简）
                if dm == "vivid":
                    need = int(((cfg.get("density_modes") or {}).get("vivid") or {}) \
                               .get("min_elements_per_content_page", 6))
                    n_el = len([e for e in (s.get("elements") or []) if isinstance(e, dict)])
                    if n_el < need:
                        rep.warn(spath, f"高级耀眼版元素不足：本页 {n_el} 个 < 下限 {need}；"
                                        f"不得自动极简，也不得为凑数加无关元素")
                    # v8.0 耀眼版硬指标（逐条可核）
                    vivid = (cfg.get("density_modes") or {}).get("vivid") or {}
                    els = [e for e in (s.get("elements") or []) if isinstance(e, dict)]
                    _ds_cfg = cfg.get("decoration_sets") or {}
                    # v8.9 创意度开关：装饰组上下限按档位取（缺省/非法档位回落 off，与既有行为一致）
                    _cl = cfg.get("creative_level") or {}
                    _lv = str(db.get("creative_level") or _cl.get("default") or "off")
                    if _lv not in (_cl.get("levels") or {}):
                        rep.warn("design_brief.creative_level",
                                 f"创意度档位非法：{_lv!r}（可选 off / conservative / balanced / expressive），已按 off 处理")
                        _lv = "off"
                    _ds_range = (((_cl.get("levels") or {}).get(_lv) or {}).get("sets_per_content_page")) \
                        or (_ds_cfg.get("sets_per_content_page") or [2, 3])
                    _lo_ds = int(((_ds_range or [2, 3]) or [2, 3])[0])
                    _tgt = (cfg.get("gsl_alignment") or {}).get("targets") or {}
                    _n_ds = len([e for e in els if isinstance(e, dict) and e.get("type") == "decoration_set"])
                    if _n_ds < _lo_ds:
                        rep.warn(spath, f"装饰组偏少：本页 {_n_ds} 组 < 下限 {_lo_ds}；"
                                        f"国赛对齐目标 形/页 ≥{_tgt.get('content_shapes_per_page_min', 55)}"
                                        f"（口径见 references/gsl-alignment.md）")
                    _hi_ds = int(((_ds_range or [2, 3]) or [2, 3])[1])
                    if _n_ds > _hi_ds:
                        rep.warn(spath, f"装饰组过多：本页 {_n_ds} 组 > 上限 {_hi_ds}；装饰组承担版面框架，不应堆叠过度")

                    _cards = [e for e in els if isinstance(e, dict) and e.get("type") == "shape"
                              and e.get("shape_type") in ("rect", "roundRect")
                              and (e.get("role") or "") not in ("decoration", "title", "subtitle")]
                    if len(_cards) >= 3 and not (vs.get("card_style") or {}):
                        rep.warn(spath, f"本页 {len(_cards)} 个卡片类形状，但所选视觉系统未定义 card_style"
                                        f"（半透明底 / 细描边 / 图标位 / 标题条）：卡片观感会与目标案例库有差距"
                                        f"（见 references/gsl-alignment.md 第七节）")
                    _ds_ids = [str(e.get("set_id") or e.get("set") or "") for e in els
                               if isinstance(e, dict) and e.get("type") == "decoration_set"]
                    _nav_sidebar = str(db.get("navigation_mode") or "") == "sidebar"
                    _conflict = [x for x in ("left-rail-geometry", "section-rail") if x in _ds_ids]
                    if _conflict and _nav_sidebar:
                        rep.warn(spath, f"左栏装饰组（{'、'.join(_conflict)}）与 sidebar 导航冲突：左栏已被导航占用，请改用 right-rail-ruler / top-rule-band / bottom-rule-band / corner-ticks，或把 design_brief.navigation_mode 改为 top")
                    dec = [e for e in els if e.get("role") == "decoration" and e.get("type") != "decoration_set"]
                    if n_el and len(dec) / n_el > float(vivid.get("decoration_ratio_max", 0.333)) + 0.007:
                        rep.warn(spath, f"耀眼版纯装饰占比过高：{len(dec)}/{n_el} 超过元素总数三分之一，"
                                        f"纯装饰性线条/边框/图标不得超限")
                    if not dec and not _n_ds:
                        rep.warn(spath, "耀眼版缺少装饰层：每页至少要有标题装饰线或装饰元素（L2）")
                    if not any((e.get("font_pt") or 0) >= 36 for e in els if e.get("type") == "text"):
                        rep.warn(spath, "耀眼版缺少大字号数据：每页至少一个 36–60pt 的大字元素作为视觉焦点")
                    imgs = [e for e in els if e.get("type") == "image"]
                    n_img = len(imgs) + (1 if s.get("image_required") else 0)
                    lo, hi = (vivid.get("images_per_content_page") or [1, 2])[:2]
                    if n_img < lo:
                        rep.warn(spath, "耀眼版每页应有 1–2 张图片（产品/场景/人物/数据图），不能全是纯文字页")
                    elif n_img > hi:
                        rep.warn(spath, f"本页图片 {n_img} 张 > 上限 {hi}，耀眼版要求每页 1–2 张")
                    if lt not in ("sidebar-nav", "data-dashboard", "four-grid"):
                        rep.warn(spath, f"耀眼版内页需有篇章导航标签栏：当前版式 {lt} 不含导航，"
                                        f"建议改用 sidebar-nav / data-dashboard / four-grid")

            notes = str(s.get("notes", "") or "").strip()
            if not notes:
                rep.error(f"{spath}.notes", "缺少讲者备注（红线第 14 条：每页必须有 notes）")
            elif len(notes) < 20:
                rep.warn(f"{spath}.notes", f"讲者备注过短（{len(notes)} 字），建议写清主张/卡片理由/素材/讲述提示")

            # 正文语气（规格 v8.6 红线第 22 条：禁止 AI 味）
            bs = cfg.get("body_style") or {}
            if bs:
                texts = []
                for el0 in (s.get("elements") or []):
                    if not isinstance(el0, dict):
                        continue
                    if el0.get("type") == "text" and isinstance(el0.get("text"), str):
                        texts.append(el0["text"])
                    tb = el0.get("table")
                    if isinstance(tb, dict):
                        for row in (tb.get("rows") or []):
                            if isinstance(row, list):
                                texts.extend(str(c) for c in row)
                blend = " ".join(texts)
                if blend.strip():
                    ctx = " ".join([str(intent.get("deck_title") or ""), str(intent.get("communication_goal") or ""),
                                    str(intent.get("audience") or ""), " ".join(str(x) for x in (sections or []))])
                    exempt = any(str(k) for k in (bs.get("context_exempt_keywords") or []) if str(k) and str(k) in ctx)
                    for w in (bs.get("ai_flavor_patterns") or []):
                        if str(w) and str(w) in blend:
                            rep.warn(spath, f"正文有 AI 味用语「{w}」（小红书/口语化表达）：改成正式、朴实的项目汇报表述（红线第 22 条）")
                    esc = [str(w) for w in (bs.get("escalation_patterns") or []) if str(w) and str(w) in blend]
                    if esc and exempt and bool(bs.get("escalation_exempt_in_context", True)):
                        rep.info(spath, f"升华式表述（{'、'.join(esc)}）按党建/政务/乡村振兴语境视为规范结尾（红线第 22 条）")
                    elif len(esc) >= int(bs.get("escalation_per_page_warn", 2)):
                        rep.warn(spath, f"整页有 {len(esc)} 处升华式表述（{'、'.join(esc)}）：商业/科技类项目不要每段结尾都空泛升华（红线第 22 条）")
                    elif esc:
                        rep.info(spath, f"升华式表述「{esc[0]}」：正式汇报里克制使用（红线第 22 条）")
                    hol = [str(w) for w in (bs.get("hollow_word_patterns") or []) if str(w) and str(w) in blend]
                    if hol and not exempt:
                        rep.warn(spath, f"正文空泛动词（{'、'.join(hol)}）：科技/商业类项目避免空泛使用；"
                                        f"党建/政务/乡村振兴语境可在 brief_intent 里体现以豁免（红线第 22 条）")
                    elif hol:
                        rep.info(spath, f"本页空泛动词（{'、'.join(hol)}）按党建/政务/乡村振兴语境保留（红线第 22 条）")
                    segs = [x.strip() for x in blend.replace("！", "。").replace("？", "。")
                            .replace("!", "。").replace("?", "。").split("。") if x.strip()]
                    if len(segs) >= int(bs.get("fragmented_min_segments", 4)) and \
                            sum(len(x) for x in segs) / len(segs) < float(bs.get("fragmented_avg_chars", 10)):
                        rep.info(spath, "正文断句偏碎（句子平均不足 10 字）：合并成完整句，避免小红书式短句堆叠（红线第 22 条）")
            # v8.7 超大字号目标：封面 / 目录 / 章节 / 结尾页在耀眼版下应有 ≥187pt 的标题
            _dm2 = str((db.get("density_mode") or ""))
            if _dm2 == "vivid" and stype in ("cover", "section_divider", "closing"):
                _needpt = float(((cfg.get("gsl_alignment") or {}).get("targets") or {}).get("cover_section_max_font_pt_min", 187))
                _mxpt = max([float(e.get("font_pt") or 0) for e in (s.get("elements") or [])
                             if isinstance(e, dict) and e.get("type") == "text"] or [0])
                if _mxpt < _needpt:
                    rep.warn(spath, f"封面 / 章节 / 结尾页缺少超大字号：本页最大字号 {_mxpt:g}pt < 国赛对齐目标 {_needpt:g}pt"
                                    f"（层级见 config.fonts.display_size）")
            # v9.0.2 模板校验兜底：元素量与常见布局区间极端偏离时提示退回最近布局
            _lfp = cfg.get("layout_fallback") or {}
            if _lfp.get("enabled", True):
                _lib = layout_patterns()
                _same = [p for p in _lib if p.get("role") == stype and p.get("shape_range")]
                if _same:
                    _fac = float(_lfp.get("shape_factor", 3.0))
                    _hi = max(float(p["shape_range"][1]) for p in _same) / _fac
                    _lo = min(float(p["shape_range"][0]) for p in _same) / _fac
                    _nel = len([e for e in (s.get("elements") or []) if isinstance(e, dict)])
                    _cid = cand.get("candidate_id")
                    if _hi > 0 and _nel > _hi * float(_lfp.get("extreme_over", 2.0)):
                        rep.warn(spath, f"布局兜底：本页 {_nel} 个元素远超该角色常见上限 {round(_hi)} 个——"
                                        f"建议改用更简布局；可用 python scripts/check_layout_similarity.py --plan "
                                        f"<计划> --candidate {_cid} --fix 退回最接近布局")
                    elif _lo > 0 and _nel < _lo * float(_lfp.get("extreme_under", 0.3)):
                        rep.warn(spath, f"布局兜底：本页仅 {_nel} 个元素，低于该角色常见下限 {round(_lo)} 个——"
                                        f"内容可能过空，建议增加模块或换更简布局")
            # v9.0.2 视觉母题：装饰元素只能用登记的母题，且同页母题面积 <= 页面 1/5
            _vm_list = (db.get("visual_motifs") if isinstance(db, dict) else None) or []
            _vm_ok = {str(m.get("name")) for m in _vm_list if isinstance(m, dict) and str(m.get("name") or "").strip()}
            _vm_used = []
            for _el in (s.get("elements") or []):
                if not isinstance(_el, dict):
                    continue
                _mt = str(_el.get("motif") or "").strip()
                if not _mt:
                    continue
                if _vm_ok and _mt not in _vm_ok:
                    rep.error(f"{spath}.elements.motif",
                              f"母题 {_mt!r} 不在 design_brief.visual_motifs 名单内：{sorted(_vm_ok)}")
                _zr = _el.get("z_index")
                _is_dec = str(_el.get("role") or "") == "decoration" or (
                    isinstance(_zr, (int, float)) and not isinstance(_zr, bool) and 10 <= float(_zr) < 20)
                if not _is_dec:
                    rep.info(f"{spath}.elements.motif",
                             f"母题 {_mt!r} 标在非装饰元素上：母题只约束装饰元素，内容元素不受限")
                _vm_used.append(_el)
            if _vm_used:
                _cv = cfg.get("canvas") or {}
                _pa = float(_cv.get("width_in") or 13.333) * float(_cv.get("height_in") or 7.5)
                _varea = sum(float(e.get("w_in") or e.get("w") or 0) * float(e.get("h_in") or e.get("h") or 0) for e in _vm_used)
                _vratio = _varea / _pa if _pa else 0.0
                _vmax = float(_vmc.get("max_area_ratio", 0.2))
                if _vratio > _vmax:
                    rep.error(spath,
                              f"视觉母题面积占比 {_vratio:.2f} 超过上限 {_vmax:g}（页面 1/5）：母题只做点缀，不能抢内容")
            # v8.9 导航范围：逐页声明与全局策略都要合法
            _sn = s.get("show_navigation")
            if _sn is not None and not isinstance(_sn, bool):
                rep.error(f"{spath}.show_navigation", f"show_navigation 必须是布尔值，当前 {_sn!r}")
            if isinstance(_sn, bool) and (plan.get("design_brief") or {}).get("navigation_enabled") is False and _sn is True:
                rep.warn(f"{spath}.show_navigation", "本页 show_navigation=true，但 design_brief.navigation_enabled=false（全篇关闭）：逐页声明优先，本页仍会画导航")
            _bt = str(s.get("slide_type") or "")
            if _bt in ("cover", "section_divider", "closing"):
                _has_img = bool(s.get("image_required")) or any(
                    isinstance(e, dict) and e.get("type") == "image" for e in (s.get("elements") or []))
                if not _has_img:
                    rep.warn(spath, f"背景禁令（v9.0）：{_bt} 页没有配图/背景图，会退化为纯色平底——"
                                    f"规格要求背景必须有渐变、纹理或淡纹样（做法见 references/visual-system.md）")
            sec = s.get("section_name")
            if stype in INNER_TYPES:
                if not sec:
                    rep.error(f"{spath}.section_name", "内页必须填 section_name（导航高亮依据）")
                elif sec not in sections:
                    rep.error(f"{spath}.section_name", f"章节 {sec!r} 不在 design_brief.sections 中：{sections}")
            elif sec:
                rep.warn(f"{spath}.section_name", f"{stype} 页不应有导航章节（当前 {sec!r}）")

            if stype == "section_divider":
                sn = s.get("section_number")
                if sn is None:
                    rep.warn(f"{spath}.section_number", "章节过渡页缺少 section_number：无法生成超大半透明章节编号（v5.5 验收项）")
                elif not isinstance(sn, int) or isinstance(sn, bool) or not (1 <= sn <= 99):
                    rep.error(f"{spath}.section_number", f"section_number 必须是 1–99 的整数，当前 {sn!r}")

            need = s.get("image_required")
            if not isinstance(need, bool):
                rep.error(f"{spath}.image_required", f"必须是布尔值，当前 {need!r}")
            elif need:
                img_count += 1
                it = s.get("image_type")
                if it not in IMAGE_TYPES:
                    rep.error(f"{spath}.image_type", f"非法或缺失：{it!r}，应为 {IMAGE_TYPES}")
                if not str(s.get("image_prompt", "") or "").strip():
                    rep.error(f"{spath}.image_prompt", "image_required=true 时必须提供 image_prompt")
                if stype == "data_chart":
                    rep.error(f"{spath}.image_required", "数据图表页不得配图（用原生图表）")
                if s.get("photo_source") and not isinstance(s.get("photo_source"), dict):
                    rep.error(f"{spath}.photo_source", "photo_source 必须是对象（provider/page_url/author/license）")
            if stype in ("cover", "section_divider") and need is False:
                rep.warn(f"{spath}.image_required", f"{stype} 通常需要配图（生图不可用时才降级）")

            for ei, ef in enumerate(s.get("effects") or []):
                epath = f"{spath}.effects[{ei}]"
                effect_count += 1
                if not ef.get("template"):
                    rep.error(epath, "特效缺少 template")
                ez = ef.get("z_index", 12)
                if not isinstance(ez, int) or isinstance(ez, bool) or not (10 <= ez <= 19):
                    rep.warn(epath, f"特效 z_index={ez!r} 应落在装饰层 L2（10–19），默认 12")
                if not ef.get("on_fail"):
                    rep.warn(epath, "特效未声明 on_fail 降级策略")

            # v9.0.3 封面强制 AI 书法（用户 2026-11-08 指定）：缺图必须 error，不许降级为系统字
            _ct = cfg.get("cover_title") or {}
            if stype == "cover" and _ct.get("enforced"):
                _els = [e for e in (s.get("elements") or []) if isinstance(e, dict)]
                _has_callig = any(
                    (e.get("type") == "image" or e.get("type") == "effect")
                    and any(k in str(e.get("template") or e.get("image_path") or e.get("effect_path") or "").lower()
                            for k in ("calligraphy", "shufa", "书法"))
                    for e in _els)
                if not _has_callig:
                    rep.error(spath + ".cover_calligraphy",
                              "封面强制 AI 书法体（cover_title.enforced=true）：本页未找到承载主标的书法 PNG "
                              "（image / effect 元素需带 calligraphy/书法 路径或模板）。"
                              "请先用生图插件生成透明底书法图再校验，禁止用系统字体主标顶替。")
                else:
                    for e in _els:
                        if (e.get("type") in ("image", "effect")) and any(
                                k in str(e.get("template") or e.get("image_path") or e.get("effect_path") or "").lower()
                                for k in ("calligraphy", "shufa", "书法")):
                            _ip = e.get("image_path") or e.get("effect_path")
                            if _ip and not (ROOT / str(_ip)).exists():
                                rep.error(spath + ".cover_calligraphy",
                                          f"封面书法图文件不存在：{_ip}（先跑 generate_effects.js --fill 回填）")
            validate_elements(spath, s.get("elements"), cfg, vs, assets["icons"], assets["layout_templates"].get(lt), rep, stype, assets["decoration_sets"], (plan.get("components") or {}))
            validate_grid_focus_icons(spath, s, cfg, vs, rep)
            els = s.get("elements")
            if isinstance(els, list):
                for e in els:
                    if isinstance(e, dict):
                        if e.get("type") == "table":
                            stats["tables"] += 1
                        if e.get("type") == "chart":
                            stats["charts"] += 1
                if not els:
                    rep.info(spath, "elements 为空，构建时将按 claim 生成标题")
            sig.append(f"{stype}:{lt}:{card}")
            stats["slides"] += 1
            stats["effects"] += effect_count
            effect_count = 0
        stats["images"] += img_count
        sigs.append(tuple(sig))

        if img_count > max_images:
            rep.error(cpath, f"生图张数超预算：{img_count} > {max_images}")
        if len(slides) and img_count / len(slides) > max_ratio:
            rep.error(cpath, f"生图占比超上限：{img_count}/{len(slides)} > {max_ratio}")
        if img_count < min_images:
            rep.warn(cpath, f"生图张数偏少：{img_count} < 建议下限 {min_images}")
        if stats["effects"] > max_effects:
            rep.error(cpath, f"特效数量超预算：{stats['effects']} > {max_effects}")

    if len(sigs) == 2 and sigs[0] == sigs[1]:
        rep.error("candidates", "A/B 两套方案的 (slide_type, layout_template, card_used) 序列完全相同，必须给出结构不同的两套方案")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="校验页面计划与知识库/资产引用")
    ap.add_argument("plan")
    ap.add_argument("--knowledge", default=str(DEFAULT_KNOWLEDGE))
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    rep = Reporter()
    plan_path = Path(args.plan)
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAIL] 无法读取页面计划：{exc}")
        return 2
    if not isinstance(plan, dict):
        print("[FAIL] 页面计划顶层必须是对象")
        return 2

    cards = scan_cards(Path(args.knowledge), rep)
    assets = load_assets(cfg, rep)
    stats = validate_plan(plan, cards, cfg, assets, rep)

    print("=" * 66)
    print(f"页面计划校验：{plan_path}")
    print(f"卡片 {len(cards)} 张｜视觉系统 {len(assets['visual_systems'])} 套｜布局模板 {len(assets['layout_templates'])} 个｜图标 {len(assets['icons'].get('icons', {}))} 个｜装饰组 {len(assets['decoration_sets'])} 套")
    print(f"统计：页数合计 {stats['slides']}｜生图 {stats['images']} 张｜特效 {stats['effects']} 处｜原生图表 {stats['charts']} 个｜原生表格 {stats['tables']} 个")
    print("=" * 66)
    for level, items in (("ERROR", rep.errors), ("WARN", rep.warnings), ("INFO", rep.infos)):
        if items:
            print(f"\n[{level}] 共 {len(items)} 项")
            for it in items:
                print(f"  - {it['path']}：{it['message']}")
    print("\n" + "-" * 66)
    print(f"结论：{'不通过（存在 error）' if rep.errors else '通过'}（error {len(rep.errors)} / warning {len(rep.warnings)} / info {len(rep.infos)}）")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = rep.dump()
        payload.update({"plan": str(plan_path), "stats": stats, "pass": not rep.errors})
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入：{out}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())