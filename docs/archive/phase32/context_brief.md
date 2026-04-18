---
author: gemini
phase: 32
slice: context-brief
status: draft
depends_on: ["docs/roadmap.md", "docs/active_context.md"]
---

# Phase 32 Context Brief

> **TL;DR**
> 下一阶段（Phase 32）的核心目标是落地“知识双层架构”与“Librarian Agent”，分离证据层与认知层。重点在于建立 Librarian 的知识提纯与防污染防线，并将外部摄入（Ingestion Specialist）延后处理，以控制边界。

## 1. 基础信息

*   **Next Phase**: Phase 32
*   **Primary Track**: Retrieval / Memory
*   **前置依赖**: Phase 31 (Runtime v0 与统一执行器抽象) 已完成并稳定 checkpoint。

## 2. 核心目标

基于架构蓝图（特别是 `KNOWLEDGE_AND_RAG_DESIGN.md` 与 Roadmap），彻底解决多 Agent 协作带来的隐式记忆污染问题，确保系统上下文越用越精炼。

*   **分离双层架构**：在知识库设计上正式区分 `Raw Evidence Store`（原始证据层/增强 RAG）与 `LLM Wiki Store`（高层认知层）。
*   **实施知识晋升防线**：禁止普通 Agent 随意写回全局知识。所有向全局知识库的写入必须经过 `Librarian Agent` 进行提纯与仲裁。

## 3. 关键执行任务

*   **存储结构调整**：定义并划分 Evidence 和 Wiki 两类存储的数据模型与契约。
*   **Librarian Agent 落地**：开发专用的知识沉淀工作流，由该 Agent 接管 `Staged-Knowledge`，负责合并仲裁、降噪提炼，并规范化产出 Change Log。

## 4. 边界控制与风险批注

基于路线图中 Claude 的批注，本阶段需严格控制 scope 膨胀：

*   **推迟非核心链路**：`Ingestion Specialist`（外部会话摄入者，即将 ChatGPT/Claude Web 导出文件进行结构化转换的链路）应**延后**至 Phase 32 的 stretch slice 或 Phase 33 附加阶段处理。
*   **当前重心**：首要任务是确立并独立验证 Librarian Agent 的“写回防线”核心逻辑。

## 5. 建议下一步

人工审阅本 Context Brief，确认进入 Phase 32 方向无误后，由 Claude 开始撰写 `docs/plans/phase32/kickoff.md` 并进行方案拆解。
