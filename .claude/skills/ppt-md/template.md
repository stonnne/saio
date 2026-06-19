# ppt-md 格式模板

> **ppt-md** 是幻灯片的中间 Markdown 表示：一页一节，每页带版式、要点、图片与讲稿。
> 它由已有文档（`.md` / `.tex`）生成，可人工审阅，再交给 `/document` 渲染为 `PPTX`。
>
> 配套工作流见同目录 `SKILL.md`（`/ppt-md`）。本文件只定义**格式**。

---

## 0. 一份 ppt-md 的整体结构

每份 ppt-md 以一个元信息块开头，随后是若干以 `---` 分隔的幻灯片块。

```
# <演示标题>

<!--
meta:
  language: zh | en          # 全篇语言（由用户指定）
  duration_min: 12           # 目标时长（分钟，由用户指定）
  note_level: L1 | L2 | L3   # 讲稿丰富度，由时长推导，用户可覆盖
  audience: 组会 / 答辩 / 评审 / 录课
  source: path/to/source.md  # 来源文档
-->

---

## Slide 0 — Title（标题页）
...

---

## Slide 1 — ...
...
```

生成顺序遵循**由大及小**：先定整体框架与各章节，再定每页要点，最后写每页版式与讲稿。

---

## 1. 时长 → 页数 → 讲稿丰富度

页数与讲稿详略**不是凭感觉**，按目标时长推导，用户可覆盖。

| 目标时长 | 建议内容页数 | 讲稿等级 | 每页讲稿 |
|---------|------------|---------|---------|
| ≤ 5 min | 3–5 页 | **L1 提示词** | 1–2 个关键词或短句，仅作提词 |
| 5–15 min | 6–12 页 | **L2 标准** | 2–4 句完整讲稿，能脱稿照讲 |
| > 15 min | 12+ 页 | **L3 逐字稿** | 5+ 句，含过渡句、强调、口语化，可直接朗读 |

- **页数估算**：内容页数 ≈ 时长(min) ÷ 1.5（为标题、过渡、总结页留出余量）。
- **节奏**：平均每页 1–1.5 分钟；图重页可略久，过渡页很快带过。
- 用户若显式指定丰富度（如"讲稿详细一点"），以用户指定为准。
- 宁可一页内容少，也不要"一页讲不完"。内容超出就拆页。

---

## 2. 通用字段约定

每个幻灯片块可包含以下字段（按需取用，非全部必填）：

| 字段 | 说明 |
|------|------|
| `## Slide <ID> — <短标题>` | 块首行；`ID` 用于跨页引用（如 `M0`、`B3`） |
| `**标题：**` | 页面主标题；过渡页可省略 |
| `**版式：**` | `单栏` / `左右两栏` / `图文上下` / `表格` / `大图` 之一 |
| `**左侧：** / **右侧：** / **居中：**` | 两栏 / 居中布局的分区内容 |
| `**文字内容：**` / bullet 列表 | 页面要点，尽量短，一行一点 |
| `**图片：**` | 见 §3 图片放置 |
| 表格（标准 Markdown 表） | 见 `B3` 示例 |
| `$...$` / `$$...$$` | 行内 / 独立公式，原样保留 LaTeX |
| `<div class="ref">...</div>` | 页脚参考文献，见 §4 |
| `**讲稿：**` + `> ...` | 讲稿，引用块内书写，语言与 `meta.language` 一致 |

**要点写作**：动词开头、名词短语、避免整段文字；需要细读的段落一律删去或转入讲稿。

---

## 3. 图片放置（重点）

幻灯片以**图为主、文字为辅**。处理来源文档里的图时：

1. **路径**：来源图复制/链接到 `workspace/_system/figures/`，或沿用来源 `figures/` 目录。
2. **声明方式**：用 `**图片：**` 字段，给出**位置 + 路径 + 尺寸建议 + 图注 + 来源**。

