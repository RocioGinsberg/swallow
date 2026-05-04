---
author: codex
phase: r-entry-real-usage
slice: design-doc-knowledge-chain-and-ui-smoke
status: final
depends_on:
  - docs/active_context.md
  - README.md
  - docs/design/INVARIANTS.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/engineering/ADAPTER_DISCIPLINE.md
---

TL;DR:
本计划不是新 phase,而是 LTO-4 之后的真实使用 R-entry runbook。
目标是用 Swallow 自身设计文档做材料,深测 CLI + knowledge chain + Wiki Compiler + Web UI/nginx/Tailscale 展示链路。
本轮重点记录实际使用问题,不做性能优化、不做 Docker 化、不把反代当作正式远程多用户能力。

# R-entry Real Usage Plan

## 0. 定位

本轮是 **R-entry 真实使用验证**,不是常规开发 phase:

- 不产出 `plan_audit.md` / `review_comments.md` / `closeout.md`
- 不 cut tag
- 不以 pytest 覆盖率为目标
- 不新增产品能力
- 只记录真实使用中的断点、摩擦、缺口和下一轮 Direction Gate 信号

本轮最重要的问题:

1. Swallow 能否用自己的设计文档完成一条真实 knowledge capability chain?
2. CLI 是否足够可操作,输出是否能指导下一步?
3. Web Control Center 是否能浏览同一份 truth,并支撑 operator 复核?
4. Tailscale + nginx 反代是否足够作为个人设备间展示方案?
5. 哪些真实使用问题值得进入下一轮 phase,哪些只是文档/操作习惯问题?

## 1. 非目标

- 不做 Dockerfile。当前先用 host 上的 `swl serve` + host nginx 反代;Docker 会引入 volume、host networking、loopback 访问等额外变量。
- 不把 `swl serve` 直接绑定到 `0.0.0.0` 或 Tailscale IP。`swl serve` 仍只监听 `127.0.0.1`;外层由 nginx 暴露给 Tailscale tailnet。
- 不测试公网访问、不做认证系统、不做多用户语义。
- 不为了测试而 mock lifecycle。R-entry 要真实跑 CLI / UI。
- 不追求全命令覆盖。只覆盖真实知识工作流所需的 operator path。
- 不把本轮发现直接改代码。发现问题先记录,再进入 Direction Gate 决策。

## 2. 环境变量

在仓库根目录执行:

```bash
export WORKSPACE="$PWD"
export BASE=/tmp/swl-r-entry-real-usage
export SWL="swl"

rm -rf "$BASE"
mkdir -p "$BASE"
```

如果本机 shell 找不到 `swl`,改用:

```bash
export SWL=".venv/bin/swl"
```

如果要执行 Wiki real draft、HTTP LLM executor、embedding 或 dedicated rerank,先加载仓库根目录的本机环境配置:

```bash
set -a
source .env
set +a
```

当前实现不会自动读取 `.env`;必须让 shell 环境里存在 `SWL_API_KEY` / `SWL_API_BASE_URL` 等变量后再启动 `swl`。OpenRouter dedicated rerank 的可用配置示例:

```bash
export SWL_RETRIEVAL_RERANK_ENABLED=true
export SWL_RETRIEVAL_RERANK_MODEL=cohere/rerank-v3.5
export SWL_RETRIEVAL_RERANK_URL=https://openrouter.ai/api/v1/rerank
export SWL_RETRIEVAL_RERANK_API_KEY=<openrouter-key>
```

预期:

- `git branch --show-current` 是 `main`
- `git status --short --branch` 干净或只有本轮计划文档变更
- `$BASE` 是一次性 R-entry 数据目录,不会污染仓库 `.swl`

## 3. R0 Preflight

### 命令

```bash
git status --short --branch
git log --oneline -8
$SWL doctor --skip-stack
$SWL --base-dir "$BASE" migrate --status
```

### 观察点

