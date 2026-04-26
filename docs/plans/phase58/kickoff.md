---
author: claude
phase: 58
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase57/closeout.md
  - docs/plans/phase58/context_brief.md
  - docs/roadmap.md
---

## TL;DR

Phase 58 (A-lite) 将"灵感捕获 / 外部讨论回收 / staged review 可见性"三个低摩擦入口打通到 staged knowledge 管线，让系统从"任务执行工具"升级为"思考-执行一体工具"。S2 明确为 existing file ingest 的输入载体补充，并增加受限 `generic_chat_json` 支持；URL / shared link 摄入和完整 Brainstorm topology 后置。核心原则：不引入新的知识存储通道，所有入口共享 staged → review → promote/reject 管线。

# Phase 58 Kickoff: 思考-讨论-沉淀闭环 A-lite

## Phase 身份

- **Phase**: 58
- **Primary Track**: Knowledge / RAG
- **Secondary Track**: Workbench / UX
- **分支建议**: `feat/phase58-knowledge-capture`
- **Roadmap 对应**: 候选 A（A-lite 优先，完整 Brainstorm topology 后置）

## 背景与动机

Phase 55-57 完成了知识治理双层架构 + 图谱关系 + 神经 embedding + LLM rerank 的检索闭环。但在实际使用中暴露了一个体验瓶颈：**知识的"入"远比知识的"出"摩擦大**。

具体表现：
1. **灵感捕获**：operator 突然冒出想法时，需要创建 `.md` 文件 → 选路径 → 切终端 → `swl knowledge ingest-file <path>`。对"几秒钟内想记下来"的场景太重
2. **外部讨论回收**：Open WebUI / ChatGPT / Claude / 其他 chatbot 中完成的 brainstorm，结论回流需要导出 JSON 或整理为 Markdown → 放到本地路径 → `swl ingest <path>`。每次导出落盘是无意义摩擦，且非特定 provider 的 flat message-list JSON 目前缺少显式格式名
3. **staged review 可见性**：reviewer 在 `swl knowledge stage-list` / `swl knowledge stage-inspect` / `swl task staged` 中看不到完整 `source_kind` / `source_ref` / topic，无法快速判断候选来源和质量

这三个问题的共同根因是**输入通道缺乏低摩擦入口**，而非知识管线本身有缺陷。Phase 58 的目标是补齐入口，不改管线。

## 目标

1. **G1 — `swl note` 灵感捕获**：一行命令将文本直接写入 staged knowledge raw 阶段
2. **G2 — `swl ingest --from-clipboard` + `generic_chat_json`**：把 clipboard 作为现有 `swl ingest <source_path>` 的低摩擦输入载体，并支持其他 chatbot 的扁平消息列表 JSON
3. **G3 — staged review 可见性收紧**：reviewer 在列表和详情视图中能看到 `source_kind`、`source_ref`、topic 标签

## 非目标

- **完整 Brainstorm topology**（`DebateConfig` + `BrainstormOrchestrator` + 多模型群聊）：Phase 59 候选，需在低摩擦输入稳定后再做
- **notes source type 退场**：roadmap 已标记为候选方向 C 的一部分，不在本轮
- **路径感知的 Retrieval Policy**：roadmap 候选 C，依赖本轮真实使用反馈
- **Codex CLI 接入**：roadmap 候选 B，独立 phase scope
- **URL / shared link 摄入**：不抓取 `https://chatgpt.com/share/...`、网页分享链接或需要登录态的 remote URL；如需要，应作为后续独立 slice 处理网络、权限和隐私边界
- **复杂 provider adapter/plugin 抽象**：本轮只增加受限 `generic_chat_json`，不引入 `ProviderIngestionAdapter`、插件系统或 per-chatbot adapter class
- **staged knowledge stage 字段新增**：`StagedCandidate` 的 `status` 字段已承担 pending / promoted / rejected 语义，不引入独立 `stage` 字段

## 设计边界

### S1: `swl note <text> [--tag <topic>]`

**行为**：
- 绕过 `filter_conversation_turns()`（operator 文本是结论，不是对话流）
- 参照 `ingest_local_file()` 路径，直接调用 `submit_staged_candidate()`
- `source_kind = "operator_note"`（新值，与现有 `external_session_ingestion` / `local_file_capture` 并列）
- `source_task_id = "note-<YYYYMMDD-HHMMSS>"`（基于时间戳，无文件路径依赖）
- `candidate_id` 继续遵守 staged registry 约束，必须是 `staged-*`；不要生成 `note-*` candidate_id
- `submitted_by = "swl_note"`

**`--tag` 的落地位置**：
- **新增 `StagedCandidate.topic` 字段**（`str`，默认空字符串）
- 理由：`source_ref` 是来源引用（file path / URL），语义不应混用；`taxonomy_role` 是 agent 角色标识，也不应混用；`topic` 是独立的语义维度
- `from_dict()` 已用 `.get()` 默认值，新增字段向后兼容
- `update_staged_candidate()` 必须保留 `topic`，避免 promote/reject 后丢失标签

