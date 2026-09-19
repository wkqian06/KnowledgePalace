# KnowledgePalace 教程

[English](TUTORIAL.md) | 中文

从零开始，一路做到写出一节论文。每个教程都告诉你：输入什么、系统会做
什么、你要确认什么、文件最后落在哪。概念和规则去看
[GUIDE.zh-CN.md](GUIDE.zh-CN.md)，这里只管动手。

约定：

- `$`——你自己在终端里敲的命令。
- `>`——你在仓库根目录对 Claude Code（或 Codex）说的话。`/palace`
  命令和普通自然语言都行。在 Codex 里把 `/palace` 写成 `$palace`。
- **确认**——系统写你的数据之前一定先列清单问你。你说"不"，什么都
  不会变。

---

## 教程 0——装好它（5 分钟）

需要：Python ≥ 3.9（什么都不用 pip 装）+ Claude Code 或 Codex。

```bash
$ git clone <this-repo> KnowledgePalace
$ cd KnowledgePalace

# 四个数据目录必须建在仓库外面，且互不相同
$ mkdir -p ../KnowledgePalace-vault ../KnowledgePalace-state \
           ../KnowledgePalace-sources ../KnowledgePalace-workspace

$ cp .palace.example.toml .palace.toml
```

`.palace.toml` 不进 Git，只在你本地。里面的路径相对配置文件本身解析，
默认值正好对应上面建的目录：

```toml
vault_dir = "../KnowledgePalace-vault"        # 知识库
state_dir = "../KnowledgePalace-state"        # 缓存区
source_dir = "../KnowledgePalace-sources"     # 论文全文
workspace_dir = "../KnowledgePalace-workspace" # 写作区
```

验证一下配置（只读，不写文件，不联网）：

```bash
$ python3 -m knowledge_palace.tools.config_resolver
```

正常情况：打印出四个目录的绝对路径。缺目录、路径重复或配置格式错误会
直接报出是哪一行。

建议（可选）：把知识库、缓存区、写作区做成一个你自己的 Git 仓库，方便
备份。这事系统完全不管，也不会插手。

---

## 教程 1——用 `init` 从零建库

最快攒出一个能用的库：给个主题，它去搜，你勾一次，批量入库。

```
> /palace init diffusion-model-interpretability 30
```

它会依次做：

1. **查领域。** 这个主题的领域还没注册的话，先走注册流程：要 1–2 篇
   综述（你给或它去找），据此提一棵概念树草案，你确认后写入领域和
   概念注册表。
2. **搜论文。** 通过可用的数据源或浏览工具按主题搜，再从综述的参考
   文献里挖。引用数和期刊只作背景展示，不当质量分；查询词、日期和
   入选理由都会记录。
3. **给你一张候选表**（约 30 行：标题 / 年份 / 期刊 / 引用数 / 为什么
   找到它）。你**勾一次**就行，之后不会再让你重选同一批。
4. **把选定的每篇论文入库**（见教程 2）。库里已有的直接复用，不重复收。

跑完看一眼：

```
> /palace status
```

应该能看到论文数、缺口数、各轴概念数，以及一致性检查全绿（索引行数
和文件数对得上、没有野标签）。

---

## 教程 2——收一篇论文，看懂它产出了什么

```
> /palace ingest 10.48550/arXiv.2301.00001
```

或者直接给本地 PDF（下载不到的论文它本来也会问你要文件）：

```
> /palace ingest ~/Downloads/smith-2023.pdf
```

你会看到这几步：

1. **身份比对。** 用 DOI、arXiv 号和标题在库里比对。命中就复用原卡并
   加深阅读，旧引文和出处一个字不动；预印本和正式版要核实关系再合并。
2. **取材料。** 能拿到的最好材料（本地文件、Zotero、开放获取，或浏览/
   PDF 工具）放进论文全文目录。卡片记录 `source_coverage`（手里有什么）
   和 `read_depth`（实际读了多少）——硬盘上有 PDF 不等于读过。
3. **阅读。** 按你的问题和要求的深度读：作者问题、方法、主要发现和
   边界；关键 Claim 对应到支撑它的分析或图表。
4. **起草卡片。** 原文 Claim + 出处、Argument 和 Conditions 表、可选的
   `## Analysis evidence` 表、带日期的 `## Reading notes`、概念标签和
   缺口关系（对照注册表对齐）。
