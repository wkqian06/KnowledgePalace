# KnowledgePalace 指南——架构与使用方法

[English](GUIDE.md) | 中文

这份文档讲清楚三件事：系统是怎么搭的、每类数据放在哪、每条命令怎么用。
想直接动手，看 [TUTORIAL.zh-CN.md](TUTORIAL.zh-CN.md)；想看约束 AI 的
规则原文，看 `knowledge_palace/protocol/`；查术语定义，看
[CONTEXT.md](CONTEXT.md)。

## 1. 整体架构：一个公开仓库 + 四个私有目录

KnowledgePalace 把"程序"和"数据"彻底分开。本 Git 仓库（叫 Framework）
里只有程序和规则；你的数据放在仓库外面的四个目录里：

```
┌─ Framework（本仓库，Palace 唯一会执行 Git 的地方）──────────────┐
│  协议规则 · 子代理角色定义 · 卡片模板 · Python 工具              │
└──────────────────────────────┬──────────────────────────────────┘
                     .palace.toml（本地配置，不进 Git）
                     写着四个数据目录在哪
                               │
   ┌───────────────┬───────────┴──────┬───────────────────┐
   ▼               ▼                  ▼                   ▼
 vault_dir      state_dir         source_dir         workspace_dir
 知识库          缓存区            论文全文           写作区
 （你确认过     （随时可删，      （PDF 原件，       （论文/申请书
 的知识）       删了能重建）      只进不改）         项目）
```

系统里有三类角色在干活：

1. **主代理**——就是你对话的那个 Claude Code / Codex。它按任务读取
   `knowledge_palace/workflows/` 下对应的工作流，找目录、读有界证据、
   需要时把阅读或起草交给专门角色，审核关键证据，并亲手执行每一次
   授权写入。**只有它能写。**
2. **九个可选的只读专门角色**——提取、关联、侦察、审计、分析、文风、
   扩展评审、写作、评审。用得上才调用，不是固定流水线；它们只能读文件
   和搜索，拿到的是主代理给的绝对路径和有界阅读范围，写不了任何东西。
3. **一堆确定性 Python 工具**——配置解析、身份匹配、论文卡保存、建图
   索引、刷新书目、导出 viewer 等等。这些环节没有 AI 参与，就是普通
   代码，全部只用 Python 标准库（`python3 -m pytest knowledge_palace/tests`）。

几条贯穿全局的铁律：

- 没有**原文引句 + 出处**就不算论断（Claim）；引文永不改动，勘误只能
  追加。
- **存决策、算数字**——各种计数（支持数、触发条件）每次都用 grep 现场
  数，从不把旧数字当真。
- 所有正式写入**必须先经你确认**；你拒绝，所有目录保持原样。
- Palace 的 Git 操作**只限本仓库**——绝不碰你的数据目录，哪怕你自己把
  数据目录做成了 Git 仓库。
- **联网只为当前任务**：搜集、获取全文和你要求的外部检索在各自任务
  范围内可以联网；`refresh` 只更新书目信息；`govern` 从不抓取。

## 2. 仓库里都有什么

```
KnowledgePalace/
├── CLAUDE.md / AGENTS.md      # 主代理的行为契约（两份内容完全一样）
├── PALACE.md                  # 公开规则：概念轴、权重档、各种阈值
├── CONTEXT.md                 # 术语表
├── README.md / GUIDE.md / TUTORIAL.md（+ *.zh-CN.md 中文版）
├── .palace.example.toml       # 配置模板（复制成 .palace.toml 用，不进 Git）
├── .claude/                   # Claude Code 的接入层
│   ├── skills/palace/SKILL.md    # 入口：把 /palace 命令转到共享内核
│   └── agents/palace-*.md                  # 9 个子代理的接入配置（只给读权限）
├── .agents/ + .codex/         # Codex 的接入层（结构相同）
└── knowledge_palace/          # 共享内核（跨平台，两个运行时共用）
    ├── protocol/              # 规则正文 · 命令索引 · 证据表契约 · 查询接口契约
    ├── workflows/             # 工作流：搜集 · 阅读入库 · 讨论 · 论文分析 · 写作/润色 · 可行性
    ├── agents/                # 9 份可选专门角色的定义
    ├── templates/             # 论文/缺口/迁移/文风/索引/扩展记录/项目研究笔记模板
    ├── tools/                 # 配置解析
    ├── graph/                 # 图索引：身份识别 · 建索引 · 查询接口
    ├── metadata/              # 学术数据源对接 + 缓存 + 影响力 + 书目刷新
    ├── acquisition/           # 论文全文获取（收据 · 渠道 · 入库事务 · save_paper）
    ├── expansion/             # 有上限的文献扩展
    ├── semantic/              # 论断↔概念绑定 · 证据表 · 综合更新 · 走廊
    ├── interaction/           # 预筛 · 研究上下文 · 新颖性评估 · 项目来源
    ├── workspace/             # 写作区：项目 · 材料 · 证据合同 · 写作输入 · 修订版 · 研究上下文
    └── viewer/                # 离线 HTML 图谱 · Obsidian 汇总页
```

