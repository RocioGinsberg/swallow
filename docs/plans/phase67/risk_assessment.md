---
author: claude
phase: phase67
slice: risk-assessment
status: revised-after-design-audit
depends_on:
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/design_audit.md
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase66/audit_index.md
  - docs/plans/phase66/closeout.md
---

TL;DR(revised-after-design-audit,2026-04-30):**7 条风险条目**保持(R1-R7)。**0 高 / 3 中 / 4 低**。design_audit 12 项 finding 已经 design_decision §S1.X / §S2.X / §S3.X 全部消化,无新增风险条目。R1(IO helper 均质化)缓解强化 = §S2.2 加 authoritative 对照规则;R4(CLI golden output)缓解强化 = §S3.4 加 dispatch 命令验证 + §S3.1 dispatch table 重写为可执行 pseudocode + scope 扩到 3592-3787 闭合两套 dispatch 风险。**仍不触发 model_review**(max risk score = 5)。

## 风险矩阵

| ID | 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 |
|----|------|---------|--------|-----------|------|------|
| R1 | M2 IO helper 错误策略均质化(strict caller 改 missing-is-empty,无声失败代替 crash) | 2 | 2 | 1 | 5 | 中 |
| R2 | M1 `_pricing_for` 模块级 vs instance method 混淆(grep 漏检 dynamic dispatch / `getattr`) | 1 | 1 | 1 | 3 | 低 |
| R3 | M1 `[:4000]` audit 漏记 line 452(三处一致命名遗漏) | 1 | 1 | 1 | 3 | 低 |
| R4 | M3 CLI golden output 破坏(dispatch 重构改 stdout 格式) | 2 | 1 | 1 | 4 | 中 |
| R5 | M3 argparse 兼容性破坏(`--help` 输出变化) | 1 | 1 | 1 | 3 | 低 |
| R6 | M2 artifact name 决议变更影响 M3 起点(若 M2 review 时 Claude 改宽选项) | 2 | 2 | 1 | 5 | 中 |
| R7 | Phase 67 与候选 O 衔接不畅(M2 IO helper 接口接 `Path`,候选 O 需改 `source_ref` URI) | 1 | 1 | 1 | 3 | 低 |

---

## 详细分析

### R1 — M2 IO helper 错误策略均质化(中)

**描述**:Phase 67 的最高风险点。M2 创建 `_io_helpers.py` 三个 variants(`read_json_strict` / `read_json_or_empty` / `read_json_lines_or_empty`)替换 11+ callsite。**Codex 在替换时若不严格按 design_decision §S2.2 authoritative 表选 variant,可能把 strict caller 改为 missing-is-empty**,导致原本应 crash 的损坏文件场景无声成功并返回空数据。

**触发场景**:
- `canonical_registry.py` 中某 callsite 在原代码里 `path.read_text()` 抛 `FileNotFoundError` 是被外层 try/except 转为 user-visible error(语义为"canonical registry 必须存在");Codex 未读 surrounding 代码,默认改 `read_json_or_empty`,从此 canonical registry 缺失时返回 `{}` 静默成功
- 类似的"file 必须存在 → crash"语义可能散落在 `dialect_data.py` / `truth/knowledge.py` 部分路径
- Codex 实装时偷懒 = 全部用 `read_json_or_empty`(因为它最宽容,看似最安全)

**缓解**:
- design_decision §S2.2 已给 11 个 callsite 的 authoritative variant 映射表 + Codex 实装规则(grep 现行行为 → 与表对齐 → 不一致暂停回写 design)
- 表中明确标 "**Codex grep 验证**" 的 callsite(canonical_registry.py / staged_knowledge.py / dialect_data.py)— Codex 必须先读这些 callsite 的 surrounding code 确认现行行为再改
- M2 review 重点:Claude 必须 grep 每个 callsite 的 before/after 行为,验证 variant 选择对位
- 若发现误均质化 → M2 直接打回 + Codex 修订 + 重 review