**CLI 设计**：
```
swl note "用 sqlite-vec 而不是 pgvector，本地优先更符合设计哲学"
swl note "brainstorm 应该支持 attacker 角色" --tag orchestration
swl note --tag retrieval "rerank 是否应该感知 task intent"
```

### S2: `swl ingest --from-clipboard` + `generic_chat_json`

**定位**：
- `swl ingest <source_path>` 仍是稳定核心路径
- `--from-clipboard` 是输入载体补充，不替代文件路径摄入
- `generic_chat_json` 是受限格式补充，用于其他 chatbot 常见 flat message-list JSON；provider-specific 完整导出仍优先走 `chatgpt_json` / `claude_json` / `open_webui_json`

**CLI 设计冲突处理**：
- 当前 `swl ingest` 的 `source_path` 是必填 positional argument
- 方案：将 `source_path` 改为 `nargs="?"` 可选；当 `--from-clipboard` 存在时不要求 `source_path`；两者都缺时报错
- `source_path` 与 `--from-clipboard` 同时存在时报错，避免同一次 ingest 有两个来源 truth
- 这是对 CLI 签名的微调，不是破坏性变更（所有现有用法 `swl ingest <path>` 保持不变）

**剪贴板读取**：
- 不引入 `pyperclip` 依赖
- 使用平台 subprocess：`pbpaste` (macOS) / `xclip -selection clipboard -o` (Linux) / `powershell Get-Clipboard` (Windows)
- 读取失败时显式报错并提示安装要求
- `parse_ingestion_bytes(clipboard_data, format_hint=normalized_format)` 已支持全部格式，无需修改解析器

**`--format` 参数**：
- 可选，省略时 auto-detect（传入 parser 的 `format_hint=None`）
- 显式指定时跳过探测，直接调用对应解析器
- 不新增 `"auto"` 作为 parser choice；如实现层暴露 `"auto"`，必须先归一化为 `None`
- choices 扩展为 `chatgpt_json|claude_json|open_webui_json|generic_chat_json|markdown`

**clipboard source metadata**：
- 不把 `clipboard://...` 伪装成普通文件路径
- staged candidate 的 `source_ref` 必须写成 `clipboard://<format-or-auto>`
- 实现时应新增 bytes/clipboard helper，或给 staged candidate 构造增加 `source_ref` override

**`generic_chat_json` 边界**：
- 支持 `{ "messages": [...] }` 与 `[ ... ]` 两类 flat message-list JSON
- 每条 message 只要求能提取 role-like 字段（`role` / `sender` / `from` / `author`）和 content-like 字段（`content` / `text` / `message`）
- content 可为 string、string list、或 OpenAI-style text parts
- 不恢复 ChatGPT `mapping` 树、不处理 provider-specific branch semantics、不做 URL fetch
- auto-detect 只处理无歧义 flat array；`{"messages": [...]}` 这类可能与 Open WebUI 冲突的结构，推荐显式 `--format generic_chat_json`

### S3: staged review 可见性收紧

**目标**：三个 operator-facing report 函数都展示 `source_kind` / `source_ref` / `topic`

| 函数 | 当前显示 | 新增显示 |
|------|---------|---------|
| `build_stage_candidate_list_report()` | candidate_id, source_kind, source_ref, source_object_id, submitted_by, text preview | `topic`（当非空时） |
| `build_stage_candidate_inspect_report()` | source_kind, source_ref, source_object_id, taxonomy, decision fields, full text | `topic` |
| `build_task_staged_report()` | status, source_task_id, submitted_at, text preview | `source_kind`, `source_ref`, `topic` |

## 完成条件

1. **`swl note` 可用**：一行命令写入 staged knowledge，`swl knowledge stage-list` 可见新条目
2. **`swl ingest --from-clipboard` 可用**：剪贴板内容走 ingestion pipeline 入 staged knowledge
3. **`generic_chat_json` 可用**：文件和剪贴板均可摄入其他 chatbot 的 flat message-list JSON
4. **review 可见性提升**：stage list、stage inspect、task staged 三个视图均展示 `source_kind`、`source_ref`、`topic`
5. **现有行为无回归**：`swl ingest <path>` 所有现有用法保持不变
6. **测试覆盖**：`swl note` 写入 / topic 字段 / clipboard transport / `generic_chat_json` / report 展示字段均有 pytest 覆盖

## Eval 验收条件

| Slice | 需要 Eval | 说明 |
|-------|----------|------|
| S1 (swl note) | 否 | CLI → staged knowledge 写入是确定性路径，pytest 覆盖即可 |
| S2 (clipboard + generic_chat_json) | 否 | 确定性 parser / transport 变更，pytest 覆盖 flat JSON schema 即可 |
| S3 (review visibility) | 否 | 展示字段变更，pytest 验证即可 |

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 理由: Phase 57 已合并，Phase 58 应在新 feature branch 上开发
- 建议分支名: `feat/phase58-knowledge-capture`
- 建议 PR 范围: S1-S3 合入单个 PR