记住一个分工：`protocol/` 规定"必须守什么"，`workflows/` 规定"一项任务
怎么跑"，`agents/` 规定"专门角色能起草什么"，Python 包实现"不需要 AI 的
那部分"，接入层只做转发——规则原文只有一份，谁也不许复制一份自己改。

## 3. 你的四个数据目录

在 `.palace.toml` 里配置，四个路径**相对于配置文件所在目录**解析（跟你
在哪个目录敲命令无关）。四个目录必须都存在、互不相同、都在仓库外面。
要不要给它们建 Git 完全随你——Palace 不看也不管。

### 3.1 `vault_dir`——知识库（一切的核心）

全是 Markdown，人能直接读；放在这里的每个字都经过你确认。

```
vault/
├── domains.md                 # 领域注册表
├── concepts.md                # 概念注册表：7 个轴，受控词表
├── papers/    INDEX.md + <一作>-<年份>-<标题词>.md     # 论文卡
├── gaps/      INDEX.md + gap-<slug>.md                 # 缺口卡
├── transfers/ transfer-<slug>.md                       # 迁移卡
├── briefs/    <日期>-<视图>.md      # 各种简报——只是快照，不算证据
├── styles/    bank/ + profiles/     # 文风特征卡和文风档案
├── expansions/<run-id>.md           # 文献扩展的运行记录
└── governance/decisions.md          # 治理日志（只追加）
```

- **论文卡**：头部是元数据（引用数带抓取日期、权重档带推导过程、7 个
  概念轴标签、和哪些缺口有关系等），正文是摘要 / 论断（原文引句 +
  出处）/ 局限与缺口 / 迁移备注。全文 PDF 不放这里，卡片里只存一个
  指向 `source_dir` 的相对路径。
- **缺口卡**：状态（开放/部分解决/有争议/被重新表述/已关闭）、一张
  关系表（哪篇论文、什么关系、什么权重、证据是哪句话）、每次改状态
  的理由（只追加）。
- **INDEX.md**：扁平索引表，用来查重和快速筛选——子代理干活时只看
  索引行加 5–15 张候选卡，从不通读全库。

### 3.2 `state_dir`——缓存区（删了不心疼）

这里的一切都能重建，删掉不丢任何知识：

```
state/
├── graph-index/       # 知识库的 JSON 快照（图索引）
├── expansion/         # 文献扩展的候选池和断点
├── acquisition/       # 下载暂存区和获取收据
├── interaction/       # 问答会话记录（可断点续聊）
├── impact/            # 各数据源抓来的影响力快照
└── workspace-drafts/  # 还没确认的写作草稿
```

### 3.3 `source_dir`——论文全文（只进不改）

`fulltext/<slug>.<ext>`。只能通过你确认过的入库流程放进来（先写临时
文件再原子改名；同一文件重复入库自动跳过，内容对不上直接拒绝）。放进
来之后谁也不许改。

### 3.4 `workspace_dir`——写作区

```
workspace/projects/<项目slug>/
├── project.yaml       # 项目信息：类型、读者、期刊、语言、引用格式……
├── research.md        # 研究笔记：问题、定义、决策、约束、观察
├── materials/         # 你提供的草稿、数据、图表、申请指南、审稿意见
├── sources/           # 项目参考文献（优先复用知识库里已有的）
├── requirements/      # 申请书的指南笔记
├── outline/           # brief.json（证据合同）· manuscript-analysis.md（论文分析）
├── sections/<章节>/rNNN.md   # 修订版，只追加；`assembled` 留给拼装全文
├── reviews/           # 评审记录
├── bibliography/
└── exports/           # 导出产物，绝不覆盖旧文件
```

