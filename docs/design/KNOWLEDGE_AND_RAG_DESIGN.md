# 知识架构设计 (Knowledge Truth & Retrieval Architecture)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的知识架构基线**，并在必要处标注未来方向。

当前理解知识层时，应优先使用以下框架：

- **Knowledge Truth Layer**：知识对象的 authoritative state
- **Retrieval & Serving Layer**：围绕知识对象组织召回、过滤与证据打包

而不再使用早期那种简单的“LLM Wiki 在上、RAG 在下”的静态叙事。

---

## 1. 当前核心定位：知识真值优先，而非向量优先

在处理复杂的软件工程、系统设计和长期知识工作时，标准的“切块与嵌入”（Chunk & Embed）RAG 模式很容易碰到边界：

- 找得到相似片段，但找不到当前有效的知识对象
- 召回了文本，却不清楚它的阶段、来源和复用边界
- 召回了相似语义，但无法稳定回答“哪个结论是当前规范版本”
- 回答层不断重复做知识编译，造成 token 浪费和结果漂移

因此，Swallow 当前采用的不是“vector-first retrieval”，而是：

> **truth-first knowledge system with retrieval augmentation**

也就是：

- 先把知识归一为可治理对象
- 再围绕这些对象提供检索、召回与服务

---

## 2. 当前双层架构

### 2.1 Knowledge Truth Layer

知识真值层回答的问题是：

- 什么是当前有效的知识对象
- 这些知识从哪里来
- 处于哪个阶段
- 是否允许复用
- 是否已经 superseded
- 谁拥有写权限

当前基线下，这一层包含的核心对象包括：

- `Evidence`
- `WikiEntry`
- canonical records / canonical registry
- staged / task-linked / reusable knowledge
- promote / reject / dedupe / supersede decisions
- source traceability / grounding refs
- Librarian-controlled canonical write boundary

这一层的 authoritative state 当前应理解为：

> **SQLite-backed knowledge truth**

文件镜像、导出文件和索引视图仍然存在，但它们属于辅助视图或 artifact 视图，而不是天然等于知识真值。

### 2.2 Retrieval & Serving Layer

检索服务层的职责不是替代真值层，而是围绕已治理知识对象提供可用召回。

它负责：

- exact / symbolic retrieval
- metadata / policy-aware filtering
- relation expansion
- vector semantic recall
- text fallback
- evidence pack assembly

因此，在 Swallow 当前系统中，向量检索的定位应当明确为：

> **semantic retrieval augmentation, not authoritative truth**

embedding 和向量索引不是知识主线，也不应成为默认入口；它们只是对已治理知识对象进行补充召回的能力。

---

## 3. 当前 Wiki 的定位

Wiki 不应再被理解为“RAG 之上的摘要页”。

在当前基线中，Wiki 更适合被理解为：

- 项目级知识编译对象
- 稳定语义入口
- 面向人和模型共享的知识组织节点
- 知识真值层内部的一类重要对象

Wiki 的价值不在于“替代原始证据”，而在于：

- 把高价值、相对稳定、可复用的知识组织成可治理对象
- 为 exact match、canonical lookup、relation expansion 提供更稳定的入口
- 减少每次回答都重新从底层文本拼装全局认知的成本

---

## 4. 当前推荐的检索顺序

Swallow 当前更稳的默认检索顺序应是：

1. task-local / canonical / wiki exact match
2. metadata + policy-aware filtering
3. relation expansion
4. vector semantic recall
5. text fallback

也就是说，系统当前更适合坚持：

> **object-first retrieval, vector-assisted recall**

而不是 raw chunk vector-first retrieval。

这与当前已落地的 `SQLite-primary knowledge truth + optional sqlite-vec fallback` 方向保持一致。

---

## 5. 当前知识写入原则

知识层不是随手写入的记忆池，而是受治理的真值系统。

当前写入原则应明确为：

- 只有高价值、可复用、相对稳定的信息才有晋升资格
- 所有高阶知识对象都应尽可能带来源指针
- 并不是所有执行器都能直接写入 canonical knowledge
- 知识晋升必须经过显式策略边界与复核边界
- Librarian / review 流程负责冲突合并、去重和污染控制

因此，Swallow 的知识层更接近：

> **knowledge governance system**

而不是“大模型自动累积记忆的地方”。

---

## 6. 外部 AI 会话摄入

用户常常已经在 ChatGPT、Claude Web 或其他外部工具中完成了前期探索。Swallow 当前支持将这些材料作为**原始输入**进入系统，而不是直接把整段外部对话当作长期知识真值。

这一层的职责是：

- 导入外部对话记录
- 过滤无效发散
- 保留有效结论、约束和被否决路径
- 转换为结构化候选对象
- 先进入 staged / task-linked knowledge，再由后续流程决定是否晋升

因此，外部会话摄入的正确位置是：

**external session → ingestion / extraction / staging → knowledge review / promotion**

而不是：

**external session → direct canonical memory**

### 6.1 Schema Alignment

当前 handoff vocabulary 在代码层已经统一到标准 schema；设计文档中的 `Context`、`Constraints`、`Goals` 等术语，应始终理解为与当前实现的结构化字段对齐，而不是自由文本语义。

---

## 7. 检索适配与数据摄入

Swallow 处理的底层材料类型很多，因此在“原始材料层”仍然需要不同的提取、解析与组织策略。

当前更准确的理解是：

- **原始材料层**：代码、Markdown、README、文档、外部会话、日志、PDF 等
- **知识对象层**：Evidence / Wiki / canonical / staged candidates
- **检索服务层**：围绕知识对象和必要的原始材料建立索引与召回

因此，代码仓库、PDF、事件日志等“领域专属包”的意义主要在于：

- 帮助 ingest / parse / extract
- 帮助形成结构更好的候选知识对象
- 帮助 retrieval layer 在必要时回源到底层材料

而不是让底层材料直接取代知识对象层。

---

## 8. 关于 Graph RAG 等远期方向

Graph RAG、社区发现、图结构摘要等能力可以继续作为方向保留，但在当前基线下，它们应被明确标记为：

- 远期检索增强方向
- retrieval orchestration 的候选能力
- 非当前系统主骨架

它们未来若引入，也应服务于已治理知识对象和关系结构，而不是反向取代知识真值层。

---

## 9. Agentic Retrieval 的正确定位

对于复杂问题，Swallow 允许检索从单次静态流水线，升级为更自主的多轮决策行为。但这里需要注意：

- agentic retrieval 的对象应优先是知识对象与其关系
- 多轮检索是 retrieval orchestration 的升级，而不是放弃真值层
- 检索行为再智能，也不能绕过知识晋升和写入边界

因此，系统可逐步支持：

1. 动态工具选择
2. 多跳推理与多轮检索
3. 召回质量反思与搜索策略调整

但这些都属于 **retrieval / serving intelligence**，而不是知识真值本身。

---

## 10. 当前对实现者的约束性理解

如果继续推进知识系统，当前最重要的几条约束是：

1. 不要把系统重新拉回纯 RAG 叙事
2. 不要把向量索引误写成知识 authoritative store
3. 不要把 Wiki 写成漂浮在真值层之上的展示壳
4. 不要让外部会话导入绕过 staged / review / promotion 边界
5. 不要把“底层材料很重要”误解为“底层材料直接等于可复用知识对象”

---

## 11. 一句话总结

Swallow 当前的知识系统，不应理解为：

> 先做 RAG，再在其上叠一个 LLM Wiki

而应理解为：

> 先将知识归一为受治理的 truth objects，再通过 exact retrieval、policy filtering、vector recall 和 text fallback 为任务提供证据服务
