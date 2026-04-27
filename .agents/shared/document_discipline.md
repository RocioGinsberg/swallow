---
applies_to: all_agents
status: stable
---

# Document Discipline

> 这份文档是仓库所有运营文档(协作约定 / 状态文档 / roadmap / concerns 等)的元规则。设计文档(宪法层 / 设计层)以 `docs/design/INVARIANTS.md` 为权威,不受本文件约束。

仓库文档持续保持清晰的关键不在"开始时写得好",而在"持续按纪律维护"。本文档把 5 条纪律显式化,任何 agent 启动会话或参与文档变更时都应遵守。

---

## 纪律 1:每份运营文档顶部声明 owner / updater / trigger / anti-scope

每份运营文档(`AGENTS.md` / `docs/roadmap.md` / `docs/active_context.md` / `docs/concerns_backlog.md` / `docs/plans/<phase>/*.md` / `current_state.md` 等)在文件顶部声明:

```markdown
> **Document discipline**
> Owner: <谁负责这份文档的最终质量>
> Updater: <谁实际去改它,可以是 human / agent / subagent>
> Trigger: <什么条件下才被改>
> Anti-scope: <这份文档不承担什么职责,不该出现什么内容>
```

如果 PR 修改了某份文档,但 PR 内容不属于该文档的 trigger,review 应当拒绝并指向正确位置。

设计文档(`docs/design/INVARIANTS.md` / `docs/design/ARCHITECTURE.md` / 等)不需要这个声明,它们由 `docs/design/INVARIANTS.md §0` 与各文档自身的 "本文件不是" 节自我界定。

---

## 纪律 2:文档之间不允许重复"权威信息"

每个事实只在一处出现,其他位置只引用,不复制。当前的权威映射:

| 信息 | 权威位置 | 其他文档应怎么做 |
|------|---------|------------------|
| 项目原则 / 不变量 | `docs/design/INVARIANTS.md` | 只引用,不复制 |
| 写权限矩阵 | `docs/design/INVARIANTS.md §5` | 只引用,不复制 |
| 三条 LLM 调用路径 | `docs/design/INVARIANTS.md §4` | 只引用,不复制 |
| `apply_proposal` 入口语义 | `docs/design/INVARIANTS.md §0` + `docs/design/SELF_EVOLUTION.md §3` | 只引用,不复制 |
| 五元组定义 | `AGENT_TAXONOMY.md §2` | 只引用,不复制 |
| 物理 schema | `docs/design/DATA_MODEL.md` | 只引用,不复制 |
| 系统能力清单 | `README.md "Core Capabilities"` + `docs/design/EXECUTOR_REGISTRY.md` | 不在其他文档维护副本 |
| Phase 历史 | `git log` + `docs/plans/<phase>/closeout.md` | 不在 roadmap / AGENTS / README 中维护 |
| 当前 phase / slice 进度 | `docs/active_context.md` | 不在其他文档同步副本 |
| Tag / Release docs 同步状态 | `docs/concerns_backlog.md` | 不在 roadmap / AGENTS 中维护 |
| Review 过程产出的 CONCERN | `docs/concerns_backlog.md` | 不散落在 phase plan 内 |

新增"权威映射"时,在本表追加一行,并在原有副本位置改为引用。

---

## 纪律 3:Subagent 产出物边界

Subagent 是隔离 context 的辅助实体。每个 subagent **只能写自己的产出文件**,不能跨边界写。

| Subagent | 输出文件 | 不允许触碰 |
|----------|---------|-----------|
| `context-analyst` | `docs/plans/<phase>/context_brief.md` | 不写 active_context、不写 roadmap |
| `roadmap-updater` | `docs/roadmap.md` | 不写 closeout、不写 active_context |
| `consistency-checker` | `docs/plans/<phase>/consistency_report.md` | 不修改设计文档、不修改实现代码 |
| (其他 subagent) | 各自定义的 output_path | 同样遵守 single-output 边界 |

Subagent 在其定义文件(`.claude/agents/<name>.md`)中显式列出 `output_path`,违反此约束的 PR 应被 review 拒绝。

---

## 纪律 4:文档变更与代码变更分开提交

提交信息使用 `type(scope): summary` 时,文档变更应按类型分别 commit:

| Commit 类型 | scope 示例 | 内容 |
|------------|------------|------|
| `docs(design)` | `docs(design): tighten orchestrator boundary` | 设计文档(宪法层 / 设计层)变更 |
| `docs(meta)` | `docs(meta): add document discipline` | 协作约定 / agent 配置 / 流程规则变更 |
| `docs(state)` | `docs(state): update active_context for Phase 60 S2` | active_context / current_state 状态文档变更,通常跟随实现 PR |
| `docs(plan)` | `docs(plan): add Phase 60 closeout` | phase plan 文档(closeout / kickoff / breakdown 等) |
| `docs(concern)` | `docs(concern): mark Phase 49 S3 resolved` | concerns_backlog 变更 |

要求:

- 一个 commit 只表达一类变化
- 设计文档变更应单独 PR(避免与实现混合提交)
- 状态文档变更可跟随实现 PR,但用独立 commit
- git log 上一眼能看出"哪些是设计在改 / 哪些是流程在改 / 哪些是实现进度在动"

---

## 纪律 5:Agent 启动时输出 reading manifest

每个 agent 进入新会话、读完启动文件后,必须输出一份 reading manifest,告诉 human:

- 我读了哪些文件
- 我准备开始的工作类型
- 是否有读取异常

详细格式见 `.agents/shared/reading_manifest_format.md`。

简短示例:

```
Reading manifest:
  ✓ docs/design/INVARIANTS.md (constitution v1.0)
  ✓ AGENTS.md (collaboration rules)
  ✓ docs/active_context.md (current: Phase 60 design)
  ✓ docs/plans/Phase60/kickoff.md
  ⚠ docs/plans/Phase60/design_decision.md (not found, will be authored this session)
Ready to: review and produce design_decision.md
```

这是一个轻纪律,但能避免 99% 的"agent 没读到关键文件就开始干活"问题。

---

## 守护机制

本文档定义的 5 条纪律由以下机制守护:

| 纪律 | 守护机制 |
|------|---------|
| 1. 每份运营文档顶部声明 | 新增运营文档的 PR 必须包含该声明,否则 review 拒绝 |
| 2. 不重复权威信息 | review 时检查是否引入了已存在于权威位置的副本 |
| 3. Subagent 产出物边界 | subagent 定义文件必须列出 `output_path`;实现层校验 subagent 写入路径 |
| 4. 文档变更分开提交 | git commit message 检查(可选 hook) |
| 5. Reading manifest | agent 第一句输出必须包含 manifest |

发现纪律违反时,先修正再继续,不允许"下次再说"积累。

---

## 本文件的职责边界

本文档是:
- 仓库所有运营文档的元规则
- agent 协作时的纪律契约

本文档不是:
- 设计文档原则的副本(→ `docs/design/INVARIANTS.md`)
- 具体文档的内容指引(各文档自身的 anti-scope 节负责)
- Phase 流程的详细描述(→ `.agents/workflows/feature.md`)
