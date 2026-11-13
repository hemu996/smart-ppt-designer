# 参考库 · 视觉系统（指针目录）

规格 v8.0 的参考库结构里有 `reference_library/visual-systems/`。为避免同一批 JSON 在包内存在两份
（构建脚本只从 `config.json:visual_system.dir` 读一处），这里**不放实体文件，只做索引与指针**。

## 一、实体位置

| 内容 | 实际路径 |
|---|---|
| 视觉系统 JSON（18 套：9 内置 + 9 参考稿提取） | `assets/visual-systems/` |
| 每套的人可读风格卡片 | `assets/style-cards/` |
| 风格库索引（名称/关键词/明暗/配色/来源/置信度） | `assets/style-index.json` |

## 二、按来源分组

| 分组 | 系统名 | 来源 |
|---|---|---|
| 规格指定（4 套） | `national-brown-gold`、`tech-teal-green`、`tech-deep-blue`、`medical-tech-white` | 规格 v8.0 §4.1 素材库 v2.0；配色按样本校准（深青/深蓝两套因样本缺失未校准） |
| 早期内置（5 套） | `business-blue`、`tech-dark`、`national-style`、`humanities-warm`、`red-gold` | 前几轮迭代的人工校订系统 |
| 样本/参考稿提取（9 套） | `ref-*` | 由 `scripts/extract_style.py` 从参考稿实测提取，置信度见索引 |

## 三、怎么用

1. 检索：`python scripts/find_style.py <内容关键词>`（可加 `--mode dark|light`）；
2. 选定后写进页面计划 `design_brief.visual_system`，并在 `style_rationale` 写明理由；
3. 新参考稿提取：`python scripts/extract_style.py <参考文件> --name ref-xxx`。

**本包不设默认风格**：未指定或名字不存在时校验器报错、构建脚本直接中止，不做兜底回落。