5. **保存。** 走 `save_paper`：拒绝重复身份、保留每条旧 Claim、核对
   阅读深度和材料范围是否匹配、更新索引行。一批结束后重建一次索引，
   受影响的判断进 `/palace updates`。

去看看写了什么：

```bash
$ ls ../KnowledgePalace-vault/papers/
$ cat ../KnowledgePalace-vault/papers/smith-2023-emergent.md
```

论文卡长这样（挑重点）：

```markdown
---
title: ...
authors: [Smith, J., ...]
year: 2023
citations: 42
citations_date: 2026-07-17
weight: medium (IF 4.2 in 3–10)        # 书目背景，不是分数
read_depth: full                       # full | skim | abstract | metadata
source_coverage: full-text             # full-text | excerpt | abstract | metadata
domain: [diffusion-models]             # 一定带领域根标签
method: [classifier-free-guidance]
gaps:
  - gap-guidance-fidelity: supports    # 这篇论文支持解决这个缺口
local: fulltext/smith-2023-emergent.pdf   # 全文在 source_dir 里的位置
---
## Summary
（摘要可以用中文写）

## Claims
- C1 [classifier-free-guidance]: "exact verbatim sentence from the paper"
  — §4.2 [¶3] / p.6        # 原话 + 出处：第 4.2 节第 3 段，第 6 页
```

核心就一条：每个论断 = 一句原话 + 一个出处（+ 至少一个概念标签）。
没有出处的"事实"，这个库里不存在。只有摘要的论文，Claim 只能是摘要
原话，Limitations 里写明材料范围；只有元数据的记录，卡里没有 Claim。

---

## 教程 3——问问题

```
> /palace ask does classifier-free guidance hurt sample diversity?
```

它先判断问题需要什么——背景解释、论文证据、跨论文比较、暂定解释——
然后用正常的文字回答，附来源链接：

- 有论文支持的句子引用那张卡（`[C:smith-2023-emergent]`，去查出处）。
  反对意见和主流证据摆在一起。
- 综合和假设如实标明并写清依据；假设不需要先有迁移卡，解释一个概念
  也不需要先有 Claim。
- 库里没覆盖的部分明说（比如「库里没有 FID 之外的多样性指标证据」），
  不编，也不因此拒绝给出标明身份的解释。

补文献会改变答案时，它会提议去搜。你同意，它跑 `init`/`expand`
（教程 4），把你选定的论文入库，然后**接着回答同一个问题**。

回答默认只在聊天里。说"记下来"，工作定义、决策、备选解释和下一步
就进项目的 `research.md`（教程 7c）；说"存一下"则存成 `briefs/` 里的
一份简报。

---

## 教程 4——沿引用扩展文献

从库里任何一篇论文出发：

```
> /palace expand smith-2023-emergent --scope diffusion-models --depth 2 --max-new 30
```

- 沿引用关系 A→B→C 往外走，最深 2 层，攒到 30 篇库外新候选就停
  （提前搜光了就提前结束）。已经在库里的论文只记一笔引用关系，不会
  重复收。
- 每个候选都有一个决定：选 / 缓 / 拒 + 理由。默认由评审子代理来定
  （加 `--review manual` 就你亲自定）。拒绝只在当前主题范围内有效——
  换个主题这篇论文还有机会。
- 中途断了没关系，缓存区里有断点，续跑不会重复。
- 你确认一份运行记录；选中的候选接着走教程 2 的正常入库流程。扩展
  本身从不直接写卡。

---

## 教程 5——简报和跨领域发现

攒到 10 来篇之后：

```
> /palace brief onboard                 # 领域入门：地图 + 推荐阅读顺序
> /palace brief gaps                    # 开放问题排行：谁试过、卡在哪
> /palace brief map classifier-free-guidance   # 单个概念的演进和争议
> /palace brief ideas                   # 研究机会卡
> /palace brief progress guidance-schedule   # 问题演进、已有推进、剩余证据
```

每份简报从有界的研究上下文起草（`progress <主题>` 还会给出问题演进
和剩余子问题）。想要独立复查出处和来源边界时再叫审计角色。你确认后
存到 `briefs/日期-视图.md`。简报只是当天的快照——过一个月再跑一次
`brief gaps`，两份文件一对比，就能看到你这个领域的图景怎么变的。

跨领域发现需要先攒够本钱：全库 ≥15 篇、跨领域论文 ≥3 篇（第二个领域
要在收它的论文*之前*先 `/palace domain add` 注册好）。然后：

