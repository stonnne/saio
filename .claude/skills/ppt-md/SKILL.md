---
name: ppt-md
description: Use when the user wants to turn an existing document (Markdown or LaTeX) into presentation slides with speaker notes, generate a ppt-md slide draft, make a 讲稿/talk deck from a paper or report, or control slide count and note detail by target talk duration and language.
---

# ppt-md：文档 → 带讲稿的幻灯片草稿

把已有的 `.md` / `.tex` 文档转成 **ppt-md**——一页一节、带版式、图片与讲稿的中间 Markdown，可人工审阅后交 `/document` 渲染为 `PPTX`。

格式定义在同目录的 `template.md`，本 skill 只负责**工作流**，不重复模板内容。

## 何时用本 skill

- 用户已有论文 / 报告 / 笔记（md 或 tex），要据此做汇报、答辩、组会幻灯片。
- 用户要"讲稿 / talk / 逐字稿"形式的演示草稿。
- 用户按时长或受众控制内容密度与讲稿详略。

若用户**只**要直接生成 `PPTX` 文件而不需要中间审阅，可先用本 skill 出 ppt-md，再转 `/document`；纯 Office 排版细节归 `/document`。

## 开工前必须确认三件事

| 参数 | 取值 | 缺省处理 |
|------|------|---------|
| **语言** | 中文 / 英文 | 用户未说时**主动询问**，不要默认 |
| **目标时长** | 分钟数 | 据此推导页数与讲稿等级（见模板 §1）；未给则问，或默认 L2 标准 |
| **受众/场景** | 组会 / 答辩 / 评审 / 录课 | 影响正式度与讲稿口吻 |

时长 → 页数 → 讲稿丰富度的换算表见同目录 `template.md` §1。用户显式指定丰富度时以用户为准。

## 工作流（由大及小）

1. **读源文档**：解析章节结构、图、公式、文献。图片记录原始路径与图号；公式保留 LaTeX 文本。
2. **确认参数**：语言、时长、受众（见上表）。据时长推导建议页数与讲稿等级 L1/L2/L3。
3. **搭框架**：先列整体大纲与各章节目录页，跟用户对齐后再细化。一页一个核心信息，避免"一页讲不完"。
4. **排每页要点**：每页定标题、版式（单栏/两栏/表格/大图）、要点（短、动词开头）、图片位置与图注、需要的公式与文献。
5. **写讲稿**：按目标时长对应的等级写讲稿，语言与要点一致；过渡页标示当前章节。
6. **落盘**：按模板写 ppt-md 到 `workspace/<name>/`，如 `workspace/<name>/talk.ppt-md.md`。
7. **（可选）渲染**：需要可演示文件时按下方映射用 `/document`（python-pptx）渲染 `PPTX`，并 `scholaraio document inspect` 检查图片溢出与文字超框。

## 图片处理

- 一页 ≤ 1–2 张主图；多图拆页或拼图。
- 来源图复制/链接到 `workspace/_system/figures/`，每张标注**位置 + 相对宽度 + 图注 + 来源图号**。
- 公式优先转回 `$...$` 文本，不要当图片塞入。
- 详见 `template.md` §3。

## 渲染：ppt-md → PPTX（python-pptx）

渲染走 `/document` 的 python-pptx 路线（不要用 `scholaraio export docx` 那类纯 Markdown 转换）。逐页解析 ppt-md 字段，按下表映射建脚本。默认 16:9：`prs.slide_width = Inches(13.333)`、`slide_height = Inches(7.5)`。

