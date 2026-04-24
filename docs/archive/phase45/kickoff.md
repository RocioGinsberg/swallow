---
author: claude
phase: 45
slice: eval-baseline-deep-ingestion
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase44/closeout.md
  - .agents/shared/rules.md
---

> **TL;DR** Phase 45 建立 eval 基础设施（`tests/eval/` + pytest mark），为 Ingestion 降噪和 Meta-Optimizer 提案建立质量基线，同时深化 Ingestion 支持对话树上下文还原。3 个 slice，低-中风险。

# Phase 45 Kickoff: Eval 基线 + 深度摄入 (Eval Baseline & Deep Ingestion)

## Track

- **Primary Track**: Retrieval / Memory
- **Secondary Track**: Evaluation / Policy

## 目标

1. 建立 Eval-Driven Development 基础设施，为两个前置依赖模块建立质量基线
2. 深化 Ingestion Specialist，支持还原外部对话的上下文结构（对话树 / 多轮决策链）

具体目标：

1. **S1**: 建立 `tests/eval/` 目录 + pytest mark 配置 + Ingestion 降噪质量 eval（golden dataset，precision/recall 基线）+ Meta-Optimizer 提案质量 eval（scenario-based）
2. **S2**: 深化 Ingestion Parser，支持 ChatGPT 对话树结构还原（parent-child threading）和多轮决策链提取
3. **S3**: 新增 `swl ingest --summary` 模式，产出结构化摘要报告（决策清单 / 约束清单 / 被否方案），供 operator 快速审阅摄入质量

## 非目标

- **不引入 LLM 辅助降噪**：降噪仍为规则式，本阶段通过 eval 量化现有规则质量，为未来是否引入 LLM 降噪提供数据依据
- **不引入 eval 框架/平台**：纯 pytest + golden fixture，不引入 Langsmith / Braintrust 等第三方
- **不做自动化晋升流**：Ingested 知识仍需手动触发 Librarian 审查，自动触发留待后续
- **不做 RAG 质量 eval**：当前无 embedding 模型接入，RAG eval 待引入真实向量检索后再建立
- **不做 Literature Specialist**：领域 RAG 模块独立于 Ingestion 深化，留待后续 phase

## 设计边界

### S1: Eval 基础设施 + 质量基线

#### 目录结构

```
tests/
  eval/
    __init__.py
    conftest.py              # pytest mark 注册 + 公共 fixture
    fixtures/
      chatgpt_golden.json    # 标注过的 ChatGPT 导出样本
      claude_golden.json     # 标注过的 Claude Web 导出样本
      meta_optimizer_scenarios/
        high_failure_rate.jsonl     # 场景 1：某路由失败率 50%
        cost_spike.jsonl            # 场景 2：成本骤升
        healthy_baseline.jsonl      # 场景 3：全部健康
    eval_ingestion_quality.py
    eval_meta_optimizer_proposals.py
```

#### pytest 配置

```ini
# pyproject.toml 或 pytest.ini
[tool.pytest.ini_options]
markers = ["eval: quality evaluation tests (deselected by default)"]
addopts = "-m 'not eval'"
```

默认 `pytest` 不跑 eval，`pytest -m eval` 单独触发。

#### Ingestion 降噪 eval

**Golden dataset 规格**：
- 3-5 个真实（或高仿真）ChatGPT / Claude Web / Open WebUI 导出文件
- 每个文件人工标注：每轮 turn 标记 `keep` / `drop`
- eval 跑 `filter_conversation_turns()`，对比产出 fragment 与标注

**指标**：
- **Precision**: 保留的 fragment 中，确实应保留的比例（目标 ≥ 0.80）
- **Recall**: 应保留的 turn 中，被正确保留的比例（目标 ≥ 0.70）
- 首版保守：高召回低精度可接受（宁可多留不误删）

#### Meta-Optimizer 提案 eval

**Scenario 规格**：
- 3 个 event log scenario（JSONL），每个含 10-20 条事件
- 人工标注每个 scenario 的"期望提案"（如"应建议审查 route X 的失败率"）

**指标**：
- 实际提案覆盖了期望提案的比例
- 不产出纯噪音提案（与 scenario 无关的建议）

### S2: 对话树上下文还原

**当前问题**：Phase 39 的 ChatGPT 解析器按 `create_time` 排序提取 turn，丢失了对话树结构。ChatGPT 的 `mapping` 实际是一棵树（每个 node 有 `parent` 指针），用户可能在同一对话中有多条分支（"regenerate" 后的不同回复路径）。当前实现把所有分支平铺成线性序列，导致：
- 被否定的分支（用户 regenerate 后放弃的回复）混入有效片段
- 决策链断裂（"先说 A 方案 → 否定 → 改用 B 方案"变成"A 和 B 并列"）

**修复方案**：

在 `parse_chatgpt_export()` 中：
1. 构建 parent-child 树结构
2. 找到从 root 到最后一个 leaf 的**主路径**（longest path / last-modified path）
3. 侧枝上的 turn 标记 `metadata["branch"] = "abandoned"`
4. `filter_conversation_turns()` 中对 `branch=abandoned` 的 turn 应用更激进的过滤（仅保留含明确"否定"/"放弃"语义的 turn，作为"被否方案"记录）