- `doctor --skip-stack` 是否能给出可读诊断,而不是 traceback。
- `migrate --status` 是否能说明 SQLite schema 状态。
- 如果 `swl` 命令不可用,记录安装/venv 问题。

### 停止条件

- CLI 无法启动。
- `migrate --status` 直接异常。
- 当前仓库不在 `main`,或有不明 dirty changes。

## 4. R1 Design-doc Material Selection

本轮先用 3 个文档作为真实知识材料:

```bash
export DOC_INVARIANTS="$WORKSPACE/docs/design/INVARIANTS.md"
export DOC_TEST_ARCH="$WORKSPACE/docs/engineering/TEST_ARCHITECTURE.md"
export DOC_ADAPTER="$WORKSPACE/docs/engineering/ADAPTER_DISCIPLINE.md"
```

### 命令

```bash
ls -lh "$DOC_INVARIANTS" "$DOC_TEST_ARCH" "$DOC_ADAPTER"
```

### 观察点

- 文件路径是否在当前 workspace 内。
- 文档大小是否适合作为 Wiki Compiler source。
- 哪些内容适合作为 canonical knowledge,哪些只是工程操作说明。

## 5. R2 Create Anchoring Task

### 命令

```bash
TASK_ID=$($SWL --base-dir "$BASE" task create \
  --title "R-entry design knowledge chain" \
  --goal "Use Swallow design docs to exercise task, knowledge, wiki, retrieval, and UI operator flows." \
  --workspace-root "$WORKSPACE" \
  --executor note-only \
  --route-mode offline \
  --document-paths "$DOC_INVARIANTS" \
  --document-paths "$DOC_TEST_ARCH" \
  --document-paths "$DOC_ADAPTER" \
  --constraint "Do not auto-promote knowledge; all canonical writes require operator review." \
  --acceptance-criterion "CLI and UI can inspect the same task truth and knowledge artifacts." \
  --priority-hint "Prefer surfacing real operator friction over broad command coverage.")

echo "$TASK_ID"
```

### Follow-up commands

```bash
$SWL --base-dir "$BASE" task list
$SWL --base-dir "$BASE" task inspect "$TASK_ID"
$SWL --base-dir "$BASE" task intake "$TASK_ID"
$SWL --base-dir "$BASE" task control "$TASK_ID"
```

### 观察点

- `task create` 输出是否只有 task id,便于 shell 组合。
- `task inspect` 是否暴露 document paths / planning handoff。
- `task intake` 是否比 `inspect` 更适合看输入边界。
- `task control` 是否能说明当前下一步,还是信息噪音过多。

## 6. R3 Knowledge Ingestion Path

先用无 LLM ingestion 建立 staged knowledge 的基本样本。

### Dry run

```bash
$SWL --base-dir "$BASE" knowledge ingest-file "$DOC_TEST_ARCH" --dry-run --summary
```

### Real ingestion

```bash
$SWL --base-dir "$BASE" knowledge ingest-file "$DOC_TEST_ARCH" --summary
$SWL --base-dir "$BASE" knowledge stage-list --all
```

### Optional direct task knowledge capture

```bash
$SWL --base-dir "$BASE" task knowledge-capture "$TASK_ID" \
  --knowledge-item "R-entry note: TEST_ARCHITECTURE.md is the target standard for helper and fixture organization." \
  --knowledge-stage candidate \
  --knowledge-source "operator:r-entry" \
  --knowledge-retrieval-eligible \
  --knowledge-canonicalization-intent review

$SWL --base-dir "$BASE" task staged --status all --task "$TASK_ID"
```

### 观察点

- ingestion report 是否能解释产生了什么 staged candidates。
- `stage-list --all` 是否足够好找 candidate id。
- `task staged` 与全局 `knowledge stage-list` 的边界是否清楚。
- candidate 文本是否过碎、过长、过多。

## 7. R4 Wiki Compiler Dry-run

先不调用 LLM,只验证 source pack / prompt artifacts。

### 命令

