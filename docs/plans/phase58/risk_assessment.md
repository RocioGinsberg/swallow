---
author: claude
phase: 58
slice: risk-assessment
status: draft
depends_on:
  - docs/plans/phase58/design_decision.md
---

## TL;DR

Phase 58 总体风险极低。所有 slice 均为 additive 新增，不修改已有管线核心逻辑。最大风险点是 S2 的剪贴板读取平台差异与 clipboard source metadata 归一化，但 fallback / source_ref / format normalization 约束已明确。无高风险 slice，无需 Design Gate 之外的额外人工 gate。

# Phase 58 Risk Assessment

## 风险矩阵总览

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险级别 |
|-------|---------|--------|-----------|------|---------|
| S1: swl note | 1 | 1 | 1 | **3** | 低 |
| S2: clipboard ingest | 1 | 1 | 2 | **4** | 低 |
| S3: review visibility | 1 | 1 | 1 | **3** | 低 |

所有 slice 总分 < 7，无高风险 slice。

## S1: swl note — 详细风险分析

### R1.1 StagedCandidate 新增 topic 字段兼容性

**风险**：现有 `.swl/staged_knowledge/registry.jsonl` 条目没有 `topic` 字段。

**缓解**：`from_dict()` 使用 `.get("topic", "")` 默认值。旧条目在反序列化时自动获得空 topic。不需要迁移。

**补充约束**：`update_staged_candidate()` 也必须保留 `topic`，否则 promote/reject 时会因逐字段重建导致标签丢失。

**残余风险**：低。

### R1.2 source_task_id 时间戳碰撞

**风险**：同一秒内调用两次 `swl note` 产生相同 `source_task_id`。

**缓解**：`candidate_id` 和 `source_object_id` 使用 UUID，全局唯一。`source_task_id` 碰撞不影响写入和检索（staged knowledge 按 `candidate_id` 索引）。

### R1.3 candidate_id 前缀约束冲突

**风险**：`StagedCandidate.validate()` 要求 candidate_id 以 `staged-` 开头；如果实现按早期草案生成 `note-*` candidate_id，会直接失败。

**缓解**：`swl note` 创建 candidate 时传 `candidate_id=""`，复用现有 `generate_candidate_id()`，或显式生成 `staged-*`。`note-*` 只用于 `source_task_id` / `source_object_id`。

## S2: clipboard ingest — 详细风险分析

### R2.1 剪贴板工具不可用

**风险**：Linux 上 `xclip` / `xsel` 可能未安装；headless server 没有 X11 clipboard。

**缓解**：读取失败时 `sys.exit(1)` 并输出明确提示（"Install xclip or xsel"）。不会静默失败或损坏数据。

**残余风险**：headless 环境下此功能不可用，但这是预期行为（无 clipboard 可读）。

### R2.2 swl ingest CLI 签名变更

**风险**：`source_path` 从必填 positional 改为 `nargs="?"` 可选，可能影响自动化脚本。

**缓解**：所有现有用法 `swl ingest <path>` 保持不变（`nargs="?"` 接受 0 或 1 个 positional）。仅当 `source_path` 和 `--from-clipboard` 都未提供时报错。

**残余风险**：极低。`nargs="?"` 在 argparse 中是标准特性。

### R2.3 剪贴板内容格式探测失败

**风险**：auto-detect 模式下剪贴板内容既不是 JSON 也不是 markdown。

**缓解**：省略 `--format` 时向 parser 传 `format_hint=None`，复用现有探测逻辑；显式 `--format` 参数可跳过探测。不要把 `"auto"` 字符串直接传给 `parse_ingestion_bytes()`。

### R2.4 clipboard source_ref 不能复用 Path-only 构造

**风险**：现有 `build_staged_candidates()` 从 `Path` 生成 `source_ref`。如果 clipboard path 直接复用该函数，可能无法写出 `clipboard://<format-or-auto>`，或把 clipboard 来源伪装成文件路径。

**缓解**：新增 bytes/clipboard ingest helper，或给 staged candidate 构造增加 `source_ref` override；测试必须断言 clipboard candidate 的 `source_ref` 以 `clipboard://` 开头。

### R2.5 双来源 CLI 输入歧义

**风险**：`swl ingest <path> --from-clipboard` 同时给出文件与剪贴板来源，会让 source truth 不清晰。

**缓解**：CLI 层显式拒绝 `source_path` 与 `--from-clipboard` 同时出现；两者都缺失时也报错。

## S3: review visibility — 无风险

纯展示层变更，不改数据结构。最低风险 slice。实施时必须覆盖 `build_stage_candidate_list_report()`、`build_stage_candidate_inspect_report()`、`build_task_staged_report()`，避免列表、详情、task-level 视图信息密度再次分裂。

## 系统性风险评估

### 向后兼容性

Phase 58 不改变任何已有 CLI 命令语义（`swl note` 是新增命令，`swl ingest` 保持现有用法兼容）。不改变 staged knowledge 数据格式（新增 `topic` 字段向后兼容）。不改变 knowledge truth layer 或 retrieval pipeline。

### 测试策略

所有 slice 均可通过 mock 测试覆盖，不需要真实 clipboard 或 API 连接。S2 的剪贴板读取通过 mock `subprocess.run` 验证，并额外断言 `source_ref=clipboard://...`、`--format` omitted 时传入 `None`、双来源输入被拒绝。

## 结论

Phase 58 风险极低，所有 slice 总分 ≤ 4。主要工作是 CLI 层新增命令和参数，核心管线无改动。建议按设计顺序实施；通过既有 Design Gate 即可，无需 Design Gate 之外的额外人工 gate。
