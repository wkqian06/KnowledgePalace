# KnowledgePalace

[English](README.md) | 中文

一句话：这是一个**用证据说话的科研文献知识库**。你在 Claude Code（或
Codex）里跟它对话，它帮你把读过的论文整理成一套 Markdown 知识库，并在
这套库上回答问题、找研究方向、辅助写论文。

它有三条最基本的脾气：

- **每条结论都有出处**——库里存的不是"大意"，而是论文原话，外加精确
  位置（第几节、第几段、第几页）。没有出处的话，它不存也不说。
- **不知道就说不知道**——回答问题只用库里真实存在的证据。证据不够时
  不会硬编，而是告诉你缺什么、建议补哪些文献。
- **写任何东西前先问你**——所有写入操作都会先打包展示给你确认，你说
  "不"，一个字都不会动。

## 它能干什么

**攒文献**

- **收论文**（`/palace ingest`、`/palace init`）——给它 DOI 或 PDF，它
  生成一张"论文卡"：原文引句 + 出处、这篇论文暴露了哪些研究缺口、打上
  概念标签、评一个权重档（看影响因子和引用数，引用数还按论文年龄分档）。
- **记研究缺口**——论文越读越多，每个缺口（gap）下面会攒出一张关系表：
  谁提出的、谁部分解决了、谁有异议，每条关系都带权重。改缺口状态必须
  写理由，而且只靠预印本这种低权重证据永远关不掉一个缺口。
- **顺着引用扩展文献**（`/palace expand`）——沿引用关系往外找新论文，
  但深度最多 2 层、数量有上限，选或不选每篇都有记录。不会失控乱爬。
- **多领域共存**（`/palace domain add`）——每个领域有自己的概念树，
  领域之间只通过"桥"相连（共享的抽象概念、迁移卡），不允许一个领域
  当另一个领域的上级。

**问它问题**

- **问答**（`/palace ask`）——回答的每句话都带标签：`[C:xxx]` 表示
  "有论文原话支持，去这张卡看出处"，`[S]` 表示"这是跨论文的综合判断"，
  `[H:xxx]` 表示"这只是待验证的假设"。库里证据只够答一半，它就只答
  一半，并把没答上的部分列出来；完全不够，它就不答，改成给你一个补
  文献的方案。
- **简报**（`/palace brief`）——六种视图：`onboard`（领域入门地图 +
  推荐阅读顺序）、`map`（某个概念的方法演进时间线）、`gaps`（开放
  问题排行）、`ideas`（研究机会卡）、`transfers`（跨领域迁移雷达）、
  `bridges`（两个领域之间有哪些联系）。
- **跨领域找灵感**（`/palace discover`）——在不同领域之间找"这个方法
  也许能搬过来用"的迁移候选，每个候选都要有实打实的桥接概念和一个
  能先做的验证实验。泛泛的"都用了深度学习"不算桥。
- **打磨你的想法**（`/palace idea refine`）——把你的 idea 丢给它，它用
  库里的证据帮你审：哪些证据支持、哪些反对、最像的前人工作是谁、怎么
  证伪、最小验证实验是什么。它只说"相对这个库新不新"，不吹"全世界
  首创"。

**帮你写东西**

- **写论文/申请书**（`/palace write`）——按项目管理：先冻结一份"写作
  合同"（用哪些证据、写哪些章节），然后一节一节写，AI 写完 AI 审，
  审完你确认才存档。存档只追加不覆盖，历史版本永远都在。没给它实验
  数据，Results 部分就只出占位符——**结果绝不编造**。
- **学文风**（`/palace style`）——把你喜欢的论文的写作风格拆成特征卡，
  攒多了结晶成"某期刊风格"档案，写作时可以套用。
- **起草引言**（`/palace draft intro`）——给个主题，产出一份每句话都
  标了证据来源的引言骨架，你在上面自由改写。

**日常维护**

- **治理和审计**（`/palace govern`、`/palace audit`）——定期体检：哪些
  概念该转正、哪些权重该更新、有没有卡片引用了不存在的标签。所有修改
  同样先列清单再经你确认。
