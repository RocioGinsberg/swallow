# 共享规则

本文件规定所有 agent（Gemini、Claude、Codex）在本仓库中工作时应共同遵守的规则。
角色专属规则见各 agent 目录下的 `rules.md`。

---

## 一、工作边界确认

进入任何任务前，先确认：

- active_track
- active_phase
- active_slice
- 当前目标与非目标
- 当前下一步

来源优先级：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/plans/<active-phase>/kickoff.md`
4. `docs/plans/<active-phase>/breakdown.md`

**边界不清楚时，不要开始工作。先与人工确认。**

---

## 二、范围控制

除非当前文档明确要求，不要推进：

- 新 intake 宽度
- 自动 promotion
- 大范围 workbench / UX 扩张
- remote ingestion / sync
- 新平台级复杂度

如果一个改动超出当前 slice，先判断：

1. 它是否只是当前 slice 的局部实现细节
2. 它是否应放入当前 phase 的后续 slice
3. 它是否应延后到下一 phase

---

## 三、文档更新规则

### 高频状态只更新一个地方

唯一高频状态入口：`docs/active_context.md`

以下内容变化时，优先更新它：

- 当前 slice 进度
- 当前下一步
- 当前阻塞项
- 当前 active branch
- 当前产出物路径

**不要把高频状态同时写进 `AGENTS.md`、`current_state.md`、README、closeout。**

### `AGENTS.md` 是入口控制面，不是历史总表

只负责：仓库定位、当前 active 方向、长期规则、节奏规则、authoritative docs 说明。

### `current_state.md` 只做恢复入口

只负责：稳定 checkpoint、最近完成 phase、已知问题、恢复命令、最小验证命令。

### `docs/plans/<phase>/` 是 phase 的正式文档层

每个 phase 默认文档：`kickoff.md`、`breakdown.md`、`closeout.md`、`commit_summary.md`（可选）。

---

## 四、规划规则

### kickoff 必须写清楚边界

必须显式写出：当前 phase、track、slice、目标、非目标、设计边界、完成条件。
如果不明确，不要直接写 breakdown。

### breakdown 必须可执行

至少包含：slice 列表、顺序、每个 slice 的目标、验收条件、默认不做的工作、stop/go 信号。

### 不再新增 `post-phase-*`

新方向性工作必须组织为正式 phase + 明确 track + 明确 slice。

---

## 五、phase 收口规则

每结束一个 phase，至少完成：

1. `docs/plans/<phase>/closeout.md`
2. `current_state.md` 的恢复状态更新
3. `docs/active_context.md` 切换到下一轮入口状态
4. Git 分支收口与合并准备
5. 必要时 tag

### 收口时的文件同步检查

#### 必查
- `docs/plans/<phase>/closeout.md`
- `current_state.md`
- `docs/active_context.md`

#### 条件更新
- `AGENTS.md`（active 方向变化时）
- `.codex/session_bootstrap.md`（读取顺序或 phase 路径变化时）
- `README.md` / `README.zh-CN.md`（对外使用方式变化时）

---

## 六、可选：commit summary

`docs/plans/<phase>/commit_summary.md` 仅在以下情况建议写：

- phase 改动较大
- 需要为 PR / release note 准备概述
- 希望快速复用提交说明

---

## 七、产出物格式规范

### YAML frontmatter（必须）

每个 agent 产出的 .md 文件顶部必须包含：

```yaml
---
author: gemini | claude | codex
phase: <phase-number>
slice: <slice-name>
status: draft | review | approved | final
depends_on: [<file-path>, ...]
---
```

### TL;DR 摘要（必须）

frontmatter 之后、正文之前，必须有 ≤3 行的 TL;DR 摘要。
后续 agent 可以只读 frontmatter + TL;DR 来判断是否需要深入阅读全文。

---

## 八、历史隔离

- `docs/archive/*`、旧 phase closeout、旧 `post-phase-*` 仅按需读取
- 新 session 不自动加载旧 phase 文档
- 只通过 `docs/active_context.md` 中的显式指针才能触达历史材料

---

## 九、测试环境规则

项目统一使用 `.venv` 作为 Python 虚拟环境。

- 测试命令：`.venv/bin/python -m pytest`
- 环境搭建由 Codex 负责（`python3 -m venv .venv && .venv/bin/pip install -e .` + 测试依赖）
- `.venv/` 已在 `.gitignore` 中，不提交到仓库
- 所有 agent 需要跑测试时，统一使用此路径，不临时安装系统级包

---

## 本文件的职责边界

本文件是：所有 agent 的共同操作规则。
本文件不是：某个角色的专属行为定义、当前状态板、phase 正文。