```
**图片：**
- ![血管树示意图](workspace/_system/figures/fig2-tree.png) — 位置: 左栏, 宽度≈45%, 来源: 原文 Fig.2
```

也可在分区内直接用标准图片语法：

```
**左侧：图示**
- ![分叉点几何](figures/bifurcation.png)  <!-- 居左, 宽≈40% -->
- 分叉角 $\phi_l$, $\phi_r$ 与半径 $r$ 标注
```

**放置原则**：

- 一页**最多 1–2 张**主图；多图考虑拆页或拼图。
- 图文两栏：图占一侧（约 40–50% 宽），定义/要点占另一侧。
- 大图页：图居中放大，文字仅留一句标题 + 一句结论。
- 每张图给**一句话图注**，并标注**来源**（原文图号），便于 `/document` 渲染与核对。
- 不确定尺寸时给相对宽度（`宽≈45%`），由 `/document` 换算英寸并做溢出检查。
- 公式截图优先转回 LaTeX 文本（`$...$`），不要当图片塞入。

---

## 4. 参考文献格式

- **文内**：（Sarveswaran, et al. 2016）
- **页脚**：放在该页 `**讲稿：**` 之前，用 `ref` 容器：

```
<div class="ref">Bassingthwaighte, et al. <u><i>Circulation Research</i></u>, 1972；Sarveswaran, et al. <u><i>Scientific Reports</i></u>, 2016.</div>
```

格式：`作者, et al. <u><i>期刊名</i></u>, 年份`；多条用 `；` 分隔，末条以 `.` 结尾。

---

## 5. 版式模板示例

### 5.1 标题页

```
## Slide 0 — Title（标题页）

**标题：** <演示标题>
**副标题：** <作者 / 单位 / 日期>

**讲稿：**
> "大家好，今天我汇报的题目是……"
```

### 5.2 过渡 / 目录页（章节切换）

```
## Slide M0 — Contents（过渡页）

**文字内容：**
- ■ Introduction
- ■ **Methods**          <!-- 加粗标示当前章节 -->
- Common Notation
- Single-tree Generation: SCA
- ■ Results
- ■ Conclusion

**讲稿：**
> "Now I will walk through our methods. We start with notation and constraints, then present the three core algorithmic contributions in order."
```

### 5.3 图文两栏页（图示 + 定义）

```
## Slide M1 — Common Notation

**标题：** **Common Notation**
**版式：** 左右两栏

**左侧：图示**
- ![有向血管树](workspace/_system/figures/fig2-tree.png)  <!-- 宽≈45%, 来源 原文 Fig.2 -->
- 分叉点几何示意：$\boldsymbol{p}_p$, $\boldsymbol{p}_b$, $\boldsymbol{p}_l$, $\boldsymbol{p}_r$，$\phi_l$, $\phi_r$，$l$, $r$

**右侧：符号定义**
- Vascular network: $G = (N, E)$
- Node $n \in N$: spatial position $\boldsymbol{p}_n$
- Edge $e \in E$: $\langle i,j \rangle$，length $l_{ij} = \|\boldsymbol{p}_j - \boldsymbol{p}_i\|$
- Radius: $r_{ij}$；Node types: root / inter / bifurcation / leaf

**讲稿：**
> "We model a vascular network as a directed graph G. Each node has a spatial position, and each edge carries a length, direction, and radius. Nodes are classified as root, inter, bifurcation, or leaf — this distinction drives the growth logic later."
```

### 5.4 表格页（中文 L3 讲稿示例）