- **离线图谱浏览器**（`/palace viewer export`）——导出一个 HTML 文件，
  浏览器直接打开就能浏览整个知识图谱。零依赖、零联网。

## 几条底线

- **你的数据不在这个仓库里。** 论文卡、全文、写作项目放在四个独立目录
  （详见 GUIDE），本仓库只有"程序和规则"。Palace 也绝不对你的数据目录
  执行任何 Git 操作。
- **先确认后写入。** 干活的子代理全部只读；只有主代理能写，且只写你
  批准的内容。
- **引文永不改动。** 发现错误就追加勘误并保留原文，绝不原地改。
- **默认不联网。** 只有你主动执行 `/palace refresh` 时才碰网络。
- **不搞假精确。** 权重只分高/中/低档，不算什么综合得分；少数派证据
  永远和主流证据摆在一起给你看。

## 快速上手

需要：Python ≥ 3.9（纯标准库，什么都不用装）+ Claude Code（或 Codex）。

```bash
git clone <this-repo> KnowledgePalace
cd KnowledgePalace

# 1. 在仓库外面建四个数据目录
mkdir -p ../KnowledgePalace-vault ../KnowledgePalace-state \
         ../KnowledgePalace-sources ../KnowledgePalace-workspace

# 2. 复制配置（路径相对于配置文件本身；按上面建的目录默认值直接可用）
cp .palace.example.toml .palace.toml

# 3. 体检——只读，不写文件，不联网
python3 -m knowledge_palace.tools.doctor
```

然后在仓库根目录打开 Claude Code，直接开聊：

```
/palace init transformer-interpretability 30   # 建库：搜论文 → 你勾选 → 批量收录
/palace ingest 10.1038/s41586-021-03819-2      # 或者按 DOI 收单篇
/palace status                                 # 看看库里有什么
/palace ask what limits sample efficiency here?
/palace brief gaps                             # 开放问题排行
/palace viewer export                          # 导出离线图谱浏览器
```

## 常用命令

| 命令 | 干什么 |
|---|---|
| `/palace init <主题> [n]` | 从零建库：搜候选 → 你勾选一次 → 批量收录 |
| `/palace ingest [<路径\|DOI>...]` | 收录论文（单篇或一批） |
| `/palace expand <论文\|DOI> [...]` | 沿引用关系有上限地扩展文献 |
| `/palace domain add <名称>` · `list` | 注册新领域 / 列出领域 |
| `/palace status` | 库存统计 + 一致性检查 |
| `/palace brief <视图> [<领域>]` | 六种简报：onboard · map · gaps · ideas · transfers · bridges |
| `/palace ask <问题>` | 基于库内证据的问答 |
| `/palace discover [<目标>]` | 跨领域迁移侦察 |
| `/palace idea refine <文本\|文件>` | 审你的研究想法 |
| `/palace draft intro <主题>` | 起草带证据标注的引言 |
| `/palace write <项目> [<章节>]` | 按章节写论文/申请书 |
| `/palace style <ingest\|status\|crystallize>` | 建文风库 |
| `/palace govern` · `audit` | 定期体检 · 深度复查 |
| `/palace refresh <类型> [<范围>]` | 手动刷新引用数等元数据（唯一联网入口） |
| `/palace viewer export [<路径>]` | 导出离线 HTML 图谱浏览器 |

## 深入了解

- **[GUIDE.zh-CN.md](GUIDE.zh-CN.md)**——架构、目录结构、数据模型、命令
  详解。
- **[TUTORIAL.zh-CN.md](TUTORIAL.zh-CN.md)**——手把手教程，从装好到写出
  一节论文。
- **[PALACE.md](PALACE.md)**——公开规则：概念轴、权重档、各种阈值。
- **[CONTEXT.md](CONTEXT.md)**——术语表，每个名词的准确定义。
- **`knowledge_palace/protocol/`**——协议正文（约束 AI 行为的规则原文）。