# Phase Closeout

## 基本信息

- phase: `<填写 phase 名称>`
- track: `<填写当前 track>`
- slice: `<填写当前总 slice 名>`
- status: `closeout`

---

## closeout 背景

用 2 到 5 行说明为什么现在进入 closeout。

建议回答：

- 本 phase 的主要目标是否已基本完成
- 当前是否已经达到继续扩张不划算、应先收口的状态
- 是否已形成清晰的 stop / go 判断基础

要求：

- 只写当前 phase 的收口背景
- 不写完整项目编年史
- 不重复 kickoff 的大段背景说明

---

## 本轮完成内容

按条目写清楚本 phase 实际完成了什么。

建议格式：

- `<完成项 1>`
- `<完成项 2>`
- `<完成项 3>`

要求：

- 写已落地的能力、命令、artifact、inspection path、规则同步
- 不写尚未实现但“本来想做”的内容
- 尽量和 breakdown 中的 slice 对齐

---

## 本轮未完成内容

列出当前 phase 原本可能考虑，但本轮没有继续推进的内容。

例如：

- `<未完成项 1>`
- `<未完成项 2>`

要求：

- 明确说明“未完成”不等于“失败”
- 如果某项被刻意推迟，应写清楚它为何被推迟
- 避免让下一轮误以为这些是当前 phase 的遗失 bug

---

## stop / go 判断

### stop 判断

说明为什么当前 phase 可以停止继续扩张。

建议回答：

- 当前 phase 的最低完成条件是否已经满足
- 是否已经形成明确的 operator / implementation path
- 当前再继续扩张是否会开始跨出既定边界

### go 判断

说明下一轮工作应如何开始。

建议回答：

- 下一轮是否需要新的 kickoff
- 下一轮应继续哪个 track
- 下一轮是否应视为新的正式 phase，而不是继续追加当前 phase

要求：

- 必须明确写出“当前 phase 到此停止”的理由
- 必须明确写出“下一轮从哪里开始”的建议
- 不要写成模糊的“后续还可继续优化”

---

## 与 kickoff / breakdown 的对照

### 已完成的目标

把 kickoff / breakdown 中已经完成的目标列出来。

- `<目标 1>`
- `<目标 2>`
- `<目标 3>`

### 未完成但已明确延后的目标

把被推迟的目标列出来。

- `<延后项 1>`
- `<延后项 2>`

要求：

- 这里是对照检查，不是重新写一遍 breakdown
- 应帮助下一轮快速判断哪些是本 phase 已关闭事项，哪些应进入下一 phase

---

## 当前稳定边界

写清楚本 phase closeout 后，哪些边界应被视为当前稳定 checkpoint。

例如：

- `<稳定边界 1>`
- `<稳定边界 2>`
- `<稳定边界 3>`

要求：

- 这些边界应帮助后续 phase 判断“不要再默认重开这里”
- 应尽量面向 operator path、artifact semantics、state semantics、command surface

---

## 当前已知问题

列出 closeout 后仍存在、但当前 phase 不继续处理的问题。

例如：

- `<已知问题 1>`
- `<已知问题 2>`

要求：

- 这些问题应是“记录在案但不阻塞当前 closeout”
- 如果某问题已经阻塞 closeout，则不应放在这里，应先解决或明确降级判断

---

## 规则文件同步检查

phase closeout 时，检查以下文件是否需要同步更新。

### 必查
- [ ] `docs/plans/<phase>/closeout.md`
- [ ] `current_state.md`
- [ ] `docs/active_context.md`

### 条件更新
- [ ] `AGENTS.md`
- [ ] `.codex/session_bootstrap.md`
- [ ] `.codex/rules.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

---

## 规则文件更新判断

### 更新 `AGENTS.md`
当以下内容变化时更新：

- active_track 改变
- active_phase 改变
- active_slice 改变
- 长期稳定规则改变
- phase / Git / 文档节奏规则改变
- authoritative docs 路径改变

### 更新 `.codex/session_bootstrap.md`
当以下内容变化时更新：

- Codex 默认读取顺序改变
- active phase 改变
- 默认 phase 文档路径改变
- 默认推荐 branch 改变

### 更新 `.codex/rules.md`
当以下内容变化时更新：

- Git 节奏规则改变
- 文档同步规则改变
- phase closeout 规则改变
- planning / implementation 默认规则改变

### 更新 `README.md` / `README.zh-CN.md`
当以下内容变化时更新：

- 用户可见命令变化
- 用户可见工作流变化
- Quickstart 变化
- 项目整体对外说明变化

如果只是 phase 内部推进，没有改变对外使用方式，不要顺手大改 README。

### 更新 `docs/active_context.md`
closeout 时应：

- 清除当前 phase 的高频推进状态
- 标记当前 phase 已收口
- 切换到下一轮入口状态
- 不把旧 phase 的高频状态继续挂在 active context 上

### 更新 `current_state.md`
closeout 时应：

- 更新最近稳定 checkpoint
- 更新最近完成的 phase
- 更新恢复入口
- 更新最小验证命令（如有变化）
- 更新已知问题（如有变化）

---

## Git 收口建议

列出当前 phase closeout 时推荐的 Git 收口动作。

例如：

1. 完成功能与测试提交
2. 完成 closeout 文档提交
3. 更新恢复入口与必要规则文件
4. 合并回 `main`
5. 视需要打 tag

要求：

- closeout 应与 Git 收口节奏对齐
- 不要让 closeout 只存在文档层，而 Git 历史没有形成清晰边界

---

## 可选：commit summary

如果当前 phase 需要快速复用提交摘要，可在：

- `docs/plans/<phase>/commit_summary.md`

中补充一版简洁摘要。

如果当前 phase 改动不大或提交已经足够清晰，可不写。

---

## 下一轮建议

说明下一轮最建议如何开始。

建议格式：

- next_track: `<填写建议的下一 track>`
- next_phase: `<填写建议的下一 phase>`
- next_slice: `<填写建议的下一 slice>`
- next_action: `<填写下一步应先写 kickoff / breakdown / 切 branch / 先做哪个最小闭环>`

要求：

- 必须可执行
- 不要只写“后续继续优化”
- 应直接帮助下一轮进入新的 kickoff

---

## 本文件的职责边界

本文件用于：

- 判断当前 phase 是否应收口
- 记录本 phase 已完成与未完成的边界
- 给下一轮工作提供 stop / go 依据
- 检查 phase closeout 时哪些规则文件需要同步

本文件不用于：

- 高频状态记录
- 当前 slice 的实时进度追踪
- 完整项目历史归档
- 第二份 README