```
> /palace discover gap-guidance-fidelity
```

侦察子代理最多给 5 张迁移候选卡，每张必须有：≥2 个实质性的桥接概念
（"都用了深度学习"这种废话不算）、明确的关系类型、两边领域各自的
证据、一个可以先做的验证实验。你挑中的才会写成迁移卡。

---

## 教程 6——让它审你的想法

```
> /palace idea refine "Adapting guidance-schedule annealing from
  text-to-image diffusion to protein structure generation could reduce
  mode collapse without retraining."
```

（也可以给文件：`/palace idea refine ideas/my-idea.md`。）

1. 先跟你对齐：你的想法**新在哪个维度**（机制新？方法新？只是应用到
   新场景？……）。之后它只在你认领的维度上下结论。
2. 你给的参考文献先在库里找：找到了直接用库里那张卡；没找到就先作为
   临时项目来源。你决定采用它，就走正常入库（教程 2），之后按卡引用。
3. 程序化地逐级收窄范围：≤10 条相关线索 → ≤15 篇最接近的论文 →
   ≤30 条相关论断。不会把整个库塞给 AI。
4. 你拿到一份**想法评估**：支持的证据、反对的证据、没有证据的部分，
   三栏并列（都带权重）；最像你想法的前人工作直接点名；外加两样必给
   的东西——怎么证伪，以及最小验证实验。
5. 新颖性默认只相对**你的库**。想查库外？它会提议、但绝不擅自去查；
   你同意后跑一次有记录的检索，结论也只会说「在某年某月、某个范围内
   没查到」——从不说"全球首创"。

存档走复查 + 确认，落在 `briefs/日期-idea-xxx.md`。

---

## 教程 7——写一节论文

```
> /palace write guidance-anneal-paper
```

第一次运行会建项目（一次确认）：
`workspace/projects/guidance-anneal-paper/`，含 `project.yaml`（类型、
读者、目标期刊、语言、篇幅、引用格式、文风档案）和若干子目录。直接
给文本则不需要项目——`/palace write` 和 `/palace polish` 都接受贴进来
的段落或文件。

然后按顺序来：

1. **登记材料。** 你的草稿、图表、数据、审稿意见放进项目材料；参考
   文献先在库里匹配，库外采用的论文走入库。材料只供写作，永远不会
   变成库里的证据。
2. **论文分析。** 动笔前先在 `outline/manuscript-analysis.md` 记下：
   研究问题、核心主张与证据、全文论证和章节职责、目标读者、你的写作
   意图、规范术语、尚未解决的输入。后续任务只要它仍与稿件相符就复用，
   稿件实质变化后更新——不会因为你又要润色一次就重做。
3. **写一节：**

   ```
   > /palace write guidance-anneal-paper introduction
   ```

   先定论证和段落职责，再依据选定证据和你的材料起草；然后一次聚焦
   审核，最多自动改两轮。改不完的问题如实报给你，不会悄悄糊弄过去。
   没给实验数据的 Results 章节只会输出结构和占位符——**结果绝不编**。
   `draft intro <主题>` 就是同一条路的引言版。
4. **确认存档** → `sections/introduction/r001.md`。修订只追加：下次存
   是 `r002.md`，旧版本永远都在；拼装全文用保留名 `assembled`。不存
   的话内容只留在聊天里，写作区一个字不变。
5. **润色一段：**

   ```
   > /palace polish guidance-anneal-paper introduction "The gap has a second component ..."
   ```

   它读分析和前后文，判断问题是措辞、段落逻辑还是科学主张，只改这一
   段，并对照原文核对数字、单位、术语、引用、主张强度和边界条件。
   本节其余部分一个字不动，结果存成 `r002.md`。科学依据不足会明说，
   不会用语言修饰盖过去；需要大改结构会转给 `write`。

想让写出来的文字贴近某本期刊或某种语言风格，先用 `/palace style ingest`
收藏你喜欢的论文，攒够后 `style crystallize` 结晶成档案，写作时指定即可。

基金申请书（`kind: proposal`）走同一条路：把申请指南登记为材料，它的
要求就进论文分析；预算、单位信息、初步结果这类"你的事实"只能来自你
登记的材料。

---

## 教程 7b——判断一个方案可不可行