```bash
$SWL --base-dir "$BASE" wiki draft \
  --task-id "$TASK_ID" \
  --topic "Test Architecture" \
  --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md" \
  --dry-run

$SWL --base-dir "$BASE" wiki draft \
  --task-id "$TASK_ID" \
  --topic "Adapter Discipline" \
  --source-ref "file://workspace/docs/engineering/ADAPTER_DISCIPLINE.md" \
  --dry-run

$SWL --base-dir "$BASE" task artifacts "$TASK_ID"
```

### 观察点

- `--dry-run` 输出是否明确没有 staged write。
- prompt pack artifact 是否容易在 CLI / UI 找到。
- source_ref 格式是否直觉化。
- 对 operator 来说,从 dry-run 进入 real draft 的下一步是否明显。

## 8. R5 Wiki Compiler Real Draft

只有在 Provider Router / LLM 环境可用时执行。若不可用,记录为 R-entry 环境问题,不要强行配置。

### 命令

```bash
$SWL --base-dir "$BASE" wiki draft \
  --task-id "$TASK_ID" \
  --topic "Test Architecture" \
  --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md"

$SWL --base-dir "$BASE" wiki draft \
  --task-id "$TASK_ID" \
  --topic "Adapter Discipline" \
  --source-ref "file://workspace/docs/engineering/ADAPTER_DISCIPLINE.md"

$SWL --base-dir "$BASE" knowledge stage-list
```

### 观察点

- LLM 配置缺失时错误是否可理解。
- draft 输出是否能直接拿到 candidate id。
- staged candidate 是否包含 `wiki_mode`、source pack、rationale、relation metadata。
- 生成内容是否真的基于 source,还是泛化/幻觉。

### 停止条件

- LLM 调用失败且错误不可理解。
- 生成 candidate 没有 source anchor / source pack。
- candidate 自动进入 canonical。这个不应发生。

## 9. R6 Operator Review And Promotion

挑一个质量最好的 candidate 做 operator review。

### 命令

```bash
export CANDIDATE_ID=<candidate-id>

$SWL --base-dir "$BASE" knowledge stage-inspect "$CANDIDATE_ID"
$SWL --base-dir "$BASE" knowledge stage-promote "$CANDIDATE_ID" \
  --note "R-entry accepted after source-grounded review."

$SWL --base-dir "$BASE" knowledge stage-list --all
$SWL --base-dir "$BASE" knowledge canonical-audit
```

### 如果 candidate 质量不好

不要为了通过流程而 promotion。改用:

```bash
$SWL --base-dir "$BASE" knowledge stage-reject "$CANDIDATE_ID" \
  --note "R-entry rejected: insufficient grounding or poor operator usefulness."
```

### 观察点

- `stage-inspect` 是否足够支撑 review 决策。
- preflight notice 是否清楚。
- `stage-promote` 是否明确 canonical id。
- `canonical-audit` 是否能解释 registry 健康状态。
- reject 路径是否同样清晰。

## 10. R7 Retrieval / Task Run Smoke

用已积累 knowledge 检查 task run 和 retrieval/report surface。

### 命令

```bash
$SWL --base-dir "$BASE" task run "$TASK_ID" --executor note-only --route-mode offline
$SWL --base-dir "$BASE" task inspect "$TASK_ID"
$SWL --base-dir "$BASE" task control "$TASK_ID"
$SWL --base-dir "$BASE" task artifacts "$TASK_ID"
$SWL --base-dir "$BASE" task knowledge-review-queue "$TASK_ID"
```

### 观察点

- note-only/offline path 是否仍真实跑 lifecycle。
- retrieval / grounding / knowledge artifacts 是否出现在 grouped artifacts 中。
- `task inspect` 与 `task control` 是否重复过多。
- 如果没有 retrieval 命中,输出是否能解释原因。

## 11. R8 Web UI Local Smoke

先本机 UI,不要直接上 Tailscale。

### 启动

```bash
$SWL --base-dir "$BASE" serve --host 127.0.0.1 --port 8037
```

打开:

```text
http://127.0.0.1:8037
```

