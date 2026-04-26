---
author: claude
phase: 58
slice: design-decision
status: draft
depends_on:
  - docs/plans/phase58/kickoff.md
  - docs/plans/phase58/context_brief.md
---

## TL;DR

Phase 58 拆为 3 个 slice：S1 `swl note` 灵感捕获（低风险 3 分）、S2 clipboard ingest（低风险 4 分）、S3 staged review 可见性（最低风险 3 分）。S1/S2 无顺序依赖可并行，S3 依赖 S1 新增的 `topic` 字段。实施时必须保留 `staged-*` candidate_id、将 omitted `--format` 作为 auto-detect、为 clipboard path 提供非 Path 的 source_ref override，并确保 topic 在 inspect / update 路径不丢失。

# Phase 58 Design Decision: 思考-讨论-沉淀闭环 A-lite

## 方案总述

为 staged knowledge 管线补齐三个低摩擦输入入口。不修改管线本身（`submit_staged_candidate()` / review / promote 路径不变），只在 CLI 层新增命令和参数。核心设计约束：所有入口共享同一条 staged → review → promote/reject 管线，不引入新的知识存储通道。

## Slice 拆解

### S1: `swl note` 灵感捕获 CLI

**目标**：一行命令将 operator 文本写入 staged knowledge raw 阶段。

**影响范围**：
- `src/swallow/cli.py` — 新增 `swl note` 顶层子命令
- `src/swallow/staged_knowledge.py` — `StagedCandidate` 新增 `topic: str` 字段
- `src/swallow/ingestion/pipeline.py` — 新增 `ingest_operator_note()` 函数

**实现要点**：

1. **CLI 注册**：
   - `note_parser = subparsers.add_parser("note", ...)`
   - `note_parser.add_argument("text", type=str)` — 必填 positional
   - `note_parser.add_argument("--tag", dest="topic", default="")` — 可选 topic 标签

2. **`ingest_operator_note(base_dir, text, topic="")`**：
   - 生成 `source_task_id = f"note-{datetime.now():%Y%m%d-%H%M%S}"`
   - 生成 `source_object_id = f"note-{uuid4().hex[:12]}"`
   - `candidate_id` 必须继续使用现有 staged 语义：传 `candidate_id=""` 交由 `generate_candidate_id()` 生成 `staged-*`，或显式生成 `staged-*`
   - 构建 `StagedCandidate(text=text, source_kind="operator_note", source_task_id=..., submitted_by="swl_note", topic=topic)`
   - 调用 `submit_staged_candidate(base_dir, candidate)` — 直接写入 registry，绕过 `filter_conversation_turns`
   - 输出持久化后的 `candidate_id` 到 stdout

3. **`StagedCandidate.topic` 新增字段**：
   - `topic: str = ""`
   - `__post_init__()` / `to_dict()` / `from_dict()` 同步更新
   - `from_dict()` 已用 `.get()` 默认值，旧 registry 条目自动获得 `topic=""`
   - `update_staged_candidate()` 的逐字段重建必须保留 `topic`，否则 promote/reject 后 topic 会丢失

**风险评级**：
- 影响范围: 1（cli.py + staged_knowledge.py + pipeline.py，均为新增逻辑）
- 可逆性: 1（新增命令，不改已有行为）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3（低风险）**

**验收条件**：
- `swl note "some idea"` 创建 staged candidate，stdout 输出 candidate_id
- `swl note "some idea" --tag retrieval` 创建带 topic 的 candidate
- `swl knowledge stage-list` 可见新条目，`source_kind` 为 `operator_note`
- pytest 覆盖正常写入 / topic 字段 / 空文本拒绝

---

### S2: `swl ingest --from-clipboard` 剪贴板摄入

**目标**：从系统剪贴板读取外部讨论导出，走现有 ingestion pipeline 入 staged knowledge。

**影响范围**：
- `src/swallow/cli.py` — `swl ingest` 子命令参数调整 + clipboard 分支逻辑
- 不新增 Python 依赖

**实现要点**：

1. **CLI 参数调整**：
   - `source_path` 从必填 positional 改为 `nargs="?"` 可选
   - 新增 `--from-clipboard` flag（`action="store_true"`）
   - 新增 `--format` 参数（沿用现有 choices：`chatgpt_json|claude_json|open_webui_json|markdown`，默认 `None`）
   - 不新增 `"auto"` choice；省略 `--format` 即 auto-detect。若实现选择暴露 `"auto"`，进入 parser 前必须归一化为 `None`
   - 互斥校验：`source_path` 和 `--from-clipboard` 至少提供一个，否则报错
   - 冲突校验：`source_path` 和 `--from-clipboard` 不能同时提供，避免来源 truth 含糊