**不影响**：Claude Web / Open WebUI / Markdown 解析器（它们的导出本身是线性的）。

### S3: `swl ingest --summary` 结构化摘要

**新增 CLI 参数**：`swl ingest <file> --summary`

在正常 ingest 流程之后，追加输出一份结构化摘要：

```markdown
# Ingestion Summary

## Decisions (3)
- 决定保持 staged review 手动执行
- 决定采用 B 方案替代 A 方案
- 决定不做实时同步

## Constraints (2)
- 约束：不扩展 Web 控制中心
- 约束：保持本地优先

## Rejected Alternatives (1)
- A 方案（被 regenerate 否定）

## Statistics
- total_turns: 120
- kept_fragments: 15
- dropped_chatter: 80
- abandoned_branches: 25
- precision_estimate: N/A (需 golden dataset)
```

分类基于 `ExtractedFragment.signals`：含 `keyword` 且匹配"决定/decision" → Decisions，匹配"约束/constraint" → Constraints，含 `branch=abandoned` → Rejected Alternatives。

### 与现有模块的接口

- **`tests/eval/`**：新增目录，不修改现有 `tests/` 下的任何测试
- **`ingestion/parsers.py`**：修改 `parse_chatgpt_export()` 支持对话树还原
- **`ingestion/filters.py`**：新增 `branch=abandoned` 过滤逻辑
- **`ingestion/pipeline.py`**：新增 `build_ingestion_summary()` 函数
- **`cli.py`**：`swl ingest` 新增 `--summary` 参数
- **`pyproject.toml`**：新增 eval marker 配置

## Slice 拆解

### S1: Eval 基础设施 + 质量基线

**目标**：建立 `tests/eval/` + pytest mark + Ingestion eval + Meta-Optimizer eval。

**影响范围**：新增 `tests/eval/` 目录，修改 `pyproject.toml`

**风险评级**：
- 影响范围: 1 (新增独立目录)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (仅调用已有函数)
- **总分: 3** — 低风险

**验收条件**：
- `pytest` 默认不执行 eval 测试
- `pytest -m eval` 执行 eval 测试
- Ingestion eval：precision ≥ 0.80 / recall ≥ 0.70（基于 golden dataset）
- Meta-Optimizer eval：3 个 scenario 的期望提案覆盖率 ≥ 2/3
- golden dataset fixture 文件存在且格式合理

### S2: ChatGPT 对话树上下文还原

**目标**：`parse_chatgpt_export()` 支持 parent-child 树构建 + 主路径提取 + 侧枝标记。

**影响范围**：修改 `ingestion/parsers.py`，修改 `ingestion/filters.py`

**风险评级**：
- 影响范围: 2 (解析 + 过滤两个模块)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (树结构算法 + 对话语义判断)
- **总分: 5** — 中风险

**验收条件**：
- 含 regenerate 分支的 ChatGPT 导出正确识别主路径 vs 侧枝
- 侧枝 turn 的 `metadata["branch"]` 标记为 `"abandoned"`
- filter 对 abandoned turn 应用更激进过滤
- 现有 ChatGPT 解析测试通过（向后兼容：无分支的导出行为不变）
- S1 的 Ingestion eval 在新解析器下 precision/recall 不低于基线

### S3: `swl ingest --summary` 结构化摘要

**目标**：新增 `build_ingestion_summary()` + CLI `--summary` 参数。

**影响范围**：修改 `ingestion/pipeline.py`，修改 `cli.py`

**风险评级**：
- 影响范围: 1 (新增函数 + CLI 参数)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (基于 fragment signals 分类)
- **总分: 3** — 低风险

**验收条件**：
- `swl ingest <file> --summary` 输出包含 Decisions / Constraints / Rejected Alternatives / Statistics 四节
- 分类基于 fragment signals 正确映射
- 无 fragment 时显示空状态
- 全量 pytest 通过

## Slice 依赖

```
S1 (Eval 基础设施) — 独立，但为 S2 提供质量基线
S2 (对话树还原) — 依赖 S1 的 eval 验证质量不退化
S3 (结构化摘要) — 依赖 S2 的 branch 标记
```

建议顺序：S1 → S2 → S3。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 1 | 1 | 1 | 3 | 低 |
| S2 | 2 | 1 | 2 | 5 | 中 |
| S3 | 1 | 1 | 1 | 3 | 低 |
| **合计** | | | | **11/27** | **低-中** |

主要风险在 S2 的树结构算法和对话语义判断。S1/S3 为低风险新增代码。

## 完成条件

1. `tests/eval/` 目录 + pytest mark 配置可用
2. Ingestion 降噪 eval 建立基线：precision ≥ 0.80 / recall ≥ 0.70
3. Meta-Optimizer 提案 eval 建立基线：3 个 scenario 覆盖率 ≥ 2/3
4. ChatGPT 对话树还原：主路径 / 侧枝正确区分
5. `swl ingest --summary` 输出结构化摘要
6. 全量 pytest 通过（默认不含 eval），`pytest -m eval` 通过
7. 无回归

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase45-eval-deep-ingestion`
- 理由: 新增 eval 基础设施 + Ingestion 深化，应在 feature branch 上进行
- 建议 PR 范围: S1 + S2 + S3 合并为单 PR