```
> /palace feasibility "在一个公开的蛋白质结构扩散模型上比较退火引导和恒定
  引导：每种设置采 500 个样本，指标用多样性和可设计性，一张 24 GB 显卡
  跑两周。"
```

（也可以给文件，或给一个研究笔记里已有方案的项目。）

它读方案、你登记的材料和相关 Claim，然后围绕决定性问题推理：这个设计
要区分哪些解释；变量、取样尺度和独立样本是否匹配；对照能否分开备选
解释；数据、访问权限、算力、存储、技能和时间是否真的有。你得到四选一
的结论——可执行 / 满足明确条件后可执行 / 需调整方案 / 目前无法判断——
外加决定性条件、最小验证试验及其可能结果、什么会改变这个决定。资源
只按你给的信息估算：文献里的方法可用，不代表你的数据可用。说"记下来"，
结论进项目的 `research.md`；实验本身它不会替你跑。

---

## 教程 7c——研究笔记和证据复核

```
> /palace research guidance-anneal-paper
```

显示项目的 `research.md`：学习目标、工作定义、声明了 Claim/Gap 依赖的
Synthesis 行、决策、约束，以及指向你登记材料的观察。你要求保留的讨论、
可行性结论和阅读所得都追加在这里，所以"接着上次的取样方案讨论"能恢复
当时的选择和依据。

新论文入库后索引会重建，声明依赖的证据变了的判断会变成待复核项：

```
> /palace updates
> /palace updates resolve gap:guidance-fidelity S1
```

看过证据、需要的话改综合，然后记录 `retain`、`revise` 或 `withdraw` 和
理由。记录结论本身不改科学文字；之后证据再变会重新打开这一项。

---

## 教程 8——离线浏览你的图谱

```
> /palace viewer export
```

确认输出路径（默认 `./palace-viewer.html`；必须放在四个数据目录外面，
会覆盖已有文件时它会提醒）。这一步是纯程序构建，没有 AI 参与。生成的
HTML 双击就能在浏览器打开，完全离线：左边是「领域 → 概念 → 论文/
缺口」的树，右边是节点详情。数据显示不全时会如实标注（返回多少 / 总共
多少），页面零网络请求。

用 Obsidian 的话，`/palace wiki export [<目录>]` 只重新生成带标记的汇总页；
你自己的笔记和原始卡片不动。

如果导出时报索引过期，先重建：

```bash
$ python3 -m knowledge_palace.graph.builder --rebuild
```

---

## 教程 9——日常维护

大约每收 20 篇左右（或系统主动提醒时）做次体检：

```
> /palace govern
```

它会列出一批提案，每个都附受影响文件清单：攒够票该转正的候选概念
（≥3 篇真实使用，以不同数据或分析评估独立性）、待显式刷新的临时书目档、反复
出现该注册的新词、野标签、还有人在用的废弃标签。你确认后统一执行，
并在知识库的治理日志里记一笔。注意 `govern` 从不联网——想刷新引用数
是另一条命令：

```
> /palace refresh citations all        # 先看缓存里的
> /palace refresh citations all --live # 真联网，你点头才跑
```

隔段时间，或者要依赖一份重要简报之前，做次深度复查：

```
> /palace audit                        # 全库
> /palace audit smith-2023-emergent    # 或只查指定卡片
```

审计子代理逐字核对每条引文的出处、找野标签、查溯源标签越界。它只出
报告；要改，照旧走确认流程。

---

## 常见问题

| 现象 | 怎么办 |
|---|---|
| `config_resolver` 说找不到某个数据目录 | `.palace.toml` 里的路径是相对配置文件算的，跟你在哪敲命令无关——检查路径时以仓库根目录为基准 |
| ingest 说这篇已经有了 | 这是查重在起作用——选跳过、深化（补论断）或勘误（追加更正），它不会覆盖 |
| ask 说库里某部分没证据 | 那部分会作为标明身份的背景解释或假设回答；让它去补文献，或把问题问小一点 |
| `save_paper` 拒绝保存 | 看列出的原因：身份重复（复用它点名的 slug）、改了旧引文（改成追加更正）、或阅读深度超过了手里的材料 |
| `status` 里数字看着不对 | 数字都是现场从文件里数的——直接去库里看文件；索引和文件对不上的话，一致性检查里会列出来 |
| 想给知识库建 Git | 自己在数据目录里建；系统既不帮忙也不阻拦——这条界线是故意划的 |