2. **剪贴板读取函数 `_read_clipboard() -> bytes`**：
   - 按平台选择 subprocess 命令：
     - macOS: `subprocess.run(["pbpaste"], capture_output=True)`
     - Linux: `subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True)`，fallback 到 `xsel --clipboard --output`
     - Windows: `subprocess.run(["powershell", "-command", "Get-Clipboard"], capture_output=True)`
   - 读取失败时 `sys.exit(1)` 并提示安装对应工具
   - 不引入 `pyperclip`，保持零新增依赖

3. **pipeline 对接**：
   - clipboard 分支：`_read_clipboard()` → `parse_ingestion_bytes(data, format_hint=normalized_format)` → `filter_conversation_turns()` → staged candidate 构造 → `submit_staged_candidate()`
   - 不把 `clipboard://...` 伪装成 `Path`；应新增 bytes/clipboard helper，或给 staged candidate 构造函数增加 `source_ref` override
   - `source_ref` 设为 `"clipboard://<format-or-auto>"` 标识来源
   - `source_task_id` 建议设为 `ingest-clipboard-<YYYYMMDD-HHMMSS>`，`source_object_id` 继续使用 fragment 序号，保证同一次 clipboard ingest 内可追踪

**风险评级**：
- 影响范围: 1（仅 cli.py 入口层）
- 可逆性: 1（新增参数，现有 `swl ingest <path>` 用法不变）
- 依赖复杂度: 2（依赖平台剪贴板工具可用性，但 fallback 明确）
- **总分: 4（低风险）**

**验收条件**：
- `swl ingest <path>` 现有用法保持不变
- `swl ingest --from-clipboard` 从剪贴板读取并入 staged knowledge
- `swl ingest --from-clipboard --format open_webui_json` 跳过格式探测
- `swl ingest`（无参数）报错提示
- pytest 覆盖 clipboard 路径（mock subprocess）、格式探测路径、互斥校验

---

### S3: Staged review 可见性收紧

**目标**：reviewer 在 staged knowledge 列表、inspect 详情和 task-level staged 视图中能看到 `source_kind`、`source_ref`、`topic`。

**影响范围**：
- `src/swallow/cli.py` — `build_stage_candidate_list_report()`、`build_stage_candidate_inspect_report()`、`build_task_staged_report()` 三个 report 函数

**实现要点**：

1. **`build_stage_candidate_list_report()`**（全局 staged 列表）：
   - 当前已显示 `source_kind` 和 `source_ref`
   - 新增：当 `topic` 非空时显示 `topic: <value>`

2. **`build_stage_candidate_inspect_report()`**（单条 staged 详情）：
   - 当前已显示 `source_kind` 和 `source_ref`
   - 新增：`topic`（当非空时显示真实值，否则显示 `-`）

3. **`build_task_staged_report()`**（task-level 视图）：
   - 当前只显示 status / source_task_id / submitted_at / text preview
   - 新增：`source_kind`、`source_ref`、`topic`（当非空时）
   - 对齐三个 report 函数的信息密度

**风险评级**：
- 影响范围: 1（仅 cli.py report 函数）
- 可逆性: 1（展示字段变更，无数据结构改动）
- 依赖复杂度: 1（依赖 S1 新增的 `topic` 字段）
- **总分: 3（最低风险）**

**验收条件**：
- 全局 staged 列表显示 topic（当存在时）
- staged inspect 详情显示 topic
- task-level 视图增加 source_kind / source_ref / topic
- pytest 验证 report 输出包含新增字段

---

## 依赖说明

```
S1 (swl note) — 独立，无前置依赖
S2 (clipboard ingest) — 独立，无前置依赖
S3 (review visibility) — 依赖 S1 的 topic 字段定义
```

**推荐实施顺序**：S1 → S3 → S2

S1 先落地（定义 `topic` 字段 + `operator_note` source_kind），S3 紧随（展示新字段），S2 最后（独立的 CLI 入口扩展）。

## 明确的非目标

1. **不实现 `DebateConfig` / `BrainstormOrchestrator`** — 完整 brainstorm topology 后置到 Phase 59
2. **不改动 `submit_staged_candidate()` / `load_staged_candidates()` 的核心逻辑** — 只在入口层新增
3. **不引入 `pyperclip` 或任何新 Python 依赖** — 剪贴板读取走平台 subprocess
4. **不退场 notes source type** — roadmap 候选 C 讨论点，不在本轮
5. **不修改 ingestion filter / parser** — 现有 `filter_conversation_turns()` 和格式解析器不变
6. **不新增 `StagedCandidate.stage` 字段** — `status` 字段（pending/promoted/rejected）已承担此语义
