# 状态同步规则

本文件解决"忘记同步状态"的问题。所有 agent 必须遵守。

---

## 一、Session 开头：强制校验

每个 agent 新会话开始时，必须：

1. 读取 `docs/active_context.md`
2. 检查其中记录的 active_branch 是否与 `git branch --show-current` 一致
3. 检查其中记录的 active_phase / active_slice 是否与最近 commit message 一致
4. 如果发现不一致，**先修正 `docs/active_context.md`，再开始工作**

不一致的常见原因：
- 上一个 agent 完成了工作但忘记更新状态
- 分支已切换但文档未同步
- phase 已收口但 active_context 仍指向旧 phase

---

## 二、Workflow Step 完成时：触发式同步

每当一个 agent 完成自己在 workflow 中的步骤后，必须更新 `docs/active_context.md`：

### 必更新字段
- `当前产出物`：添加本次产出的文件路径
- `当前下一步`：更新为 workflow 中的下一个角色/步骤
- `当前阻塞项`：如需人工 gate，标注 `等待人工审批: <具体内容>`

### 更新格式示例
```markdown
## 当前产出物
- docs/plans/phase19/context_brief.md (gemini, 2026-04-11)
- docs/plans/phase19/design_decision.md (claude, 2026-04-11)

## 当前下一步
等待人工审批 design_decision.md，通过后由 codex 开始实现。
```

---

## 三、Slice 完成时：完整检查

每完成一个 slice，执行以下检查清单：

- [ ] `docs/active_context.md` 的 active_slice 已更新
- [ ] `docs/active_context.md` 的产出物列表已完整
- [ ] `docs/active_context.md` 的下一步已更新
- [ ] 本次产出的所有 .md 文件都有 YAML frontmatter + TL;DR
- [ ] 如果是 Codex，相关代码已 commit 且 message 与 slice 对齐

**如果以上任何一项未完成，不得声称 slice 完成。**

---

## 四、Phase 收口时：全量同步

phase 收口前，必须确认：

- [ ] `docs/plans/<phase>/closeout.md` 已写完
- [ ] `current_state.md` 已更新 checkpoint
- [ ] `docs/active_context.md` 已切换到下一轮入口状态
- [ ] `AGENTS.md` 中的 active 方向已更新（如有变化）
- [ ] Git 分支已准备合并（PR 已创建或已合并）
- [ ] 所有产出物的 frontmatter status 已设为 `final`

---

## 五、产出物登记规则

每个 agent 完成产出后，必须：

1. 在产出文件顶部写好 YAML frontmatter（author, phase, slice, status, depends_on）
2. 在 `docs/active_context.md` 的"当前产出物"节登记文件路径、作者、日期
3. 如果产出物被后续 agent 依赖，在 depends_on 中标注依赖路径

---

## 六、Workflow 步骤之间只传文件路径

agent 之间不直接传递内容。沟通方式：

1. 前序 agent 将产出写入 `docs/plans/<phase>/<artifact>.md`
2. 在 `docs/active_context.md` 登记路径
3. 后续 agent 从 `docs/active_context.md` 获取路径，自行读取

**禁止在对话中大段粘贴其他 agent 的产出内容。读文件路径，不读粘贴内容。**

---

## 七、不一致时的处理优先级

当发现状态不一致时：

1. **Git 是最终真相**：commit history 和分支状态优先于任何 .md 文件
2. **`docs/active_context.md` 优先于其他文档**：如果 active_context 与 AGENTS.md 矛盾，以 active_context 为准并修正 AGENTS.md
3. **产出物文件优先于 active_context 中的描述**：以实际文件内容为准

---

## 本文件的职责边界

本文件是：所有 agent 的状态同步操作规程。
本文件不是：当前状态板、workflow 定义、角色分工说明。