注意：你放进 `materials/` 的东西只供写作用，永远不会变成知识库里的
证据——这是 schema 层面写死的。

## 4. 数据是怎么组织的

### 4.1 三层身份：Work → Manifestation → Claim

- **Work**：一项研究贡献本身，不管它发在哪、有几个版本。
- **Manifestation**：某个具体版本（arXiv v2、期刊正式版）。
- **Claim（论断）**：从某个版本里摘出来的一句原话 + 出处，摘出来就
  不可变。

身份识别按 DOI > OpenAlex ID > arXiv ID > 标题哈希 的顺序，防止同一篇
论文收两遍。碰到疑似重复（ID 撞了、标题很像），一律弹出来问你，绝不
静默合并。

### 4.2 七个概念轴

`domain`（领域概念）和 `task`（任务）每个领域各有一棵树；`pattern`
（问题模式）、`function`（功能）、`method`（方法）、`metric`（指标）、
`failure-mode`（失效模式）全领域共享。

跨领域的联系只有三种合法形式：共享轴上挂同一个概念、迁移卡、缺口卡的
`related:` 字段。**禁止**让一个领域的概念当另一个领域概念的上级——
领域之间只有桥，没有上下级。

`concepts.md` 是受控词表：卡片只能用注册过的标准 slug。新概念先当
"候选"，攒够 3 篇真正使用它的论文，并从不同数据或分析评估支持的独立性，
才转正。

### 4.3 书目背景与证据判断

书目背景档取期刊指标档和按年龄计算的引用数档中较高的一档，具体表在
`PALACE.md`。科学判断依据具体 Claim、研究设计、条件覆盖及数据和分析
依赖；引用量、期刊、发表类型和作者重叠不决定结论。临时书目元数据通过
显式 `/palace refresh` 刷新，治理只报告状态。

Argument 和 Conditions 表保存作者论证与研究条件；Evidence relations
记录具体 Claim 关系及直接回应／事后比较；Synthesis 记录当前判断和
Claim/Gap 依赖。索引维护产生受影响综合的审核提示。
`/palace brief progress <topic>` 与 ask、gaps、ideas 共用这些证据。
字段定义见 [EVIDENCE.md](knowledge_palace/protocol/EVIDENCE.md)。

### 4.4 来源边界

简报、回答和草稿把四类陈述分开：

| 类别 | 意思 |
|---|---|
| `[C:slug]` | 有论文原话支持——去那张卡就能查到引句和出处 |
| `[S]` | 综合或推断；写明依据的卡片（单张卡也可以） |
| `[H]` | 待验证的假设；有迁移卡就引用，没有也不为凑标签去造 |
| 背景 / 用户 | 通用背景解释或你自己的观察，如实标明 |

需要时让 auditor 复查：`[C]` 查无出处、或者把综合与假设伪装成论文原话，
都是不放行的错误。

### 4.5 图索引和查询接口

`graph/builder.py` 把知识库整理成一份 JSON 快照（放在
`state_dir/graph-index/`，随时可重建，过程对知识库完全只读）。
`graph/port.py` 在快照上提供五个只读查询操作，每个返回都带快照版本号；
如果知识库在快照之后又变了，查询会明确报"索引过期"，绝不返回旧数据。
viewer、问答预筛、新颖性评估全都走这个接口，谁也不直接翻原始文件。

## 5. 命令详解

完整流程定义在 `knowledge_palace/protocol/COMMANDS.md`。这里概括每条
命令干什么、确认后写什么：

### 收文献

| 命令 | 过程 | 写什么（确认后） |
|---|---|---|
| `/palace ingest [<路径\|DOI\|slug>...]` | 先和库里比对身份（命中就复用原卡）→ 获取能拿到的最好材料 → 按要求深度阅读 → 起草卡片：原文 Claim、Argument/Conditions、可选的分析证据表、带日期的阅读笔记 → `save_paper` 保存（拒绝重复身份、保留旧 Claim）→ 每批结束重建一次索引。只有摘要的材料会生成写明范围的卡 | 论文卡、索引行、综合更新提示 |
| `/palace init <主题> [n]` | 建立或补充主题文献集：领域不存在才注册 → 通过可用数据源或浏览工具检索 → 一次有界候选选择 → 每篇选定论文走 ingest | 同 ingest |
| `/palace expand <目标> [--depth 1\|2] [--max-new N]` | 从论文、问题或证据缺口沿引用和相关研究扩展；每个候选记录选/缓/拒及理由；中断能续跑；选定论文走 ingest | 运行记录 + 同 ingest |
| `/palace domain add <名称>` · `list` | 注册新领域和初始概念（优先复用共享轴）· 列出领域 | 领域注册行 + 概念行 |
| `/palace refresh <impact\|citations\|metadata> [<范围>]` | 刷新书目信息，默认只读缓存（加 `--live` 才真联网） | 缓存区快照；要改卡片会先给你提案 |