**回滚成本**:中。M2 IO helper 切换跨 11 个 callsite,某个 callsite 行为漂移可能在生产环境长期未暴露(取决于该 callsite 是否被 hot path 触发)。但 M2 review 阶段就发现成本低(仅需 grep 对照)。

---

### R2 — M1 `_pricing_for` 删除前 grep 漏检(低)

**描述**:`cost_estimation.py` 同时有模块级 `_pricing_for(model_hint)` (line 34, dead) 和 `StaticCostEstimator._pricing_for(self, model_hint)` (line 59, live)。删除模块级版本前需确认无 `_pricing_for(...)` 非 self 形式调用。**Python 的 dynamic dispatch / `getattr(module, "_pricing_for")` / `from cost_estimation import _pricing_for` 等可能被 grep 漏检**(getattr 字符串 string literal 漏过普通 grep)。

**触发场景**:
- 极小概率有动态调用(如某测试 framework 反射加载 `_pricing_for`)
- 删除后 `pytest` 全量绿灯但生产环境某 cron / hook 触发的代码路径炸

**缓解**:
- context_brief 已确认 `grep -rn '_pricing_for' src/ tests/` 无 non-self 形式
- M1 完成前再跑一次 `grep -rn '_pricing_for' .`(包括 docs/、scripts/、配置文件等)
- 删除后若 pytest 抛 `NameError` / `AttributeError` → 立即回滚
- Phase 66 audit 已审 src/swallow/ 全部 .py 文件(70 个),`_pricing_for` 真实只有 cost_estimation.py 一处定义 + 一个 self callsite,信号干净

**回滚成本**:零(单 commit 可 git revert)。

---

### R3 — M1 `[:4000]` audit 漏记 line 452(低)

**描述**:context_brief grep 验证发现 `retrieval_adapters.py` 中 `[:4000]` 实际有三处(lines 267 / 312 / 452),但 audit_index 只记录了前两处。Codex 实装时若仅按 audit_index 行号替换,会漏掉 line 452,导致同一 magic number 部分常量化部分裸字面量。

**触发场景**:
- Codex 严格按 design_decision §S1.4 给的 lines 267/312 替换,完全没读 surrounding code → line 452 漏改

**缓解**:
- design_decision §S1.4 已明确标"audit_index 漏记 line 452;Codex 实装时处理三处一致命名"
- Codex 实装时 `grep -n '\\[:4000\\]' src/swallow/retrieval_adapters.py` 应返回 3 处,而非 2 处
- M1 review 时 Claude 验证 grep 结果 = 0 处(全部已替换)

**回滚成本**:零(发现漏改 → 补一处替换即可)。

---

### R4 — M3 CLI golden output 破坏(中)

**描述**:M3 把 20+ read-only artifact printer 收敛到 dispatch table。**dispatch handler 的 formatter 实现若与原 inline 实现有任何差异(如 indent 级别 / sort_keys / trailing newline / 等),stdout 输出会 byte-for-byte 不一致**,破坏 public CLI surface 与 `tests/test_cli.py` 中可能存在的 golden output test。

**触发场景**:
- 原 inline 实现是 `print(json.dumps(payload, indent=2))`;Codex 抽 helper 写成 `print(json.dumps(payload, indent=2, sort_keys=True))` — 只多一个 `sort_keys=True` 但输出顺序变化
- 原实现 `print(...)` 末尾 newline 由 `print` 自动加;Codex 改 `sys.stdout.write(...)` + 漏 newline
- 不同 dict.items() 顺序在 Python 3.7+ 已稳定,但若 Codex 不知道改用 `sorted()` 会导致输出差异

**缓解**:
- design_decision §S3.4 强制 Codex 在 M3 完成后 manually 验证 5 个 read-only command 输出 byte-for-byte 一致
- 若 `tests/test_cli.py` 已有 golden output assertion(很可能有部分),pytest 跑全量绿灯就是 byte-for-byte 验证
- M3 review 时 Claude 检查 dispatch table 中每个 entry 的 formatter 实现是否与原 inline 一致(grep `print(json.dumps` 对照)
- 若发现破坏 → 立即回滚或修订 formatter