| ppt-md 字段 | python-pptx 实现 |
|------------|------------------|
| 整页 | 多数页用空白版式 `prs.slide_layouts[6]`，手动摆放；纯文字单栏页可用 `slide_layouts[1]` |
| `**标题：**` | 顶部 `add_textbox`，加粗、≈28–32pt |
| `**版式：** 单栏` | 标题下一个全宽 `add_textbox`，bullets 写入 `text_frame` |
| `**左侧：** / **右侧：**` | 两个 `add_textbox`，各占约半宽（左 `Inches(0.5)`、右 `Inches(6.9)`，宽 `Inches(6)`） |
| `**居中：**` | 单个居中容器；大图页图 `PP_ALIGN.CENTER` |
| bullet 列表 / 缩进 | `tf.add_paragraph()` + `p.level = 0/1/2` |
| `![cap](path) <!-- 宽≈45% -->` | `add_picture(path, left, top, width=Inches(0.45*13.333))`；位置按所属分区（左/右/居中）定 left/top |
| Markdown 表格 | `add_table(rows, cols, left, top, width, height)`，逐格 `table.cell(r,c).text` |
| `$...$` / `$$...$$` | python-pptx **不排版 LaTeX**：简单式可作纯文本；复杂式用 matplotlib mathtext 预渲染成 PNG 再 `add_picture`（见下文「公式」） |
| `<div class="ref">…</div>` | 底部小字 `add_textbox`，≈10pt 灰色，置于页脚区 |
| `**讲稿：** > …` | **写入备注页**：`slide.notes_slide.notes_text_frame.text = 讲稿`（每页都要带，这是 ppt-md 的核心，不可丢） |

**字体**：中文用**黑体**（SimHei），英文/数字用 **Arial**。`run.font.name` 只设西文字体；中文必须额外设东亚字体，否则回落系统默认。封装一个 helper，每个 run 都过一遍：

```python
from pptx.oxml.ns import qn
from pptx.util import Pt

def set_font(run, size=18, bold=False):
    run.font.size = Pt(size); run.font.bold = bold
    run.font.name = "Arial"                       # 西文 / 数字
    rPr = run.font._rPr                            # 东亚字体（中文黑体）
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {}); rPr.append(ea)
    ea.set('typeface', '黑体')
```

标题等加粗大字同样调用 `set_font(run, size=30, bold=True)`。

**公式**：python-pptx 无公式引擎。行内简单符号保留为文本；独立或复杂公式用

```python
import matplotlib.pyplot as plt
fig = plt.figure(); fig.text(0, 0, f"${latex}$", fontsize=24)
fig.savefig("workspace/_system/figures/eqN.png", dpi=200, bbox_inches="tight", transparent=True)
```

再 `add_picture` 嵌入。

**渲染后必做**：`scholaraio document inspect <file>` 检查每页 shape 溢出、文字超框、图片尺寸；逐页确认备注（讲稿）已写入；有问题改脚本重渲染再 inspect。

## 与其他 skill 的关系

| 需求 | 路线 |
|------|------|
| 论文/报告先成文，再做 PPT | `/paper-writing` 或 `/technical-report` 出文 → 本 skill |
| 已有 md/tex，要带讲稿的幻灯片草稿 | 本 skill |
| 把 ppt-md 渲染成 PPTX 文件并检查布局 | `/document` |
| Nature 风格 paper-to-PPT | `/nature-workflow` |
| 海报而非幻灯片 | `/poster` |

## 原则

- **先框架后细节**：整体大纲对齐后再写每页与讲稿。
- **一页一意**：内容超出就拆页，宁少勿挤。
- **图为主、文为辅**：要点简短，细读内容转入讲稿。
- **时长驱动详略**：讲稿丰富度由目标时长推导，用户可覆盖。
- **诚实分工**：本 skill 产出 ppt-md 草稿；可演示文件由 `/document` 渲染，不假装内置 PPTX 后端。

## 示例

用户说："把这篇 tex 论文做成 12 分钟答辩 PPT，英文，要详细讲稿"
→ 确认语言=英文、时长=12min（→ L2，约 8 页）、受众=答辩；解析 tex 结构与图 → 搭框架对齐 → 写每页要点与英文讲稿 → 输出 `workspace/<name>/talk.ppt-md.md` → 需要文件再转 `/document` 出 PPTX 并 inspect。

用户说："据这个 md 笔记做组会汇报，5 分钟就行"
→ 确认中文、5min（→ L1 提示词、约 4 页）→ 框架从简，每页 1–2 个提词式讲稿 → 落盘 ppt-md。
