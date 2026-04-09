# Session Bootstrap

本文件用于规定 Codex 在本仓库中新开会话时的默认读取顺序与上下文装配规则。

目标：

- 减少无必要的历史加载
- 优先读取当前轮次必需信息
- 保持 phase、Git、文档节奏一致
- 避免把 archive 当作当前目标

---

## 默认读取顺序

新会话默认按以下顺序读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `docs/plans/phase12/kickoff.md`
5. `docs/plans/phase12/breakdown.md`

如果以上文件已经足够回答“当前在做什么、为什么做、边界是什么、下一步是什么”，则不要继续扩大读取范围。

---

## 按需读取

只有在以下情况才继续读取其他文档。

### 读取 `current_state.md`
适用情况：

- 需要恢复到上一次稳定 checkpoint
- 需要确认当前恢复命令、最小验证命令、已知问题
- 需要快速理解最近阶段收口后的整体状态

### 读取 `docs/plans/phase12/closeout.md`
适用情况：

- 当前 phase 已经接近收口
- 需要判断 stop / go 条件
- 需要准备 closeout、README 对齐或阶段归档

### 读取旧 phase 文档
适用情况：

- 当前问题明确依赖某个历史 phase 的设计边界
- 当前实现需要确认某条旧 closeout 的 stop/go 判断
- 当前需要核对历史命令、artifact、语义来源

### 读取 `docs/archive/*`
适用情况：

- 需要查旧命名、旧过渡方案、旧 post-phase 材料
- 需要确认历史遗留设计，而不是当前默认工作方向

---

## 默认不要读取的内容

新会话不要默认回读以下内容：

- 所有历史 phase 文档
- 所有旧 closeout
- 所有 archive 材料
- 所有旧 `post-phase-*`
- `.codex/` 下的历史 phase 副本文档
- README 中与当前实现无关的长背景说明

除非当前任务明确依赖这些信息，否则不要把它们自动装入当前上下文。

---

## 当前默认工作方向

当前默认工作方向为：

- active_track: `Retrieval / Memory`
- active_phase: `Phase 12`
- active_slice: `Knowledge Promotion And Reuse Review`

当前默认分支建议：

- `feat/phase12-knowledge-promotion-review`

当前默认工作重心不是扩大 intake，而是补齐 intake 之后的：

- review queue
- promote / reject
- decision record
- reuse-readiness inspect
- docs/help alignment

---

## 当前默认工作方式

每次新会话都先确认以下问题：

1. 当前 active track 是什么
2. 当前 active phase 是什么
3. 当前 active slice 是什么
4. 本轮目标与非目标分别是什么
5. 当前下一步是什么
6. 当前是否处于 planning、implementation、closeout 之一

如果以上问题无法从 `AGENTS.md` 与 `docs/active_context.md` 中清楚回答，再按需扩展读取范围。

---

## 文档使用规则

### `AGENTS.md`
用途：
- 仓库入口控制面
- 长期规则
- 当前 active 方向说明
- phase / Git / 文档节奏规则

不应用作：
- 完整 phase 历史总表
- 高频状态板
- 详细恢复日志

### `docs/active_context.md`
用途：
- 当前唯一高频状态入口
- 当前 phase / 当前目标 / 当前边界 / 当前下一步

要求：
- 新会话优先读取
- 当前实现推进中优先更新
- 不承担长期归档职责

### `current_state.md`
用途：
- 恢复入口
- 最近稳定 checkpoint
- 已知问题
- 最小恢复命令

要求：
- 只在收口或恢复语义变化时更新
- 不当作当前高频状态板使用

### `docs/plans/<phase>/`
用途：
- 当前 phase 的 kickoff / breakdown / closeout / 可选 commit summary

要求：
- 当前 phase 先读 kickoff 和 breakdown
- closeout 只在接近收口时重点读取
- 历史 phase 只按需读取

### `.codex/`
用途：
- Codex 控制层
- 会话启动规则
- 工作规则
- 模板

要求：
- 不复制一整套 phase 正文
- 不复制 README / AGENTS / docs 的主内容
- 保持轻量

---

## Git 与实现节奏

新会话进入实现前，默认假定以下节奏成立：

- 不直接在 `main` 上开发
- 一个 phase 对应一个短生命周期 feature branch
- 一个 slice 对应一个或多个小步提交
- 高频状态只更新 `docs/active_context.md`
- closeout 时再同步 `current_state.md`、README、AGENTS

如果当前分支、当前 phase、当前 active_context 不一致，先修正文档与分支语义，再继续实现。

---

## 当前会话启动检查

开始当前轮次实现前，先确认：

- [ ] 已读取 `AGENTS.md`
- [ ] 已读取 `docs/active_context.md`
- [ ] 已读取 `docs/plans/phase12/kickoff.md`
- [ ] 已读取 `docs/plans/phase12/breakdown.md`
- [ ] 已确认当前分支命名是否与当前 phase 对齐
- [ ] 已确认当前任务没有无意扩张到 phase 外范围

如果以上检查未完成，不应直接进入大范围实现。

---

## 本文件的职责边界

本文件是：

- Codex 新会话的读取顺序说明
- 当前上下文装配规则
- 当前默认工作方向入口

本文件不是：

- 历史 phase 归档
- 当前完整状态板
- phase closeout 材料
- 第二份 AGENTS