**回滚成本**:低-中。dispatch table 改动局部,但 cli.py 是大文件,修订需要重新 review M3。最坏情况 = M3 推迟 1 commit。

---

### R5 — M3 argparse 兼容性破坏(低)

**描述**:M3 dispatch table 替换 if-chain 时,**若不小心改了 `task_subparsers.add_parser(...)` 注册顺序 / help text / argument schema,`--help` 输出会变化**,这是 public CLI surface 变更(operator 写脚本依赖 argparse 自动生成 help)。

**触发场景**:
- Codex 抽 dispatch table 时把 parser registration 也"顺手整理"
- 改 subparser 列表顺序导致 `--help` 显示顺序变化

**缓解**:
- design_decision §S3.5 显式声明:M3 **只改 dispatch handler,不改 parser registration**
- M3 review 时 Claude grep `add_parser` 确认 cli.py 中 add_parser 行数 / 顺序与 main 一致

**回滚成本**:低(parser registration 是局部改动,git revert 单段)。

---

### R6 — M2 artifact name 决议变更影响 M3 起点(中)

**描述**:design_decision §S2.3 决议采纳"窄选项 (a) — M2 内不引入 artifact-name registry,留给 M3 dispatch table 内嵌 artifact 名 mapping"。**若 M2 review 阶段 Claude 主线认为应改宽选项 (b) (引入 registry),M3 起点必须重新对齐**(从"内嵌 artifact 名"改为"消费 registry"),M3 工作量从单 commit 增至跨多模块。

**触发场景**:
- M2 review 时 Claude 发现某 callsite 行为对 artifact name 有强 ownership 需求(如 retrieval.py:64-79 的 `STANDARD_SUBTASK_ARTIFACT_NAMES` 与 cli.py 重复 → 必须由 paths.py owner 拥有)
- Human 在 Direction Gate 反馈"M2 应做更深的设计"

**缓解**:
- design_decision §S2.3 已显式锁定窄选项 (a)+ 给充分理由;M2 review 时 Claude 主线应坚持决议(audit_index 推荐"narrowest reversible step")
- 若真的需要改宽选项 → M3 启动前 Codex 先消化 M2 决议变更,M3 工作量重估
- audit_block2 finding 7 + audit_block4 finding 9 backlog 状态:窄选项下标 Partial(留给后续 design phase 引入 registry);宽选项下标 Resolved。窄选项 + Partial 是合理 trade-off,Phase 67 不需要解决一切

**回滚成本**:中。M2 决议变更需要 M3 重做起点设计;但 Phase 67 的 review 分轮机制设计就是为吸收此类变更。

---

### R7 — Phase 67 与候选 O 衔接不畅(低)

**描述**:M2 创建的 `_io_helpers.py` 三个 helper 接受 `Path` 参数。**候选 O 实装 `RawMaterialStore` 接口时,helper 可能需要改为接受 `source_ref` (URI 字符串) + 通过 RawMaterialStore 解析为 bytes**。Phase 67 不解决此扩展。

**触发场景**:
- 候选 O 启动时发现 `_io_helpers` signature 与 RawMaterialStore 接口冲突,需要 wrap 或重写
- 候选 O 实装时 11+ callsite 都需要从 `read_json_or_empty(path)` 改为 `raw_store.read_json_or_empty(source_ref)`,改动量大

**缓解**:
- design_decision §S2.5 明确预留候选 O 衔接:`_io_helpers` 接口足够薄(单 path 参数 + return type),候选 O 时只需 helper 签名变化 + 11 callsite signature 跟随,不需重构其他逻辑
- 候选 O 启动时若发现衔接成本高 → 候选 O 先做接口 design + 反向 deprecate `_io_helpers`(渐进迁移),不必一次性切换

**回滚成本**:零(Phase 67 不涉及候选 O 实装,衔接成本由候选 O 自己承担)。

---

## 总体策略

