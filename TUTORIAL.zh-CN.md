# KnowledgePalace 教程

[English](TUTORIAL.md) | 中文

从零开始，一路做到写出一节论文。每个教程都告诉你：输入什么、系统会做
什么、你要确认什么、文件最后落在哪。概念和规则去看
[GUIDE.zh-CN.md](GUIDE.zh-CN.md)，这里只管动手。

约定：

- `$`——你自己在终端里敲的命令。
- `>`——你在仓库根目录对 Claude Code（或 Codex）说的话。`/palace`
  命令和普通自然语言都行。
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

体检一下（只读，不写文件，不联网）：

```bash
$ python3 -m knowledge_palace.tools.doctor
```

正常情况：四个目录都能找到、互不相同，各项契约完整。第一次收论文之前
看到「index: absent (rebuildable)」是正常的——索引还没建而已。

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
2. **搜论文。** 通过 OpenAlex（备用 Crossref / Semantic Scholar）按
   主题搜，再从综述的参考文献里挖，按默认配比凑候选：老经典 ≥20%、
   综述 2–4 篇、每代方法 ≥3 篇、近三年 ≥25%。
3. **给你一张候选表**（约 30 行：标题 / 年份 / 期刊 / 引用数 / 分类）。
   你**勾一次**就行，之后不再反复问。
4. **批量入库**，每批 5–10 篇、每批一次确认（确认里有什么，见教程 2）。

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

1. **抓元数据和引用数**，引用数带上抓取日期。
2. **查重。** 用临时 slug（`一作-年份-标题词`）和 DOI 在库里搜。真撞上
   了让你三选一：**跳过**、**深化**（往已有卡里补新论断，旧引文一个
   字不动）、**勘误**（追加带标记的更正）。
3. **提取子代理起草论文卡**：原文引句 + 出处、从局限性推出的缺口候选、
   迁移备注、建议权重档。
4. **关联子代理做对齐**：只看筛出来的 5–15 张相关卡，给出概念标签
   对齐表、新概念提案（每篇最多 5 个）、缺口关系表。
5. **一次打包确认**：卡片、索引行、新概念、缺口状态变更，全摆在一起
   让你过目。你批准，主代理才写入知识库。

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
weight: medium (IF 4.2 in 3–10)        # 权重怎么算的直接写在旁边
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
没有出处的"事实"，这个库里不存在。

---

## 教程 3——问问题

```
> /palace ask does classifier-free guidance hurt sample diversity?
```

结果只有三种，由"库里证据够不够"决定：

- **够**——给你完整回答，*每句话*都带标签：`[C:smith-2023-emergent]`
  （有论文原话，去那张卡查出处）、`[S]`（跨论文综合）、`[H:transfer-x]`
  （待验证假设）。权重摆在一起看，反对意见不会被藏起来。
- **够一半**——只回答有证据的部分，没证据的部分逐条列出来（比如
  「库里没有 FID 之外的多样性指标证据」）。
- **不够**——不硬编。给你一个**补文献方案**：根据缺口推荐种子论文和
  搜索词，深度最多 2 层、最多 50 篇候选。

你接受方案，它就跑一次正常的文献扩展（教程 4）；跑完**回到刚才的
对话**重新评估，再问一遍，缺口应该就补上了。

回答默认只在聊天里。说一句"存一下"，就会走复查 + 确认，存到
`briefs/日期-ask-xxx.md`。

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
```

每份简报先由分析子代理起草，再由审计子代理**复查**（出处能不能查到、
标签有没有越界），最多改两轮才交付。你确认后存到
`briefs/日期-视图.md`。简报只是当天的快照——过一个月再跑一次
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
2. 你给的参考文献先在库里找：找到了直接用库里那张卡；没找到就作为
   本次会话的临时来源（核实过身份，但不会自动进库）。
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
读者、目标期刊、语言、篇幅、引用格式、文风档案）和八个子目录。

然后按顺序来：

1. **登记材料。** 你的草稿、图表、数据、审稿意见放进项目材料；参考
   文献先在库里匹配。材料只供写作，永远不会变成库里的证据。
2. **冻结"写作合同"。** 问题、贡献点、章节计划、允许使用的证据清单
   （每条都带原话和出处）——冻结后打上指纹，之后每次写作都锁定这个
   指纹，AI 没法偷偷扩大证据范围。
3. **写一节：**

   ```
   > /palace write guidance-anneal-paper introduction
   ```

   写作子代理起草 → 评审子代理挑毛病 → 最多自动改两轮 → 审计子代理
   把关出处和编造。改不完的问题如实报给你，不会悄悄糊弄过去。没给
   实验数据的 Results 章节只会输出结构和占位符——**结果绝不编**。
4. **确认存档** → `sections/introduction/r001.md`。修订只追加：下次存
   是 `r002.md`，旧版本永远都在；拼装全文用保留名 `assembled`。不存
   的话内容只留在聊天里，写作区一个字不变。
5. **导出。** 先给你看完整的 pandoc 执行计划（用哪个引用格式：手动
   指定 > 项目配置 > 默认 APA；每个参数都列出来），实际跑的就是你
   看到的计划。产物进 `exports/`，不覆盖任何旧文件。没装 pandoc？
   它会直说，不会瞎凑合。

写基金申请书（`kind: proposal`）时多三道工序：申请指南先拆成带出处的
**需求矩阵**，每条没覆盖到的需求都点名；研究目标和技术方案做对齐
检查；预算、单位信息、初步结果这类"你的事实"必须来自你登记的材料，
AI 一律不代填。

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
（≥3 篇真实使用、来自 ≥2 个互不合作的团队）、该重算的临时权重、反复
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
| `doctor` 说找不到某个数据目录 | `.palace.toml` 里的路径是相对配置文件算的，跟你在哪敲命令无关——检查路径时以仓库根目录为基准 |
| 报"索引过期"/ viewer 导不出来 | 库在上次建索引后变过了：`python3 -m knowledge_palace.graph.builder --rebuild` |
| ingest 说这篇已经有了 | 这是查重在起作用——选跳过、深化（补论断）或勘误（追加更正），它不会覆盖 |
| ask 不肯回答 | 说明库里证据不够——这是特性不是 bug；接受它的补文献方案，或把问题问小一点 |
| 导出说缺 pandoc | 自己装一下；系统故意不代装软件、也不换别的转换器凑合 |
| `status` 里数字看着不对 | 数字都是现场从文件里数的——直接去库里看文件；索引和文件对不上的话，一致性检查里会列出来 |
| 想给知识库建 Git | 自己在数据目录里建；系统既不帮忙也不阻拦——这条界线是故意划的 |
