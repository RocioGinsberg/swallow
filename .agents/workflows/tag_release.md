# Workflow: Tag Release

tag 决策与发布流程。在每次 phase merge 到 main 后触发，由 Claude 评估、Human 决策、Codex 同步文档、Human 执行 tag。roadmap 的 phase 完成状态应已在 post-merge workflow 中同步；本流程不再把 roadmap update 绑定到 tag 决策上。

---

## 触发条件

- feature branch 已 merge 到 main
- 至少完成了一次 phase closeout
- `current_state.md`、`docs/active_context.md` 和 `docs/roadmap.md` 已完成 post-merge 同步

此 workflow 独立于 feature delivery workflow，可单独运行。在 `feature.md` Step 7 中引用此文档为详细规范。

---

## 流程总览

```
Claude: Tag Evaluation  (tag-evaluate skill)
        ↓
 Human: Tag Gate ⛔  →  不打 / 延迟 → 结束（记录原因）
        ↓ 打 tag
 Codex: Release Doc Sync
        ↓
 Human: 审阅 release docs → commit
        ↓
 Human: git tag + push
        ↓
 Codex: Tag Result Sync
```

⛔ = 人工 gate，必须由人工决策后才能继续。

---

## Step 1: Claude — Tag Evaluation

**技能**：`tag-evaluate`

**输入**（按序读取）：

1. `docs/active_context.md` — 确认 merge 状态和当前 phase
2. `docs/concerns_backlog.md` — 检查 Open 项是否影响公共 API
3. `docs/plans/<phase>/closeout.md` — 本轮完成了什么
4. `current_state.md` — 当前公开 tag 与最近稳定 checkpoint

**评估维度**：

| 维度 | 问题 |
|------|------|
| 能力增量 | 自上一个 tag 以来，是否有用户可感知的新能力？ |
| 主线稳定性 | main 上是否有进行中的重构或已知破坏性问题？ |
| Concern 影响 | `concerns_backlog.md` 中的 Open 项是否可能改变公共 API？ |

**输出决策**（三选一）：

- **打 tag**：有显著能力增量，main 稳定，无阻塞性 concern
- **不打**：增量较小，建议等下一个 phase 合并后再评估
- **等待**：存在 Open concern 可能改变公共 API，建议 concern 消化后再打

**产出**：在 `docs/active_context.md` 中以以下格式记录 tag 建议：

```markdown
## Tag 建议（Phase <N> merge 后）

- 建议：打 tag / 不打 / 等待
- 建议版本号：v<X>.<Y>.<Z>（如建议打）
- 理由：<一句话>
- 等待条件：<如选"等待"，说明等什么>
```

---

## Step 2: Human — Tag Gate ⛔

**触发条件**：Claude 已在 `docs/active_context.md` 记录 tag 建议。

**人工动作**：

- 阅读 Claude 的 tag 建议（重点看理由和等待条件）
- 确认测试全部通过（`./venv/bin/python -m pytest` 无失败）
- 决策：

| 决策 | 后续 |
|------|------|
| ✅ 打 tag | 进入 Step 3，通知 Codex 同步文档 |
| ⏸ 延迟 | 在 `docs/active_context.md` 标注 `tag deferred: <原因>`，流程结束 |
| ❌ 不打 | 在 `docs/active_context.md` 标注 `tag skipped: <原因>`，流程结束 |

**版本号选择规则**：

```
v<major>.<minor>.<patch>

patch++  一个 phase 的小增量，无公共 API 变化
minor++  一组 phase 完成，有用户可感知的新能力模块
major++  系统架构层面的重大升级

当前惯例：每 1-3 个有意义的 phase 打一次 tag
不补打历史 tag；不要求每个 phase 必须打 tag
```

---

## Step 3: Codex — Release Doc Sync

**触发条件**：Human 决定打 tag，版本号已确认。

**动作**：更新以下两个文件，使其与新 tag 对齐：

### `README.md`

更新对外版本说明或能力概况章节：
- 版本号引用
- 新增的能力描述（参考 closeout.md 的产出摘要）
- 不删除已有能力描述，只追加或修订有变化的部分

### `current_state.md`

更新两处：
1. `latest_public_tag`
2. 与该 tag 对应的稳定 checkpoint / 恢复说明

**格式约束**：

- README 中英两段保持同步，但仍在同一个文件内维护
- `AGENTS.md` 只在协作规则变化时更新，不作为 tag-level release snapshot
- 完成后在对话中给出建议 commit 命令：`docs(release): sync README and current_state for v<X>.<Y>.<Z>`

---

## Step 4: Human — Release Docs Commit + Tag 执行

**触发条件**：Codex 完成 release doc sync。

**人工动作**：

1. 审阅 Codex 的 README/current_state.md 改动 diff
2. 执行 release docs commit（在 main 上）：
   ```
   git add README.md current_state.md
   git commit -m "docs(release): sync README and current_state for v<X>.<Y>.<Z>"
   ```
3. 确认 main 处于 release docs commit 的顶端
4. 执行 tag：
   ```
   git tag -a v<X>.<Y>.<Z> -m "<tag message>"
   git push origin main --tags
   ```
5. 通知 Codex：tag 已完成（或指出执行失败）

**tag message 建议格式**：

```
v<X>.<Y>.<Z>: <一句话描述这个 tag 代表的能力里程碑>

示例：
v1.3.0: Route-aware retrieval source policy with explicit override support
v1.2.0: Retrieval quality era — neural embedding, LLM rerank, lit-specialist doc paths
```

## Step 4.5: Codex — Tag Result Sync

**触发条件**：Human 已确认 tag 已完成或已说明失败原因。

**动作**：

- 更新 `docs/active_context.md`：标注 `tag completed` / `tag failed` / `tag deferred`
- 如 tag 已完成，确认 `current_state.md` 中的 `latest_public_tag` 与已执行版本一致
- 不再额外要求 roadmap follow-up step

---

## 异常处理

### Codex release doc sync 后发现遗漏

Human 审阅时发现描述不准确 → 直接在对话中说明，Codex 修正，重新给出 commit 建议。

### Tag 打完后发现 release docs 有误

不修改已打的 tag。在下一个 tag 的 release docs 中修正（tag 不补打，不删除重打）。

### 延迟的 tag 何时重新评估

下一个 phase merge 到 main 后，重新运行此 workflow 的 Step 1（Claude Tag Evaluation），一并评估两个 phase 的累积增量。