### 查询咨询（默认不写文件，除非你说要存）

| 命令 | 你得到什么 |
|---|---|
| `/palace status` | 库存统计（论文/缺口/迁移/概念/领域数）+ 一致性检查（索引和文件对不对得上、有没有野标签） |
| `/palace brief onboard [<领域>]` | 领域入门：概念地图、核心词表、5–8 篇推荐阅读顺序 |
| `/palace brief map <概念>` | 一个概念的方法演进时间线、已确立的结论（带背景）、争议双方并列 |
| `/palace brief progress <主题>` | 问题演进、已有推进、争议、剩余子问题和证据覆盖 |
| `/palace brief gaps [<领域>]` | 开放问题排行：谁试过、为什么没解决、还剩什么子问题 |
| `/palace brief ideas [<领域>]` | 研究机会卡：缺口 × 迁移 → 假设、依据、风险、最小验证实验 |
| `/palace brief transfers [<领域>]` | 迁移候选现状一览 |
| `/palace brief bridges [<领域A> <领域B>]` | 两个领域之间的联系报告；不给参数就出全领域交叉矩阵 |
| `/palace ask <问题>` | 解释、比较或接续讨论（细节见 §6）：有文献支持的话引用 Claim，背景解释和假设如实标明；需要时搜集并入库新文献再接着答 |
| `/palace research <项目>` | 项目研究笔记：问题、工作定义、决策、约束、有材料来源的观察；你要求保留讨论时更新 |
| `/palace updates` · `updates resolve <节点> <条目>` | 索引维护后证据变化、需要复核的判断 · 记录你的复核结论（retain / revise / withdraw） |
| `/palace feasibility <想法\|文件\|项目>` | 可执行 / 满足明确条件后可执行 / 需调整方案 / 目前无法判断，附决定性条件和最小验证试验；科学可辨识性与执行可行性分开判断 |
| `/palace discover [<目标>]` | 最多 5 个跨领域迁移候选，每个都有 ≥2 个实质性桥接概念、双边证据、一个先手验证实验 |
| `/palace idea refine <文本\|文件>` | 想法评估：支持/反对/未知证据并列、最像的前人工作、证伪条件 + 最小实验；只评"相对这个库"的新颖性 |

简报、存档的问答、想法评估在你确认后存到 `briefs/<日期>-….md`；想要独立
复查时再叫 auditor。记住它们只是**快照视图**：可以引用来源，但自己永远
不能当证据用。要保留的讨论结论进项目的 `research.md`。

### 写作

| 命令 | 过程 |
|---|---|
| `/palace write <项目\|材料> [<章节>]` | 先做论文分析（仍有效就复用）→ 明确论证和段落职责 → 依据选定证据和你的材料起草 → 一次聚焦审核，最多自动改两轮，改不完的如实报给你 → 你确认后存成只追加的 `rNNN.md`。直接给材料不用建项目。申请书走同一条路，把申请指南登记为材料即可。没给数据的 Results 只出占位符 |
| `/palace polish <文本\|文件\|项目>` | 先做论文分析 → 判断问题是措辞、段落逻辑还是科学主张 → 只改你指定的段落 → 对照原文核对数字、单位、术语、引用和主张强度。实质性重构归 `write`。科学依据不足会明说，不会用语言修饰盖过去 |
| `/palace draft intro <主题>` | 就是 `write` 的引言章节 |
| `/palace style ingest\|status\|crystallize` | 从你点名喜欢的论文提取 7 维文风特征卡（"喜欢哪里"必须你说，AI 不代猜）→ 攒多了结晶成期刊/语言风格档案；一条风格规则要有 ≥3 篇支持且无冲突才算"稳定" |