1. **3 milestone 顺序**(M1 → M2 → M3),无并行,每 milestone Claude review 通过才进下一
2. **M1 风险最低**(纯清理 + 常量命名);M2 风险最高(R1 IO helper 均质化 + R6 artifact name 决议),通过 design_decision §S2.2 authoritative 表 + 锁定窄选项缓解;M3 风险中等(R4 golden output + R5 argparse),通过 byte-for-byte 验证缓解
3. **不触发 model_review**(max risk score = 5,低于 6 阈值;不触动 INVARIANTS / DATA_MODEL / KNOWLEDGE)
4. **review 分轮严格执行**:M1 → review_comments_block_l.md → M2 → review_comments_block_m.md → M3 → review_comments_block_n.md。Codex 等 verdict APPROVE / APPROVE_WITH_CONDITIONS 才进下一 milestone
5. **每 milestone 完成后立即跑全量 pytest**,不积累测试 debt 跨 milestone
6. **Phase 67 不打 tag**(清理 phase 不构成 release 节点);候选 O 启动后视情况考虑

## 与既有 risk 模式的对照

- **类似 Phase 66 audit phase**:Phase 66 是 read-only audit;Phase 67 是 implementation phase。但 review 分轮机制完全沿用(M1/M2/M3 独立 review_comments)
- **不像 Phase 65 truth schema phase**:Phase 65 触动 INVARIANTS P2 + DATA_MODEL §3,需要 model_review + design_audit + 大量回归测试;Phase 67 不触动设计层,仅实装清理
- **新模式**:Phase 67 是首个"三合一大 phase + 严格分 milestone"。审计警告"不应合并"的最弱违反形式;若实施成功,可作为后续类似情况的参考模板。Phase 66 的 read-only audit 是首个非 implementation phase;Phase 67 的"知情合并 + 强 milestone 隔离"是另一种新模式

## 与 INVARIANTS 的对照(本 phase 不触动)

| INVARIANTS 条目 | Phase 67 触动方式 |
|----------------|----------------|
| P1 Local-first / P2 SQLite-primary truth / P3 Truth before retrieval / P4 Taxonomy before brand / P5 Explicit state / P6 Controlled vs black-box / P7 Proposal over mutation / P8 Canonical-write-forbidden | **零触动**。Phase 67 实装清理,不评判 / 不修改 / 不间接影响 INVARIANTS 任何条款 |
| §0 四条规则 / §4 LLM 调用契约 / §5 写权限矩阵 / §7 集中化函数 / §9 不变量守卫 | **零触动**。M1/M2/M3 改动均在实装层,不写 truth、不影响 LLM 调用边界、不引入 §9 守卫新条目 |

## 与 DATA_MODEL.md 的对照(本 phase 不触动)

| DATA_MODEL 条目 | Phase 67 触动方式 |
|----------------|-----------------|
| §3 Schema(全部 namespace) / §4 写入入口 + 白名单 / §5 跨命名空间引用 / §6 文件系统约束 / §7 ID + Actor / §8 Migration / §9 文档接口 | **零触动** |

## 与 KNOWLEDGE.md 的对照(本 phase 不触动)

| KNOWLEDGE 条目 | Phase 67 触动方式 |
|----------------|----------------|
| 三层架构 / Evidence 定义 / Wiki / Canonical 默认入口 / EvidencePack / Storage Backend Independence / Replaceable Components / Anti-Patterns | **零触动** |

候选 O 是 Storage Backend Independence 的实装路径,Phase 67 不涉及。

## Model Review Gate

**默认 skipped**(per kickoff + design_decision):
- 不触动 INVARIANTS / DATA_MODEL / KNOWLEDGE / SELF_EVOLUTION
- 不涉及 schema / CLI / API surface 设计变化(M3 仅 dispatch 重构,public surface 行为不变)
- 不涉及 state transition / truth write path / provider routing policy
- 风险矩阵无 ≥ 6 项
- scope 全为清理 + 实装层重构

`docs/active_context.md` 的 model_review 段记录:

```markdown
model_review:
- status: skipped
- artifact: none
- reason: cleanup phase, no INVARIANTS/DATA_MODEL/KNOWLEDGE impact, no schema/state-transition/CLI surface change, max risk score = 5
```
