---
name: paper-assets
description: Use when a paper directory contains a supplementary or appendix PDF that still needs converting to Markdown, or when the user asks to process attachments, supplementary information, or SI files that the ingest pipeline did not handle.
---
# 论文附件转 Markdown

论文入库时 pipeline 只会把正文 PDF 转成 `paper.md`。同一目录下的**附件 PDF**（supplementary information / appendix / SI）不在自动流程内，需要单独处理。

## 何时用

论文目录下出现正文之外的 PDF，例如：

```
data/libraries/papers/<Paper>/
    <Paper>.pdf              正文，入库时已转为 paper.md
    paper.md
    images/                  paper.md 引用的图片
    supplementary.pdf        ← 附件，需要单独转
```

## 执行

```bash
scholaraio attach-asset <paper_id> <附件PDF路径> --name supplementary
```

- `--name` 决定产物名，默认取源文件名去扩展名。约定用 `supplementary`
- 产出 `<Paper>/supplementary.md`，与 `paper.md` 平级
- 图片**增量合并**进共享的 `images/`，引用重写为 `images/<file>`

先跑 `--dry-run` 确认目标路径和将要覆盖的文件；产物已存在时命令会拒绝执行，**必须由用户确认后**才加 `--force` 覆盖。

## 产物约定

与库内既有附件条目保持一致：

| 项 | 约定 |
|---|---|
| 正文 | `supplementary.md`，与 `paper.md` 同级 |
| 图片 | 合并进共享 `images/`，保留 MinerU 的哈希文件名 |
| 公式 | `$$ ... $$` 独立块 |
| 表格 | 带 `rowspan` / `colspan` 的 HTML `<table>`，不是 Markdown 表格 |

图片合并是**只增不改**的：同名同内容复用，同名不同内容退回内容哈希命名。任何情况下都不会覆盖 `paper.md` 已在引用的图片。这也是不能拿 `attach-pdf` 处理附件的原因——那条路径会整体替换 `images/`。

## 验证

转换后确认图片引用全部可解析（命令会直接报告未解析的引用数）：

- 输出中 `Merged N images` 与既有图片数一致递增
- 没有 `image references do not resolve` 警告

抽查正文开头与图表小节，确认公式和表格没有退化成乱码。

## 边界

- 当前只支持 **PDF** 附件。Office 数据文件（`.xlsx` / `.docx` / `.pptx`）尚未纳入，命令会直接拒绝
- 附件不进检索索引：命令不做 embed / index。`paper.md` 才是检索正文
- 如果要转的是正文而非附件，用 `attach-pdf`，不要用这个 skill
