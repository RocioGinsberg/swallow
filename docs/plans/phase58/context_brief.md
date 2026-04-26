---
author: claude
phase: 58
slice: context-brief
status: draft
depends_on:
  - docs/plans/phase57/closeout.md
  - docs/roadmap.md
---

TL;DR: Phase 57 landed neural embedding + LLM rerank; the retrieval layer is now stable. Phase 58 (A-lite) targets low-friction knowledge capture through `swl note`, clipboard transport, bounded `generic_chat_json`, and staged review visibility, all flowing into the existing `staged_knowledge.py` pipeline. The primary implementation constraints are: keep candidate_id as `staged-*`, add/preserve `topic`, normalize omitted `--format` to parser auto-detect, store clipboard sources as `clipboard://...`, and keep generic chatbot JSON limited to flat message lists.

## 变更范围

- **直接影响模块**:
  - `src/swallow/cli.py` — new top-level `swl note` command; extend `swl ingest` parser with `--from-clipboard` + `--format generic_chat_json`; update staged review output (`build_stage_candidate_list_report`, `build_stage_candidate_inspect_report`, `build_task_staged_report`)
  - `src/swallow/ingestion/pipeline.py` — new `ingest_operator_note()` function (wraps `submit_staged_candidate` directly, bypasses `filter_conversation_turns`); new bytes/clipboard ingest helper or `source_ref` override for clipboard path
  - `src/swallow/staged_knowledge.py` — `StagedCandidate` dataclass; `submit_staged_candidate()`; `load_staged_candidates()`
  - `src/swallow/ingestion/parsers.py` — add bounded `generic_chat_json` parser for flat message-list JSON; existing `chatgpt_json` / `claude_json` / `open_webui_json` / `markdown` behavior remains unchanged

- **间接影响模块**:
  - `src/swallow/ingestion/filters.py` — `filter_conversation_turns()` is called for external session path; `swl note` should bypass it (operator text is already a conclusion, not a raw conversation)
  - `src/swallow/ingestion/__init__.py` — may need to export new public symbols

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| `d001d5b` | docs(retag): sync roadmap and state files before retag | docs only |
| `73a96d7` | roadmap(claude): direction gate update | docs only |
| `aa35ac9` | merge: Retrieval Quality Enhancement | retrieval layer |
| `76c6d9c` | feat(cli): pass document paths to literature specialist | `cli.py`, `planner.py` |
| `30c4c5f` | feat(retrieval): improve chunk overlap behavior | `retrieval_adapters.py` |
| `11d3d92` | feat(retrieval): add llm rerank stage | `retrieval.py` |
| `631e3d2` | feat(retrieval): require neural embedding for vector search | `retrieval_adapters.py` |

## 关键上下文

**ingestion pipeline 结构**

`swl ingest <source_path>` → `run_ingestion_pipeline()` → `parse_ingestion_path()` → `filter_conversation_turns()` → `build_staged_candidates()` → `submit_staged_candidate()`.

`swl knowledge ingest-file <source_path>` → `ingest_local_file()` — 跳过 `filter_conversation_turns()`，直接按 markdown section 分段写入 `StagedCandidate`，`source_kind="local_file_capture"`.

两条路径共享 `submit_staged_candidate()` 写入 `.swl/staged_knowledge/registry.jsonl`。

**`swl ingest` 当前仅支持 file path**

`ingest_parser.add_argument("source_path", ...)` — positional argument，不支持 stdin 或 clipboard。`parse_ingestion_bytes()` 已存在且接受 `bytes`，但 clipboard 读取不能把 `clipboard://...` 伪装成文件 `Path`；CLI 层新增 `--from-clipboard` 分支后，应调用 `parse_ingestion_bytes(clipboard_data, format_hint=normalized_format)`，其中 omitted `--format` 传 `None`，并通过 bytes/clipboard helper 或 `source_ref` override 写出 `source_ref=clipboard://<format-or-auto>`。`--format` choices 需要增加 `generic_chat_json`，用于其他 chatbot 的 flat message-list JSON。

**`generic_chat_json` 的定位**

当前 parser 已有 provider-specific 格式：`chatgpt_json` 处理 ChatGPT `mapping` 树，`claude_json` 处理 `chat_messages`，`open_webui_json` 处理 OpenAI-compatible messages。其他 chatbot 常见导出往往只是 flat message list，字段可能是 `role/content`、`sender/text`、`from/message`。Phase 58 只应新增受限 `generic_chat_json`：

- 支持 `[{"role": "...", "content": "..."}]`
- 支持 `{"messages": [{"sender": "...", "text": "..."}]}`
- 支持 string / string list / OpenAI-style text parts
- 不处理 ChatGPT `mapping` 树、URL、HTML、登录态抓取或复杂 provider plugin
- 对可能与 Open WebUI 冲突的 `{"messages": [...]}` 结构，推荐显式 `--format generic_chat_json`