### 维护

| 命令 | 过程 |
|---|---|
| `/palace govern` | 体检扫描（哪些候选概念攒够票该转正、哪些临时权重该重算、哪个词反复出现该注册、有没有野标签、废弃 slug 还有谁在用）→ 每个提案附受影响文件清单 → 你确认 → 执行并在治理日志里记一笔 |
| `/palace audit [<卡片>...]` | 深度复查：逐字核对每条引文的出处、找野标签、查溯源标签有没有越界。只出报告；要改，走正常的确认流程 |
| `/palace viewer export [<路径>]` | 纯程序构建（无 AI）：把图索引导出成一个自包含 HTML 文件（默认 `./palace-viewer.html`，必须放在四个数据目录之外），先写临时文件再原子改名 |
| `/palace wiki export [<目录>]` | 重新生成带标记的 Obsidian 汇总页；你的笔记和原始卡片保持权威 |

## 6. ask 是怎么回答的

`/palace ask` 按 `knowledge_palace/workflows/discussion.md` 走：

1. 从你的问题、你的定义、项目里已有的决策和你给的材料出发；不要求先
   有缺口卡或迁移卡。
2. 判断问题需要什么：背景解释、论文证据、跨论文比较、暂定解释，还是
   一个研究决策。
3. 需要库内证据时运行
   `python3 -m knowledge_palace.interaction.research ask "<主题>" --json`，
   得到有界上下文（≤15 个候选、Claim、关系、当前综合、待复核项）；整个
   知识库从来不会整个塞进 prompt。关键 Claim 回到原文上下文核对。
4. 有文献支持的句子引用 Claim；背景解释、假设和你的观察如实标明。库里
   没覆盖的部分说清楚，不编，也不因此拒绝给出标明身份的解释。
5. 补文献会改变答案且你允许时，跑 `init`/`expand`，把你选定的论文入库，
   再用新增 Claim 接着回答同一个问题。你说"记下来"，工作定义、决策、
   备选解释和下一步就进项目的 `research.md`。

## 7. 命令行工具

全部纯标准库，在仓库根目录运行：

```bash
python3 -m knowledge_palace.tools.config_resolver     # 打印四个数据目录解析结果
python3 -m knowledge_palace.graph.builder --rebuild   # 重建图索引
python3 -m knowledge_palace.graph.builder --check     # 查索引是否过期
python3 -m knowledge_palace.metadata.refresh --kind citations --scope all       # 刷新（默认只读缓存，--live 才联网）
python3 -m knowledge_palace.viewer.cli [output.html] [--config <toml>]          # viewer 导出
python3 -m knowledge_palace.viewer.obsidian [目录] [--config <toml>]             # Obsidian 汇总页导出
python3 -m knowledge_palace.interaction.research ask "<主题>" --json            # 有界研究上下文
python3 -m knowledge_palace.interaction.research progress "<主题>"             # 进展视图
python3 -m knowledge_palace.interaction.research updates                        # 待复核的判断
```

跑测试：

```bash
python3 -m pytest knowledge_palace/tests -q   # 几秒跑完
```

## 8. 安全边界一览

| 边界 | 规则 |
|---|---|
| 写入 | 子代理不能写；主代理确认后才写；你拒绝 = 什么都不变 |
| 证据 | 原文 + 出处，不可变；勘误只能追加 |
| 联网 | 搜集、获取全文、你要求的外部检索和 `refresh`，各在自己的任务范围内；`govern` 只报告不联网；viewer 页面零外部请求 |
| Git | 所有 Git 写操作都由你执行；Palace 不暂存、不提交、不推送，也不碰数据目录 |
| 上下文 | 有界研究上下文（≤15 个候选）、每次派活 5–15 张卡、新颖性评估逐级 ≤10/15/30——整个知识库永远不进 prompt |
| 全文 | 只放 `source_dir`；知识库只存指针；写作材料永远不能变成证据 |

## 9. 想扩展

- **加新领域**：`/palace domain add`，不用写代码。
- **接新运行时**：写一个薄接入层，转发到 `knowledge_palace/protocol/`
  与 `workflows/` 并原样绑定九份角色定义即可；接入层不许复制规则正文。
- **加依赖**：目前是零依赖，这是故意的；想加必须走专门的风险评审
  （见 `CLAUDE.md`）。
