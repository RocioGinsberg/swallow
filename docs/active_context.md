# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Orchestration`
- latest_completed_phase: `Phase 62`
- latest_completed_slice: `Multi-Perspective Synthesis M1+M2+M3 + Review 消化 + Merge`
- active_track: `Governance`
- active_phase: `Phase 63`
- active_slice: `revised-after-model-review + §S2 M0-dependent 双方案待定,待 Human Design Gate / M0 audit`
- active_branch: `main`(尚未切换 feature 分支)
- status: `phase63_S2_dual_scheme_pending_m0_audit`

## 新差距(2026-04-29 Direction Gate 后输入,待 roadmap-updater 增补 §三/§四)

### G:治理守卫收口(Governance Closure)

- **相关设计文档**:INVARIANTS / DATA_MODEL / SELF_EVOLUTION
- **当前状态**:Phase 61 / 62 暴露 5 条宪法-代码漂移 Open(详见 `docs/concerns_backlog.md`):
  1. INVARIANTS §9 剩余 14 条守卫测试缺失(Phase 61 non-goal Open)
  2. Repository 抽象层(`KnowledgeRepo` / `RouteRepo` / `PolicyRepo`)未实装,`_PENDING_PROPOSALS` 模块级 in-memory 注册表(Phase 61 non-goal Open)
  3. `apply_proposal` 事务性回滚缺失,`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` 四步中途失败会导致状态不一致(Phase 61 non-goal Open)
  4. `orchestrator.py:3145` `submit_staged_candidate(...)` 既有 stagedK 直写违反 §5 矩阵 Orchestrator 行 stagedK 列 `-`(Phase 62 design audit Open)
  5. INVARIANTS §7 集中化函数 `swallow.identity.local_actor()` / `swallow.workspace.resolve_path()` 不存在,§9 守卫 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` 可能 vacuous(Phase 62 design audit Open)
- **演进方向**:**候选 G(Phase 63)** —— 一次性收敛 5 条宪法漂移 Open,把 INVARIANTS §5 / §7 / §9 与代码侧拉齐

---

## 当前状态说明

Phase 61 已 merge 至 `main`(`c66fa87 merge: Refine codes after PRD change`,2026-04-28)。M1 canonical / M2 route metadata / M3 policy 三类主写入收敛 + 3 条 INVARIANTS §9 apply_proposal 守卫测试落地,543 passed / 8 deselected。详见 `docs/plans/phase61/closeout.md`。

Phase 62 已 merge 至 `main`(`ce98f92 merge: Complete Refine codes after PRD change`,2026-04-29)。Multi-Perspective Synthesis(MPS) 已完成:Path A route-resolved participant / arbiter 编排、MPS policy governance、仲裁 artifact、explicit `swl synthesis stage` staged handoff、13 条守卫测试与 review follow-up。Closeout 验证:`.venv/bin/python -m pytest` → 559 passed / 8 deselected;`git diff --check` passed。

`v1.3.1` release doc sync 已完成:README / current_state / active_context 已对齐 release target。Tag preflight 验证:`.venv/bin/python -m pytest` → 559 passed / 8 deselected;`git diff --check` passed。Human 已提交 release docs 并完成 annotated tag。

`v1.3.1` tag 已完成(2026-04-29):tag message `v1.3.1: Governance boundary and multi-perspective synthesis`,tag 指向 release docs commit `d6e4b90 docs(release): sync README and state for v1.3.1`;`origin/main` 与本地 `main` 已同步。

post-merge 已完成:

- **[Claude]** 已通过 `roadmap-updater` subagent 增量更新 `docs/roadmap.md`:候选 F 标注为已完成、§三差距表 apply_proposal 行标 [已消化]、Claude 推荐顺序改为 E → D、新增 §六"写入治理"维度行
- **[Claude]** 修正 `roadmap-updater` 输出中 §四 一处重复的"候选 E"段(原 body 是 D 内容)
- **[Claude]** state-sync-checker 复核完毕,识别 2 处 pre-merge 未消化的 doc drift(下方 Open Codex doc TODO)

Phase 62 design 产物(2026-04-28):

- **[Claude/context-analyst]** `docs/plans/phase62/context_brief.md` 已产出。两个意外发现:(a) MPS 完全 greenfield,核心代码无任何 scaffold;(b) staged-knowledge 写权限缺口——INVARIANTS §5 矩阵 Orchestrator 无 stagedK 写权限,需在 design_decision 中给出合宪解。
- **[Claude]** `docs/plans/phase62/kickoff.md` / `design_decision.md` / `risk_assessment.md` 起草完成;采用 3 milestone × 5 slice 拆解(M1 配置与策略 / M2 编排核心 / M3 staged 集成 + 守卫完整化)。
- **[Claude/design-auditor]** `docs/plans/phase62/design_audit.md` 已产出:3 [BLOCKER] + 9 [CONCERN]。三个 BLOCKER 分别为 (a) `_PolicyProposal` 单字段无法承载 MPS kind、(b) `swl audit policy set` 不是 kind-generic、(c) `StagedCandidate` 字段映射错误 + orchestrator.py:3145 既有 stagedK 直写违反 §5 矩阵。
- **[Claude]** 修订 `design_decision.md` → `revised-after-audit`:三个 BLOCKER 解决方案 (a) 新增 `_MpsPolicyProposal` 独立 dataclass + isinstance dispatch(零修改 Phase 61 路径)、(b) 新增独立 `swl synthesis policy set` 子命令组(不重构 audit policy CLI)、(c) StagedCandidate 字段严格对齐既有 schema,且 Phase 62 守卫缩小到 `test_synthesis_module_does_not_call_submit_staged_candidate`,既有 orchestrator.py:3145 路径登记 backlog Open(类比 Phase 61 librarian-side-effect 模式)。
- **[Claude]** 修订 `risk_assessment.md` → `revised-after-audit`:R5 降级、R8/R9 几乎归零、新增 R10/R11(低风险)。
- **[Claude]** `docs/concerns_backlog.md` 新增 2 条 Phase 62 audit 暴露 Open:(a) orchestrator.py:3145 stagedK 直写;(b) INVARIANTS §7 集中化函数 (identity.py / workspace.py) 实际缺失。
- **[Codex]** Human 指定 Codex 按 `.claude/skills/model-review/SKILL.md` 完成 Phase 62 二次审计,替换外部通道 404 占位稿。审计结论:`verdict: BLOCK`。第一轮 audit 的 3 个结构性 BLOCKER 已在修订稿中解决,但新增发现 MPS Path A / Provider Router / `SynthesisParticipant.route_hint` 语义仍未定义清楚,触及 INVARIANTS §4 与 ORCHESTRATION §5,详见 `docs/plans/phase62/model_review.md`。
- **[Claude]** 已按 model_review BLOCK + 7 CONCERN 修订 `design_decision.md` → `revised-after-model-review`:新增 §B.1 Path A route resolution seam(`route_by_name`/`select_route` + `_MPS_DEFAULT_HTTP_ROUTE`),§B.2 task state isolation(`dataclasses.replace` per call),§A.2 同步扩 `_validate_target` 接受 `_MpsPolicyProposal`,§A.6 集中 `paths.mps_policy_path` helper,§E.4 `swl synthesis stage` idempotency(同 task / 同 config_id pending 拒绝重复)。守卫总数从 6 调到 13(M1: 4 / M2-S2: 4 / M2-S3: 3 + 1 加强既有 / M3-S4: 1 / M3-S5: 1)。
- **[Claude]** 同步修订 `risk_assessment.md` → `revised-after-model-review`:新增 R12(Path A 绕过 Provider Router,中)+ R13(`_validate_target` 漏改,低),修订 R1 标题、R3 路径表述、R9 引用。
- **[Claude]** 同步 `kickoff.md` G3/G4:guard 列表与 design_decision §五 对齐,artifact 路径改 `paths.artifacts_dir(...)` 表达,`hard_cap` 项改 `policy_cap` 项。
- **[Human]** Design Gate **已通过**(2026-04-28):approved Phase 62 design 修订稿,Codex 可启动 M1 实装。
- **[Codex]** Phase 62 MPS implementation 已覆盖 M1/M2/M3:新增 `SynthesisConfig` / `SynthesisParticipant`、MPS policy store + `apply_proposal` 写入路径、Path A synthesis 编排、`swl synthesis policy set/run/stage`、staged idempotency 与 13 条守卫测试。验证:`.venv/bin/python -m pytest` → 557 passed / 8 deselected; `git diff --check` passed。
- **[Claude]** Phase 62 PR review 已完成 → `docs/plans/phase62/review_comments.md`(0 [BLOCK] / 4 [CONCERN] / 4 [NOTE])。复跑 `pytest` 仍 557 passed / 8 deselected。CONCERN-1..4 建议本 PR 内消化(participant executor 失败处理 / participant artifact 存全 prompt / participant_id 唯一性 / stage duplicate CLI UX);4 条 NOTE 推荐进 closeout 留痕,不写入 concerns_backlog。其中 NOTE-D(`_MPS_DEFAULT_HTTP_ROUTE` design §B.1 文字偏差)经复核确认 implementer 主动纠正了 design 文字错误(把 Path B 的 `local-claude-code` 误标为 Path A),代码侧无需变更,closeout 中应同步修订 design 表述。
- **[Codex]** 已消化 Phase 62 review:CONCERN-1..4 全部修复;NOTE-B/C 低风险 tightening 已落地;NOTE-A/D 记录到 `docs/plans/phase62/closeout.md`。验证:`.venv/bin/python -m pytest` → 559 passed / 8 deselected;`git diff --check` passed。`pr.md` 已更新为 Phase 62 PR body。

post-merge 决议(Human 已确认,2026-04-28):

1. **Tag 决策**:打 `v1.3.1`(patch bump)。后续动作:Codex 同步 release docs → Human commit + execute `git tag v1.3.1` → Codex 同步 tag 结果。详见 `.agents/workflows/tag_release.md`。
2. **Phase 62 Direction**:候选 E — 完整 Multi-Perspective Synthesis(ORCHESTRATION §5)。设计依据:`docs/design/ORCHESTRATION.md` 受控多视角综合方案 + A-lite 已落地的低摩擦捕获反馈基础 + roadmap §五推荐 E 优先。

## Tag 建议（Phase 62 merge 后）

- 建议:打 tag
- 建议版本号:`v1.3.1`
- Human 决策:已确认打 `v1.3.1`
- 理由:`v1.3.0` 之后已累计 Route-aware Retrieval Policy、`apply_proposal()` governance boundary、Multi-Perspective Synthesis 三项稳定能力增量;当前 main 已 merge Phase 62 且测试通过。
- 当前状态:tag completed,等待后续 phase direction / roadmap factual update。

---

## 当前关键文档

1. `README.md`(v1.3.1 release snapshot 已同步)
2. `docs/active_context.md`(本文)
3. `current_state.md`(v1.3.1 release checkpoint 已同步)
4. `.agents/workflows/tag_release.md`
5. `docs/plans/phase62/closeout.md`
6. `docs/concerns_backlog.md`
7. `docs/design/INVARIANTS.md`

---

## 当前推进

已完成:

- **[Human]** 已 merge `feat/phase61-apply-proposal` 至 `main`(`c66fa87`)
- **[Claude]** 已触发 `roadmap-updater` 完成 post-merge 增量更新
- **[Claude]** 已修正 roadmap §四 重复段
- **[Claude]** 已切换 active_context 至 post-merge 状态
- **[Human]** 已确认 tag = `v1.3.1`、Phase 62 方向 = 候选 E(Multi-Perspective Synthesis)
- **[Claude/context-analyst]** Phase 62 context_brief 已产出
- **[Claude]** Phase 62 kickoff / design_decision / risk_assessment 已起草并经 audit 修订
- **[Claude/design-auditor]** Phase 62 design_audit 已产出(3 BLOCKER 全已在修订稿中处理)
- **[Claude]** concerns_backlog 新增 2 条 Phase 62 audit Open
- **[Codex]** Phase 62 `model_review.md` 二次审计已完成并记录 `verdict: BLOCK`
- **[Codex]** Phase 62 MPS M1/M2/M3 实装与验证完成:policy governance、Path A route resolution + transient state isolation、artifact/event 写入、CLI run/stage/staged duplicate guard、13 条 MPS 守卫均已落地;full pytest passed。
- **[Codex]** Phase 62 review CONCERN-1..4 已消化,NOTE-B/C 已 tightening,`docs/plans/phase62/closeout.md` 与 `pr.md` 已准备完成。
- **[Human]** Phase 62 已提交并 merge 到 `main`(`ce98f92`)。
- **[Codex]** `v1.3.1` release docs 已同步:`README.md` release snapshot + `current_state.md` release checkpoint + 本文状态;tag preflight `.venv/bin/python -m pytest` 已通过(559 passed / 8 deselected)。
- **[Human]** 已提交 release docs 并完成 annotated tag `v1.3.1`(`d6e4b90`,tag message:`v1.3.1: Governance boundary and multi-perspective synthesis`)。
- **[Codex]** 已同步 tag result 状态。
- **[Claude]** 已触发 `roadmap-updater` subagent 完成 Phase 62 post-merge 增量事实更新:§三差距表"完整 Multi-Perspective Synthesis"行标 [已消化]、§四 候选 E strikethrough、§六"思考-讨论-沉淀"现状改为 MPS 已落地。
- **[Claude]** 已修订 `docs/roadmap.md` §五 Claude 推荐顺序:消除原"D 首选 + 无瓶颈推动"自相矛盾,新文 §五 显式说明候选 D 后置、下一轮可考虑非 §三 差距类 phase(治理守卫收口 / 真实使用反馈收集)。
- **[Human]** Direction Gate 已通过(2026-04-29):选定候选 G(治理守卫收口)为 Phase 63 active direction。
- **[Claude/roadmap-updater]** 已增补 `docs/roadmap.md` §三差距表新增"治理守卫收口"行;§四推荐队列新增候选 G 块、候选 D 降至推荐次序 2;§六"写入治理"维度下一步候选改为候选 G(Phase 63 active)。
- **[Claude]** 已二次修订 `docs/roadmap.md` §五 Claude 推荐顺序为"G → D"格式,与 §四对齐。
- **[Claude/context-analyst]** Phase 63 `context_brief.md` 已产出。关键发现:(a) §9 标准表 17 条已实装 3 条(Phase 61 apply_proposal),Phase 62 新增 4 条 MPS 守卫不在 §9 标准表内,§9 表内净缺 14 条;(b) `"local"` 字面量 25+ 命中,大部分是 `execution_site="local"`(站点语义,不应受 §7 集中化约束),需 disambiguate;(c) `orchestrator.py:3145` 是 stagedK 直写唯一漂移点,cli/ingestion 4 处合规;(d) `rollback_*` 字段已存在但只是快照,缺执行路径;(e) `test_append_only_tables_reject_update_and_delete` 需要 SQLite trigger 基础设施。
- **[Claude]** Phase 63 `kickoff.md` / `design_decision.md` / `risk_assessment.md` 已起草完成。设计要点:5 slice / 4 milestone(M1=S1 §7 集中化 / M2=S2 stagedK 治理 + S3 Repository 骨架 / M3=S4 §9 13 条守卫批量 / M4=S5 事务回滚)。S3 标记**高风险(7)**,其他 1 低 / 2 中 / 1 中-低。Phase-guard 内嵌检查已通过。**Model Review Gate 标 required**(触及 INVARIANTS / DATA_MODEL §4.1 / truth write path / S3 高风险)。
- **[Claude/format-validator]** Phase 63 三件套 frontmatter + TL;DR 全部 PASS。
- **[Claude/design-auditor]** Phase 63 `design_audit.md` 已产出:has-blockers,2 BLOCKER + 7 CONCERN。BLOCKER:(a) `apply_proposal` 签名冲突(我误写四参数 + `payload`,实际既有签名是三参数 `(proposal_id, operator_token, target)`,governance.py:209 / DATA_MODEL §4.1);(b) `test_only_orchestrator_uses_librarian_side_effect_token` 守卫无 AST 实装策略说明。
- **[Claude]** 已修订 `design_decision.md` / `kickoff.md` / `risk_assessment.md` → `revised-after-audit`,消化 2 BLOCKER + 7 CONCERN:
  - **BLOCKER S2/S3 签名修正**:S2 改为两步 `register_staged_knowledge_proposal(payload) → apply_proposal(proposal_id, OperatorToken(source="librarian_side_effect", reason=...), STAGED_KNOWLEDGE)`;扩展 `_VALID_OPERATOR_SOURCES` + `ProposalTarget` enum + 新增 `_StagedKnowledgeProposal` dataclass + 新增 `register_staged_knowledge_proposal` 函数;`OperatorToken` 字段保持 `source` / `reason`(无 `actor`)
  - **BLOCKER S2 守卫策略**:7 步 AST 实装规则具体化,允许命中文件集合 ⊆ {orchestrator.py, governance.py};tests/ 豁免;额外断言 orchestrator.py 至少有一次签发(防止伪实装)
  - **CONCERN S1**:`ACTOR_SEMANTIC_KWARGS` 闭集统一为 `{actor, submitted_by, caller, action, actor_name, performed_by}`(authoritative,与 R2 对齐);`workspace.py base` 解析优先级显式 base > SWL_ROOT > cwd;DDL `DEFAULT 'local'` 字面量自然豁免(不在 AST kwarg 调用语境)
  - **CONCERN S3**:Repository 私有方法签名映射表 + Codex PR body 要求列出 actual signature;`_PENDING_PROPOSALS` key 元组化 `(target, proposal_id)`(与既有实装一致)
  - **CONCERN S4**:`NO_SKIP_GUARDS` 白名单(8 条 §0 核心不变量守卫不可 skip);`test_only_apply_proposal_calls_private_writers` S3 内更新扫描目标(不计入 S4 新增)
  - **CONCERN S4/S5 milestone 边界**:`test_append_only_tables_reject_update_and_delete` S4 内只覆盖既有 4 张表,S5 内扩展到包含 `route_change_log` / `policy_change_log`(6 张)
  - **CONCERN S5**:完整 DDL + 字段对照表(对齐 `know_change_log` 的 `timestamp`/`actor`/`target_kind`/`target_id`/`action`/`rationale`,仅 `before_snapshot`/`after_snapshot` 是 route/policy 专用);R10 风险等级降低
- **[Claude/format-validator]** revised-after-audit 三件套 frontmatter + TL;DR 全部 PASS。
- **[Claude/model-review]** Phase 63 `model_review.md` 已产出(reviewer = external-model GPT-5 via `mcp__gpt5__chat-with-gpt5_5`):**verdict = BLOCK**。3 BLOCK + 3 CONCERN:
  - **[BLOCK Q1]** `librarian_side_effect` token 创建 §5 矩阵-代码漂移(本 phase 自称消化漂移却引入新漂移,自我矛盾);Claude 决策:**本 phase 内更新 §5 矩阵 Orchestrator 行 stagedK 列**(需要把"不修改 INVARIANTS 文字"的 non-goal 收紧)
  - **[BLOCK Q5]** staged 应用 + 失败回滚在 SQLite WAL 下不是 race-free,中间状态对 reader 可见,违反"零行为变化";Claude 决策:**改用 SQLite transaction/savepoint(`BEGIN IMMEDIATE`)**;实装路径要 M0 audit 现有 store 函数 connection 模式后定
  - **[BLOCK Q6]** Repository 是新的 bypass surface(私有方法可被任何模块直接调);Claude 决策:S3 增加 2 条守卫(`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`)
  - **[CONCERN Q2]** Repository 公开-私有边界(已通过 Q6 follow-up 消化)
  - **[CONCERN Q3]** ACTOR_SEMANTIC_KWARGS 闭集太窄;Claude 决策:**扩展闭集 + 移除 `action`**(action 不是 actor 语义)
  - **[CONCERN Q4]** NO_SKIP_GUARDS 中途红灯无 fallback;Claude 决策:**新增 M0 pre-implementation audit slice**(report-only NO_SKIP 扫描),根据 audit 结果决定是否拆 Phase 63.5
- 修订 follow-up 范围较大(增加 M0、改 §5 文字、改 SQLite 实装、加 2 守卫、扩展闭集),待 Human 在下方"当前下一步"中决定 follow-up scope。
- **[Human]** 已确认完整 revised-after-model-review(2026-04-29):follow-up scope = 完整修订三件套。
- **[Claude]** 已修订 design_decision / kickoff / risk_assessment → `revised-after-model-review`,落实所有 BLOCK + CONCERN 的消化:
  - **新增 S0 / M0 — Pre-implementation audit slice**:NO_SKIP_GUARDS report-only 扫描 + store 函数 connection 模式 audit;Claude 据 M0 报告决定 phase scope(维持 6-slice / 拆 Phase 63.5)+ S5 实装路径(A/B/C);Human 在 M0 完成后审阅决策再继续
  - **§5 矩阵文字本 phase 内更新一行**(Orchestrator 行 stagedK 列从 "-" 改为 "W*(via apply_proposal + librarian_side_effect token)"+ 配套注脚);non-goals 收紧到"不修改 §0/§1/§2/§3/§4/§6/§7/§8 等核心原则文字;§5 矩阵此一行允许更新"
  - **S5 改用 SQLite `BEGIN IMMEDIATE` transaction wrapping**(取代原 staged 应用 + 失败回滚方案);`action` 字段去掉 `rollback_failed`(SQLite ROLLBACK 原子);S5 实装路径 A/B/C 由 M0 audit 决定
  - **S3 增加 2 条 Repository bypass 守卫**:`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`(§9 表外架构守卫)
  - **ACTOR_SEMANTIC_KWARGS 闭集扩展**:加入 `created_by` / `updated_by` / `owner` / `user` / `principal` / `agent` / `originator` / `executor_name` 等;移除 `action`(不是 actor-semantic)
  - **风险条目调整**:R9(原 staged 回滚函数失败)取消;新增 R12(§5 文字更新下游不一致)/ R13(store connection refactor)/ R14(M0 暴露大范围漂移触发 Phase 63.5)/ R5_NEW(SQLite transaction 路径选择失误);**2 条高风险 slice**(R3 Repository + R5_NEW SQLite transaction)
  - **Slice 数量**:5 → 6(M0 + S1-S5);**5 milestone**(M0/M1/M2/M3/M4);Human Design Gate 时显式审批超出"≤5 slice"指引的例外
- **[Claude/format-validator]** revised-after-model-review 三件套 frontmatter + TL;DR 全部 PASS;model_review.md status 字段是 SKILL 模板要求的 `review`,符合 `.agents/shared/rules.md §七` 允许值。
- **[Human]** Design review 阶段反馈(2026-04-29):**质疑 §5 矩阵更新的必要性**,指出 `_route_knowledge_to_staged` 实际是按 `taxonomy_memory_authority` 路由的通用副作用流(不限于 Librarian),**让 Specialist 直接写 stagedK 才是干净路径**(§5 Specialist 行 stagedK 列已 W,合规)。
- **[Claude]** 已修订 design_decision / kickoff / risk_assessment,**§S2 标记为 M0-dependent 双方案待定**:
  - **方案 A**(librarian_side_effect token + §5 矩阵更新):若 M0 audit 显示 General Executor 等非-Specialist 也走这条流
  - **方案 D**(下沉到 Specialist 内部 + §5 不动):若 M0 audit 显示仅 Specialist 类 executor 触发
  - M0 audit 范围从 2 项扩到 **3 项**(新增 `_route_knowledge_to_staged` 触发场景 audit)
  - kickoff non-goals 软化:`§5 矩阵是否更新由 M0 audit 决定`(不再固定要求更新)
  - risk_assessment 新增 R15(§S2 方案选择失误,中);R12(§5 矩阵更新)调整为 M0-dependent
- **[Claude]** Phase 63 design 现处于"待 M0 audit 决定 §S2 方案"状态,而非"待 Human Design Gate"状态;Human Design Gate 仍可基于当前三件套审批整体 phase 计划,但 §S2 具体实装在 M0 完成后由 Claude 在 active_context 中给出方案选择 + 必要时同步修订三件套。

进行中:

- 无。

待执行:

- **[Human]** Design Gate ⛔:阅读 phase63 三件套 + design_audit + model_review,决定通过 / 打回。本 phase 有几个特殊点需要 Human 显式审批:
  - **§5 矩阵文字更新**:non-goals 已从"不修改 INVARIANTS 文字"收紧为"§5 矩阵 Orchestrator 行 stagedK 列允许更新一行"
  - **6 slice / 5 milestone**:超出"≤5 slice"指引一个(M0 是 audit-only safety net)
  - **2 条高风险 slice**(R3 Repository + R5_NEW SQLite transaction)
  - **M0-dependent S5 实装路径**:Path A / B / C 由 M0 audit 后再敲定
- **[Human]** Design Gate 通过后,切换 feature branch `feat/phase63-governance-closure`,通知 Codex 开始 M0 实装
- **[Codex]** M0 完成后产出 `docs/plans/phase63/m0_audit_report.md`,等待 Claude / Human 决定是否继续 6-slice 或拆 Phase 63.5
- **[Codex / 低优先]** `docs/plans/phase61/closeout.md` 第 81 行 cosmetic doc fix

当前阻塞项:

- 等待 Human Design Gate 决议。

---

## 下一轮 direction 候选(2026-04-29 Claude 提案)

> 以下候选不直接写入 roadmap §四,先由 Human 在 Direction Gate 阶段对比选择,通过后再走 roadmap-updater 标准流程。

### 候选 G:治理守卫收口(Governance Closure)

- **核心价值**:消化 Phase 61 / 62 暴露的 5 条宪法-代码漂移 Open(详见 `docs/concerns_backlog.md`):
  1. INVARIANTS §9 剩余 14 条守卫测试缺失(Phase 61 Open)
  2. Repository 抽象层(`KnowledgeRepo` / `RouteRepo` / `PolicyRepo`)未实装(Phase 61 Open)
  3. `apply_proposal` 事务性回滚缺失(Phase 61 Open)
  4. `orchestrator.py:3145` stagedK 直写违反 §5 矩阵(Phase 62 audit Open)
  5. INVARIANTS §7 集中化函数(`identity.py` / `workspace.py`)不存在,§9 守卫 vacuous(Phase 62 audit Open)
- **可能 slice**:M1 §7 集中化函数 + 守卫真实化 / M2 stagedK 治理通道 + Repository 抽象层骨架 / M3 §9 剩余守卫批量实装 / M4 事务回滚 staged 应用
- **风险**:中——多在治理表面收敛,回滚成本低;但 Repository 抽象层涉及现有 store 函数封装,需谨慎设计接口
- **优先级理由**:宪法层债务继续累积会让 INVARIANTS 失去威慑力;Phase 61/62 已经引入两次"承认现状、登记 Open"模式,再不收口会成习惯
- **依赖**:无,且与未来 D 不冲突(Repository 抽象层是 D 的有用前置)

### 候选 D:编排增强(Planner / DAG / Strategy Router)

- **核心价值**:见 roadmap §四
- **风险**:高——orchestrator 主链路重构,回滚成本高
- **优先级理由**:架构债务清理,但当前编排能力实际可用,**无真实瓶颈推动**;建议在 MPS 真实使用反馈或多 task 复杂依赖场景出现后再做

### 候选 R:真实使用反馈收集(无新代码 phase)

- **核心价值**:用 1-2 周时间真实使用 A-lite + MPS,产出使用反馈,作为后续 Phase 63 / 64 方向的事实输入
- **可能产出**:`docs/feedback/<date>.md` 真实使用记录、新 concern 登记、roadmap §三 新差距条目
- **风险**:低——无代码改动
- **优先级理由**:Phase 60-62 连续三个 phase 都是新能力实装,需要一个"消化期"评估能力是否真正有效;否则 D 没有信号支撑

---

## 当前下一步

1. **[Claude]** 触发 `design-auditor` subagent,产出 `docs/plans/phase63/design_audit.md`
2. **[Claude]** 根据 design_audit BLOCKER / CONCERN 决定:若有 BLOCKER 回到设计修订;若无,触发 Model Review Gate(已预判 required)
3. **[Claude]** 通过 model-review skill(`mcp__gpt5__chat-with-gpt5_5`)产出 `docs/plans/phase63/model_review.md`,根据 verdict 消化反馈
4. **[Human]** Design Gate ⛔:阅读 kickoff / design_decision / risk_assessment / design_audit / model_review,决定通过 / 打回
5. **[Human]** 通过后切换 feature branch `feat/phase63-governance-closure`,通知 Codex
6. **[Codex]** 按 design_decision M1 → M2 → M3 → M4 顺序实装

```markdown
model_review:
- status: completed
- artifact: docs/plans/phase63/model_review.md
- reviewer: external-model (GPT-5 via mcp__gpt5__chat-with-gpt5_5)
- verdict: BLOCK
- next: 待人工决定 follow-up scope (revised-after-model-review / phase split / partial accept)
```

```markdown
model_review:
- status: completed
- artifact: docs/plans/phase62/model_review.md
- reason: BLOCK + 7 CONCERN 已通过 design_decision/risk_assessment/kickoff revised-after-model-review 修订消解;新增 6 条 model-review-driven 守卫
```

---

## 当前产出物

- `docs/roadmap.md`(claude / roadmap-updater, 2026-04-28, post-merge 增量更新 + 重复段修正)
- `docs/active_context.md`(claude, 2026-04-28, post-merge state sync + phase62 design 进度)
- `docs/plans/phase62/context_brief.md`(claude/context-analyst, 2026-04-28, Phase 62 MPS 上下文 brief)
- `docs/plans/phase62/kickoff.md`(claude, 2026-04-28, Phase 62 MPS 入手与范围)
- `docs/plans/phase62/design_decision.md`(claude, 2026-04-28, Phase 62 MPS 实装决策,revised-after-model-review)
- `docs/plans/phase62/risk_assessment.md`(claude, 2026-04-28, Phase 62 MPS 13 项风险与缓解,revised-after-model-review)
- `docs/plans/phase62/kickoff.md`(claude, 2026-04-28, Phase 62 MPS 入手与范围,guard 列表已同步)
- `docs/plans/phase62/design_audit.md`(claude/design-auditor, 2026-04-28, 3 BLOCKER + 9 CONCERN)
- `docs/plans/phase62/model_review.md`(codex, 2026-04-28, Model Review Gate `blocked` — Path A / Provider Router boundary BLOCK)
- `docs/concerns_backlog.md`(claude, 2026-04-28, 新增 Phase 62 audit 暴露 2 条 Open)
- `src/swallow/synthesis.py` / `src/swallow/mps_policy_store.py` + related `models.py` / `paths.py` / `governance.py` / `cli.py` updates(codex, 2026-04-28, Phase 62 MPS implementation)
- `tests/test_synthesis.py` + related `test_cli.py` / `test_governance.py` / `test_invariant_guards.py` updates(codex, 2026-04-28, Phase 62 MPS guards and e2e coverage)
- `src/swallow/synthesis.py` / `src/swallow/cli.py` review follow-up updates(codex, 2026-04-29, Phase 62 CONCERN-1..4 + NOTE-C fixes)
- `tests/test_synthesis.py` / `tests/test_cli.py` review follow-up tests(codex, 2026-04-29, failure abort / prompt elision / unique IDs / duplicate stage UX / state snapshot)
- `docs/plans/phase62/review_comments.md`(claude, 2026-04-28, Phase 62 PR review:0 BLOCK / 4 CONCERN / 4 NOTE)
- `docs/plans/phase62/closeout.md`(codex, 2026-04-29, Phase 62 closeout and review digestion record)
- `pr.md`(codex, 2026-04-29, Phase 62 PR body draft)
- `README.md`(codex, 2026-04-29, v1.3.1 release snapshot)
- `current_state.md`(codex, 2026-04-29, v1.3.1 release checkpoint)
- `docs/active_context.md`(codex, 2026-04-29, post-merge + release docs sync state)
- `v1.3.1`(human, 2026-04-29, annotated tag completed at `d6e4b90`)
- `docs/active_context.md`(codex, 2026-04-29, tag result sync completed)
- `docs/roadmap.md`(claude / roadmap-updater, 2026-04-29, Phase 62 post-merge 增量事实更新 + §五 推荐顺序修订 + 候选 G 增补到 §三/§四/§六 + §五 改为 G→D 顺序)
- `docs/active_context.md`(claude, 2026-04-29, Direction Gate 决议 G + Phase 63 三件套起草 + 状态切换到 design-auditor 待触发)
- `docs/plans/phase63/context_brief.md`(claude/context-analyst, 2026-04-29, Phase 63 治理守卫收口上下文 brief)
- `docs/plans/phase63/kickoff.md`(claude, 2026-04-29, Phase 63 入手与范围)
- `docs/plans/phase63/design_decision.md`(claude, 2026-04-29, Phase 63 5 slice / 4 milestone 治理收口方案)
- `docs/plans/phase63/risk_assessment.md`(claude, 2026-04-29, Phase 63 11 项风险与缓解 — 1 高 / 5 中 / 5 低,revised-after-audit)
- `docs/plans/phase63/design_audit.md`(claude/design-auditor, 2026-04-29, has-blockers — 2 BLOCKER + 7 CONCERN)
- `docs/plans/phase63/kickoff.md`(claude, 2026-04-29, revised-after-audit — G2/G3 调用形式与 key 描述对齐既有签名)
- `docs/plans/phase63/design_decision.md`(claude, 2026-04-29, revised-after-audit — 2 BLOCKER + 7 CONCERN 全部消化)
- `docs/plans/phase63/model_review.md`(claude, 2026-04-29, Model Review Gate verdict = BLOCK,3 BLOCK + 3 CONCERN,reviewer = GPT-5 via mcp__gpt5__chat-with-gpt5_5)
- `docs/plans/phase63/kickoff.md`(claude, 2026-04-29, revised-after-model-review + Human 反馈:G0 audit 第 3 项 + G2 双方案)
- `docs/plans/phase63/design_decision.md`(claude, 2026-04-29, revised-after-model-review + Human 反馈:S0 audit 3 项 + S2 M0-dependent 方案 A/D 决策表)
- `docs/plans/phase63/risk_assessment.md`(claude, 2026-04-29, revised-after-model-review + Human 反馈:R12 改 M0-dependent + 新增 R15 方案选择失误)