**`StagedCandidate` 字段清单（无 `topic` 字段）**

`candidate_id`, `text`, `source_task_id`, `source_kind`, `source_ref`, `source_object_id`, `submitted_by`, `submitted_at`, `taxonomy_role`, `taxonomy_memory_authority`, `status`, `decided_at`, `decided_by`, `decision_note`.

`topic` 不存在。`--tag <topic>` 的 S1 设计需要决定：新增字段 vs. 写入 `source_ref` vs. 写入 `taxonomy_role`。`source_kind` 目前已有两个值：`"external_session_ingestion"` (pipeline.py L14) 和 `"local_file_capture"` (pipeline.py L15)；新增 `"operator_note"` 是标准做法，但需要同步 `build_stage_candidate_list_report`、`build_stage_candidate_inspect_report`、`build_task_staged_report` 的展示，并确保 `update_staged_candidate()` promote/reject 后不丢失 `topic`。

**staged review 当前可见字段**

`build_stage_candidate_list_report()` (cli.py L658–686) 显示：`candidate_id`, `source_task_id`, `source_kind`, `source_ref`, `source_object_id`, `submitted_by`, `taxonomy`, `submitted_at`, `text (72-char preview)`. `build_stage_candidate_inspect_report()` 已显示 source metadata 但没有 topic。`topic` 和 `stage` 均不在列表视图中。`build_task_staged_report()` (cli.py L729–758) 更简化：只有 `status`, `source_task_id`, `submitted_at`, `text (80-char preview)`，不显示 `source_kind` 或 `source_ref`.

**`swl note` 与 filter_conversation_turns 的耦合**

`run_ingestion_pipeline()` 强制经过 `filter_conversation_turns()`，该函数基于 keyword 信号和 chatter 检测过滤发散内容。对于 `swl note <text>` 这种 operator 直接写入的场景，文本本身就是结论，不应被过滤。`ingest_local_file()` 已绕过 filter，可作为 `swl note` 实现参考。

**clipboard 读取的平台差异**

`pyperclip` 是跨平台 clipboard 读取的标准方案，但当前 `pyproject.toml` 未声明此依赖。备选是 `subprocess` 调用 `pbpaste` (macOS) / `xclip` / `xsel` (Linux)，但会引入平台检测逻辑。需要在设计阶段决定：新增依赖 vs. 平台 subprocess。

**`source_task_id` 对 `swl note` 的适配**

`_build_source_task_id()` (pipeline.py L269–271) 基于文件路径 stem 构造 ID。`swl note` 没有文件路径，需要一个固定或基于时间戳的 `source_task_id` 策略（如 `"operator-note"` 或 `"note-<date>"`）。注意：`candidate_id` 不能使用 `note-*`，因为 `StagedCandidate.validate()` 要求 `staged-*`。

## 风险信号

- `StagedCandidate` dataclass 使用 `slots=True`，新增字段需要同步所有 `from_dict()` / `to_dict()` 路径以及现有 `.swl/staged_knowledge/registry.jsonl` 向后兼容性（`from_dict()` 已使用 `.get()` 默认值，新字段可安全添加）
- `update_staged_candidate()` 会逐字段重建 `StagedCandidate`，新增 `topic` 后必须同步，否则 promote/reject 会丢失 topic
- `build_task_staged_report()` 不展示 `source_kind` / `source_ref`，若 S3 (review visibility) 仅修改 `build_stage_candidate_list_report` 而不同步此函数，task-level 视图仍然不透明
- `swl ingest --from-clipboard` 与现有 `source_path` positional argument 存在 CLI 设计冲突：`source_path` 目前是必填 positional；引入 clipboard 分支需要将其改为 optional 或改用 `--file` flag，这是破坏性变更
- `parse_ingestion_bytes()` 不接受 `"auto"` 作为 format hint；omitted `--format` 应传 `None`，或 CLI 层先把 `"auto"` 归一化为 `None`
- clipboard transport 需要 `source_ref=clipboard://...`；不能只复用当前 Path-only `build_staged_candidates()` 而不提供 source_ref override
- `generic_chat_json` 容易过度扩张；本轮必须限制为 flat message-list JSON，不做 URL/shared-link ingest 或 provider adapter framework
- `filter_conversation_turns()` 的 chatter 过滤对短 note 文本（如"用 sqlite-vec 而不是 pgvector"）可能误判为 drop_chatter（该函数检查长度 ≤ 24 且以特定 prefix 开头），但不会误判不以 CHATTER_PREFIXES 开头的短句；需要验证
