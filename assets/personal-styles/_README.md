# 个人风格库（assets/personal-styles/）

规格 v8.2 验收项「**个人风格库**：满意的风格自动保存，下次直接复用」。
本目录就是它的落点：**与内置视觉系统同 schema**，放进来即可被检索、校验与构建脚本识别，无需改代码。

## 一、什么时候保存

人工终审（工作流第 12 步）里出现以下任一情况时保存：

- 用户明确说"这个风格我喜欢，下次还用"；
- 某套配色/装饰组合连续两份稿都获好评；
- 从某份参考 PPT / 图片复刻出来的风格被确认可用。

## 二、怎么保存

```bash
# 从参考稿提取 → 直接落到个人风格库
python scripts/extract_style.py <参考文件.pptx> \
  --name personal-<短名> \
  --out assets/personal-styles/personal-<短名>.json \
  --card assets/style-cards/personal-<短名>.md

# 或手工写：复制一套现有视觉系统，改 system_name（personal- 前缀）与 colors/fonts 后存入本目录
```

命名约定：`personal-<短名>`（如 `personal-tea-green-2026`），避免与内置/参考稿条目重名。

## 三、怎么复用

| 动作 | 命令 / 位置 |
|---|---|
| 检索（与内置风格一起列出） | `python scripts/find_style.py <关键词>`（个人条目标注"个人风格库"） |
| 写进页面计划 | `design_brief.visual_system = "personal-xxx"`，并写明 `style_rationale` |
| 校验 | `python scripts/validate_plan.py <plan.json> --knowledge knowledge`（本目录的 JSON 会被一起加载） |
| 构建 | `node scripts/build_pptx.js ...`（查找顺序：`assets/visual-systems/` → 本目录） |

## 四、纪律

1. **不设默认**：个人风格同样不是默认风格，仍按"检索/推导 + 写明理由"使用；
2. **不混用**：一份 PPT 只用一套视觉系统（红线第 13 条），个人风格也不例外；
3. **同 schema**：必须含 `system_name`、`colors`、`fonts`、`grid`、`layers`、`navigation` 等字段，缺 `colors` 的文件会被校验器报错；
4. **重名优先**：与内置系统同名时以本目录为准（便于用个人版本覆盖内置版本），请在 `label` 里注明"个人版"。