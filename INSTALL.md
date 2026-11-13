# 安装与素材补充说明

> 适用：smart-ppt-designer 技能包。**装包不会缺功能，但可能缺素材**——本文说清哪些随包可用、哪些要你自己准备、怎么补。

## 一、装哪个包

| 包 | 内容 | 适合 |
|---|---|---|
| `smart-ppt-designer.zip`（完整包） | 全部内容，含参考稿原文件、样本 PPT | 首次安装、需要「参考手法提取 / 样本借鉴」类任务 |
| `smart-ppt-designer-slim.zip`（精简包） | **排除**参考稿原文件（`assets/templates/references/`）与样本 PPT（`assets/sample-ppts/*.pptx|pdf`） | 只要生成能力、想少占空间 |

两个包**同一套代码与规范**，精简包少的是"参考素材"，不影响生成、校验、模板索引等能力。

安装：解压到 DSH 的技能目录（`...\data\skills\user\smart-ppt-designer\`），或解压到任意位置后在技能加载处指向该目录。

## 二、开箱即有能力

- **规范**：`references/`（工作流、设计规范确认、视觉系统、卡片/版式、叙事、验收清单等）
- **脚本**：`scripts/`（材料解析、计划校验、布局接近度、构建、检测、评分、素材检索、用户模板索引、素材体检）
- **素材库**：视觉系统、设计卡片、版式模板、装饰组、图标库、特效模板、常见布局特征库
- **知识库**：`knowledge/`（参考稿实测台账、失效案例、目标案例、个人风格库）
- **用户模板索引**：`assets/user-templates/`（**只有索引**，见第三节）

## 三、需要你自己准备的素材

| 素材 | 随包情况 | 缺了会怎样 | 怎么补 |
|---|---|---|---|
| **用户模板原文件**（95 份 / 7.3 GB） | ❌ 不进包，只随包分发索引 `assets/user-templates/index.json` | 「模板填充模式」搜得到、但读不到原文件 | ① 把模板放回原目录；② 或放到新目录后跑：`python scripts/index_user_templates.py --source "<你的模板目录>"` |
| **随附字体**（84 个） | ❌ 不进包，只登记在 `assets/user-templates/fonts-index.json` | 不影响功能；只是生成稿用不到这些字体 | 需要时**自行确认授权**后安装；不用可忽略 |
| **参考稿原文件**（13 份） | ⚠️ 仅完整包含有 | 「参考手法提取 / 对齐口径」类任务样本变少 | 用完整包覆盖安装 |
| **样本 PPT**（9 份 pptx/pdf） | ⚠️ 仅完整包含有 | 「参考样本借鉴」类任务样本变少 | 用完整包覆盖安装 |

> 表格里的判断不是靠猜：`scripts/check_assets.py` 会逐项实测并给出上面这些补充命令。

## 四、一条命令体检

```bash
python scripts/check_assets.py           # 体检并打印补充指引（只提醒，不阻断，退出码 0）
python scripts/check_assets.py --strict  # 包本体缺失等情况返回退出码 1（供脚本/CI 用）
python scripts/check_assets.py --json out.json
```

输出示例（齐备）：

```
[OK]   包本体          SKILL.md 在｜style-index.json 在
[OK]   用户模板原文件      索引 95 份，本机全部就位
[OK]   随附字体         清单 84 个，本机全部在
[OK]   参考稿原文件       assets/templates/references 下 13 个文件
[OK]   样本 PPT        assets/sample-ppts/ 下 9 个 pptx/pdf
素材齐备，可直接使用。
```

缺失时会单独列出「需要补充的项」与可执行命令，例如：

```
[提醒] 用户模板原文件      索引 95 份，本机找到 90 份，缺 5 份
  · 用户模板原文件：把模板放回原目录（D:\...），或把模板放到新目录后跑：
    python scripts/index_user_templates.py --source "<你的模板目录>"
```

## 五、目录约定（素材放哪）

| 素材 | 目录 |
|---|---|
| 用户模板原文件 | 任意目录（建议固定），由 `index_user_templates.py --source` 指定并写入索引 |
| 参考稿原文件 | `assets/templates/references/` |
| 新参考稿（要做手法提取） | `assets/sample-ppts/` 并登记后跑 `scripts/analyze_reference.py` |
| 个人满意的风格 | `assets/personal-styles/` |

## 六、常见问题

**Q：拷给别人后提示模板缺失，是我装坏了吗？**
不是。模板原文件 7.3 GB，按设计不进包，只随包分发索引。按第四节提示补充即可，或让使用者用「自由生成模式」——不依赖模板库。

**Q：精简包到底能不能用？**
能。它只少了参考素材，生成、校验、模板索引、体检等能力都在。

**Q：升级技能包会不会弄丢我的素材？**
不会。模板原文件与字体都在**包外**（你自己的目录），升级只覆盖包内规范与脚本；用完整包覆盖安装时会带入参考原文件与样本（属正常）。

**Q：索引会不会过期？**
素材目录变动后重跑一次 `python scripts/index_user_templates.py` 即可刷新；索引只是风格信息与路径，不复制原文件。