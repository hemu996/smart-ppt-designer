# 预置完整模板（assets/template-library/）

4 套**整套风格**的模板（不是单页布局），必要时可套用保底。每套 6 页：
封面 → 章节页 → 多模块内页 → 数据页 → 四宫格 → 结尾页。

| 文件 | 模板 | 绑定视觉系统 | 适用场景 |
|---|---|---|---|
| `tech-dark-template.pptx` | 科技深蓝模板 | `tech-deep-blue` | 技术创新、智慧矿山、装备制造类项目 |
| `national-style-template.pptx` | 国潮棕金模板 | `national-brown-gold` | 文化传承、非遗、乡村振兴类 |
| `business-blue-template.pptx` | 商务浅蓝模板 | `business-blue` | 商业计划、市场分析类 |
| `humanities-warm-template.pptx` | 人文暖色模板 | `humanities-warm` | 教育、医疗、社会服务类 |

## 一、套用规则（必须遵守）

1. ✅ **可以套**：整体配色、母版结构、章节导航位置、装饰元素风格、字号梯度；
2. ❌ **不能直接抄**：
   - 不能用模板里的占位文字，必须全部替换成当前项目内容；
   - 不能用模板里的示例图片，必须重新生图或搜图；
   - 不能原样照搬布局，必须根据内容调整元素位置与数量；
3. **改的幅度**：至少替换 **70% 以上**的内容元素，不能让人一眼看出是套模板；
4. **什么时候用**：模型从零生成效果不理想时，套用模板保底。

## 二、模板内容速览

- 每套模板均为 **13.333 × 7.5 in（16:9）**、**6 页**、**每页含讲者备注**；
- 数据页含 **1 个原生图表 + 1 个原生表格**（可在 PowerPoint 里"编辑数据/改单元格"）；
- 内页为"金色竖条 + 原生图标 + 模块标题 + 正文 + 细分隔线"的开放模块结构，无遮挡风险；
- 模板中的数字与文案均为**占位示例**，套用后必须替换并核对口径。

## 三、复核方式

```bash
python scripts/detect_layout.py assets/template-library/tech-dark-template.pptx   # 期望 error 0
python scripts/validate_plan.py <你写的新计划.json> --knowledge knowledge          # 套用后按新计划校验
```

模板本身只提供版式与配色，**不提供内容**；套用后仍按 `references/evaluation-rubric.md` 自检。