### UI 检查项

- task list 能看到 `TASK_ID`
- task detail 能打开
- events / artifacts / knowledge sections 能加载
- promoted/rejected staged candidates 能在 UI 中看出状态
- artifact 内容可读,尤其是 wiki prompt/result artifacts
- UI 的 action eligibility 不与 CLI `task control` 矛盾
- 浏览器 console / network 无明显 500 或 JSON parse error

### 观察点

- UI 是否能替代常用 CLI inspect,还是只能辅助浏览。
- 哪些信息 CLI 清楚但 UI 不清楚。
- 哪些信息 UI 清楚但 CLI 难找。

## 12. R9 Tailscale + nginx Reverse Proxy Smoke

### 推荐拓扑

```text
另一台 Tailscale 设备浏览器
        |
        | http://<swallow-host-tailscale-ip>:8080
        v
Swallow 主机 nginx:8080
        |
        | proxy_pass http://127.0.0.1:8037
        v
swl serve --host 127.0.0.1 --port 8037
```

### nginx config sketch

把 `100.x.y.z` 换成 Swallow 主机的 Tailscale IP:

```nginx
server {
    listen 100.x.y.z:8080;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8037;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Smoke commands

Swallow 主机:

```bash
$SWL --base-dir "$BASE" serve --host 127.0.0.1 --port 8037
```

另一台 Tailscale 设备:

```text
http://100.x.y.z:8080
```

### 观察点

- nginx 是否能访问 upstream `127.0.0.1:8037`。
- 静态资源是否完整加载。
- API 请求是否仍指向同 origin,没有跨域问题。
- 另一台设备上 task/artifact/knowledge 浏览是否可用。
- 远端 UI 操作是否让人误以为这是多用户/公网能力。

### 停止条件

- 需要把 `swl serve` 绑定到非 loopback 才能工作。不要这样做;先修 nginx。
- 需要 Docker 才能跑通。先记录问题,不要在 R-entry 中引入 Dockerfile。
- tailnet 内有非可信用户但没有 ACL/basic auth。

## 13. Issue Log Template

执行时把问题按以下格式追加到临时记录,建议路径:

```bash
mkdir -p "$BASE/notes"
touch "$BASE/notes/r-entry-issues.md"
```

模板:

```markdown
## <short-title>

- step: R<N>
- surface: CLI | UI | nginx | knowledge | wiki | retrieval | docs
- severity: blocker | concern | nit
- command/url:
- expected:
- actual:
- reproduction:
- likely category:
  - docs only
  - CLI ergonomics
  - UI visibility
  - knowledge quality
  - source grounding
  - environment/setup
  - candidate for next phase
- notes:
```

## 14. Completion Criteria

本轮 R-entry 完成条件:

- 至少创建 1 个真实 task。
- 至少 ingest 或 capture 1 份设计文档相关 staged knowledge。
- 至少跑 1 次 Wiki Compiler dry-run。
- 如 LLM 环境可用,至少生成 1 个 real wiki staged candidate。
- 至少 promote 或 reject 1 个 candidate,并说明原因。
- CLI 能 inspect/control/artifacts 同一 task。
- 本机 UI 能浏览同一 task。
- nginx/Tailscale 至少完成静态 UI + task detail smoke;如失败,记录具体失败点。
- 产出一份 issue log,用于下一轮 Direction Gate。

## 15. 结果判定

R-entry 成功不等于“没有问题”。成功标准是:

- 问题被定位到具体 surface / command / step。
- 没有违反核心不变量。
- 没有出现测试数量减少、truth 被绕过写入、自动 promotion 等红线。
- 能回答下一轮最应该修什么。

R-entry 后建议把真实问题分成三类:

1. **立即修的小 UX/文档问题**:命令提示、README runbook、错误信息。
2. **下一 phase 候选**:UI visibility、knowledge review ergonomics、source grounding report、nginx-local deployment recipe。
3. **暂不做**:Docker 化、多用户认证、公网部署、性能优化。