```
## Slide B3 — 计算瓶颈：高维性与逆问题代价

**标题：** 声子 BTE 的计算瓶颈
**版式：** 左右两栏

**左侧：BTE 维度分析（相空间 6D + 时间 1D）**

| 变量 | 维度 | 说明 |
|------|------|------|
| $\mathbf{r}$ | 3 | 实空间位置 |
| $\mathbf{s}$（方向） | 2 | 立体角，$\mathbf{k}$ 方向 |
| $\omega, p$ | 1 + 离散 | 频率与声子支路 |
| $t$ | 1 | 时间 |
| **合计** | **7** | **积分–微分方程** |

**右侧：传统方法困境**
- DOM / 有限体积 / DUGKS / 方差缩减 MC
- 三维器件 + 模态分辨 + 多参数扫描 → 成本爆炸
- **逆问题**（MFP 谱、热导率张量、界面热阻）须**反复正向求解**

<div class="ref">Luo and Chen. <u><i>Phys. Chem. Chem. Phys.</i></u>, 2013；Li, et al. <u><i>ASME J. Heat Mass Transfer</i></u>, 2024.</div>

**讲稿：**
> "接下来是计算瓶颈。声子 BTE 本质上是高维积分-微分方程，三维空间、方向、频率、支路和时间都要算进去。单次正向求解就可能很慢。更大的问题在逆问题，比如从 TDTR 信号反推平均自由程谱，需要反复调用正向求解器——正向已经贵，反演会把代价再放大一层。后面的 PINN、JAX-BTE 都围绕这个痛点展开。"
```

### 5.5 大图页

```
## Slide R2 — Main Result

**标题：** 生成网络与真实血管对比
**版式：** 大图

**居中：**
- ![对比图](workspace/_system/figures/fig7-compare.png)  <!-- 居中, 宽≈70%, 来源 原文 Fig.7 -->

**文字内容：**
- 形态学指标与解剖数据一致（误差 < 5%）

**讲稿：**
> "This is our main result. The generated network reproduces the branching statistics of real anatomy, with morphological metrics within five percent of the reference data."
```

### 5.6 结论页

```
## Slide C0 — Conclusion

**文字内容：**
- 提出 X 方法，解决 Y 问题
- 关键结果：Z
- 局限与未来工作：……

**讲稿：**
> "总结一下，我们提出了……，主要贡献是……，未来将进一步……。谢谢，欢迎提问。"
```

---

## 6. 双语约定

- 全篇语言由 `meta.language` 决定；**讲稿与要点同语言**。
- 中文稿中的专业术语首次出现给出英文原词，如"离散坐标法（Discrete Ordinates Method, DOM）"。
- 英文稿保持术语一致，避免中英混排。
- 公式、代码、文献作者名、期刊名不翻译。
- **字体**：中文统一用**黑体**（SimHei），英文（含数字、术语原词）统一用 **Arial**。中英混排页对中文字符应单独指定黑体，西文回落 Arial（渲染实现见 `SKILL.md`「渲染」节）。

---

## 7. 生成与渲染流程

1. 解析来源（`.md` / `.tex`）：抽取章节结构、图、公式、文献。
2. 与用户确认：**语言**、**目标时长**（→ 推导讲稿等级）、**受众**。
3. 由大及小：先列章节框架与目录页，再排每页要点，最后写版式与讲稿。
4. 按本模板写出 ppt-md 到 `workspace/<name>/`（如 `talk.ppt-md.md`）。
5. 需要可演示文件时，转 `/document`：解析每页版式/图片/表格/讲稿，渲染为 `PPTX`，并 `scholaraio document inspect` 检查溢出。

---

## 8. 质量自检清单

- [ ] 一页一个核心信息，没有"一页讲不完"的页。
- [ ] 要点简短，需细读的内容已转入讲稿或删除。
- [ ] 每页讲稿详略符合目标时长对应的等级（§1）。
- [ ] 图片有位置、尺寸建议、图注与来源；一页 ≤ 2 张主图。
- [ ] 公式为 LaTeX 文本而非截图；文献文内 + 页脚格式正确（§4）。
- [ ] 章节逻辑连贯，过渡页标示当前所在章节。
- [ ] 全篇语言一致，与 `meta.language` 相符。
- [ ] 字体统一：中文黑体、英文 Arial（含中英混排页）。