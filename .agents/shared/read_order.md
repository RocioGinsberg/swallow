# 公共读取顺序

所有 agent 新会话的默认读取顺序。各角色在此基础上追加角色专属文件。

---

## 必读（每次新会话）

按以下顺序读取：

1. `.agents/shared/rules.md` — 共同规则
2. `.agents/shared/state_sync_rules.md` — 状态同步规则
3. `.agents/shared/document_discipline.md` — 运营文档纪律
4. `.agents/shared/reading_manifest_format.md` — 启动 manifest 格式
5. `AGENTS.md` — 仓库入口控制面
6. `docs/active_context.md` — 当前高频状态

完成上述读取后，应先按 `reading_manifest_format.md` 输出 reading manifest，再执行状态校验。

读完上述文件后，应能回答：

- 当前 active track / phase / slice 是什么
- 本轮目标与非目标是什么
- 当前下一步是什么
- 当前有哪些产出物、各处于什么状态

**如果无法回答以上问题，不要开始工作，先与人工确认。**

---

## 按需读取

### 当需要理解当前 phase 的具体任务时
- `docs/plans/<active-phase>/kickoff.md`
- `docs/plans/<active-phase>/breakdown.md`

### 当需要恢复到上次稳定状态时
- `current_state.md`

### 当需要判断 phase 是否该收口时
- `docs/plans/<active-phase>/closeout.md`

### 当需要查阅历史 phase 的设计边界时
- `docs/plans/<older-phase>/closeout.md`
- `docs/archive/*`

### 当需要理解系统方向全局时
- `docs/system_tracks.md`

---

## 默认不读

新会话不自动加载：

- 所有历史 phase 文档
- 所有旧 closeout
- 所有 archive 材料
- 所有旧 `post-phase-*`
- README 中与当前实现无关的背景说明

---

## active_context.md 是唯一路由表

所有 agent 通过 `docs/active_context.md` 找到当前需要读的文件路径。
不要自行搜索文件系统来发现当前工作上下文。
