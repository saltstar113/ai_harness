# AGENT_LOG.md — Coding Agent Harness 开发日志

> AI4SE 期末项目 A · 颜鑫 · 2026-08
> 作业要求：每条记录包含时间戳与 task 编号、触发的 Superpowers 技能、关键 prompt / context 配置、subagent 输出的关键片段或 commit hash、人工干预的内容与理由、学到的教训。

---

## 2026-08-04 — 项目初始化（T00: 环境准备）

**技能：** 无（手动操作）

**关键 prompt/context：** 新建 GitHub 仓库 `saltstar113/ai_harness`，从 GitHub 市场安装 Superpowers 插件。

**Subagent 输出/commit：** `9051452` — 导入 Superpowers 全部技能文件（55 个文件，9830 行），包括 brainstorming、writing-plans、subagent-driven-development、test-driven-development、systematic-debugging 等。`b286de4` — 切换至官方 plugin 配置。`52bff9c` — 清理手动配置。`a63f1b2` — 清理 hom_require 目录。

**人工干预：** 无。

**学到的教训：** Superpowers 技能文件占用大量 repo 空间（近 10k 行），但这些技能是后续开发的核心工作流依赖。作业要求明确禁止使用现成 agent 编排框架（LangChain 等），Superpowers 是属于"方法论文档"而非"框架代码"，不违反约束。

---

## 2026-08-06 — 需求分析与设计（Brainstorming，3 轮迭代）

**技能：** `brainstorming`

**关键 prompt/context：** 向智能体提供三份作业要求文件（通用要求、A 类项目要求、PROJECT_AGENT_REFERENCE）。要求：输出 SPEC 大纲，覆盖 10 项基本要素 + 领域与机制设计章节。

### 第 1 轮：大纲输出 + 架构质询

**Subagent 输出：** 11 章大纲，完全对齐作业要求。提出 3 个架构决策问题：

| 问题 | 选项 | 我的选择 | 理由 |
|------|------|----------|------|
| 反馈闭环粒度 | A 简单回灌 / B 结构化分类 / C 多轮修正状态机 | **C** | 结构化分类 + 熔断是确定性代码而非提示词，符合作业 A.4-C 判据 |
| 记忆方案 | A Flat Scratchpad / B 结构化 Session Store / C 向量化 RAG | **B** | 结构化 JSON 可在 mock LLM 下 100% 可测试 |
| 治理分类体系 | A 二元 / B 三级 / C 多维度分级 | **C** | 治理是 Main Contribution，多维度规则引擎最能体现工程深度 |

**人工干预：** 选择 C/B/C。无额外修改。

**学到的教训：** 这三个问题定义了我之前没想清楚的关键设计决策。特别是"熔断"机制——此前我只模糊地想过"失败后重试"，但未意识到需要区分"第 1 次全量上下文 → 第 2 次精简 → 第 3 次熔断"的递进策略。

### 第 2 轮：核心三章草稿 + 再次质询

**Subagent 输出：** 功能规约、系统架构、领域与机制设计三章草稿。提出 3 个质询点。

**人工干预：** 修正了 3 个问题：

1. **Shell 命令匹配逻辑 Bug**：智能体初版用 `tokens[0] + re.fullmatch` 匹配。我指出这无法匹配 `rm -rf /` 这类带参数的模式，且会被 `sudo` 前缀绕过。修正为 `re.search(command) or re.fullmatch(pattern, cmd_name)` 双重校验。

2. **文件写入建图保障**：要求在 `write_file` 规约中补充 `target.parent.mkdir(parents=True, exist_ok=True)`，确保写入深层路径时不会因缺少父目录失败。

3. **MockLLM 设计规范化**：要求明确 `ScriptedMockLLM` 采用 `List[Action]` 动作队列注入，`chat()` 按 FIFO 返回，队列耗尽返回 FINISH 信号。

**质询决策：**

| 质询 | 我的决策 |
|------|----------|
| WARN 是否跳过审批环节 | 默认自动执行 + 日志记录；`--strict` 命令行开关升格为 HITL |
| 修正轮次计数单位 | 按"连续同类失败"计数；成功即重置；失败类型变化亦重置 |
| 是否引入 keyring | 放弃 keyring（回避 WSL/D-Bus 依赖），仅用 `.env` + `getpass` |

**学到的教训：** 智能体在架构层面表现优秀，但代码细节需要我纠正。它能画出正确的架构图，但代码级别的逻辑漏洞（Shell 匹配的 `sudo` 绕过）需要我来发现和修正。这印证了作业的核心命题：**工程师的价值不在"写出代码"，而在"判断代码是否正确"**。

### 第 3 轮：签字确认 + 生成完整 SPEC.md

**Subagent 输出：** 完整 SPEC.md（11 章，1169 行）。智能体自行发现并修复 2 个问题：
- 实体关系图 `Session 1 ──── * Turn` 与 `Session` dataclass 矛盾 → 修正为 `Session 1 ──── * Error`
- v1.0 范围决策中声称支持 REPL 模式，但 CLI 规约未定义 → 修正为"仅 `--task` 单次模式"

**人工干预：** 无。这两处是智能体自行发现的。

**学到的教训：** SPEC 自审（Spec Self-Review）机制有效。智能体在生成完整文档后自行检查一致性，发现并修复了 2 个矛盾点。这种"自己检查自己"的纪律在单人项目中尤为珍贵。

---

## 2026-08-06 — 实现计划（Writing-Plans，3 轮迭代）

**技能：** `writing-plans`

**关键 prompt/context：** SPEC.md 作为输入，要求输出细粒度 task 列表，每个 task 包含目标、文件、实现要点、验证步骤（含失败测试代码）、commit 信息。

### 第 1 轮：Task 拆解框架 + 策略质询

**Subagent 输出：** 18 个 task 的框架（7 个 Phase），提出 4 个策略问题：

| 问题 | 我的选择 | 理由 |
|------|----------|------|
| Worktree 粒度（A 每 task / B 每 Phase / C 混合） | **C 混合** | 治理和核心循环独立 worktree，其余 Phase 合并 |
| 治理 task 组织（A 自底向上 / B 自顶向下 / C TDD） | **A 自底向上** | 每个子组件独立可测，T10 集成时已有扎实基础 |
| 测试基础设施（A 独立前置 / B 各模块自带 / C 折中） | **A 独立前置** | 共享 fixture 避免治理模块 4 个 task 的重复代码 |
| AC 优先级（A 编号顺序 / B 模块分组 / C 关键路径优先） | **C 关键路径优先** | 最早在 Phase 5 就能看到端到端闭环 |

### 第 2 轮：完整 Task 列表细化

**Subagent 输出：** 18 个 task 的完整拆解，每个 task 含目标、涉及文件、实现要点、验证步骤（含失败测试的具体代码）、commit 信息。确认：Task 粒度合适、Worktree 分配合理、无需显式重构步骤。

### 第 3 轮：生成 PLAN.md + 质量审查

**Subagent 输出：** 完整 PLAN.md（2442 行）。智能体自行发现并修复 3 个问题：
1. `ApprovalResult` 在 `models.py` 和 `io_interface.py` 中重复定义 → 去重
2. T14 测试从 `src.io_interface` 导入 `RiskInfo`（实际在 `src.models`） → 修正导入路径
3. `run_cli.py` 引用 `DeepSeekClient` 但无 task 实现 → 补充薄封装实现

**学到的教训：** 写作计划期间智能体发现的 3 个问题验证了"先写计划再实现"的价值——这些问题如果在实现阶段才发现，会导致跨分支的返工。PLAN 的质量审查机制是投资回报率最高的环节。

---

## 2026-08-06 — 冷启动验证（§4.5 自我验证）

**技能：** 无（使用与主开发智能体**不同**的 agent，全新会话）

**关键 prompt/context：** 仅提供 SPEC.md + PLAN.md，不提供任何 brainstorming 对话历史。要求：从 PLAN 选 1–2 个 task 自主推进，遇到不确定之处即暂停询问。

**Subagent 行为：** Agent 依次完成 T01-T05，共出现 3 次暂停：

| 暂停点 | Agent 行为 | 分析 |
|--------|-----------|------|
| T02 命名 | "PLAN 里写 `Ver`，SPEC 用 `Verdict`，不一致。我暂停等你确认。" | Agent 正确识别了文档不一致，选择了暂停而非猜测 |
| T01 验证 | `git check-ignore .env` 报错：`fatal: not a git repository` | 记录为 blocker，等待用户决策 |
| T01 验证 | `pytest --collect-only` 报错：pytest 未安装 | 记录为 blocker |

**Subagent 产出片段：** Agent 的 T03 实现存在一个 off-by-one bug：

```python
# Agent 初版（有 bug）
def chat(self, messages):
    self.call_count += 1            # 先递增
    if self.call_count > len(self.queue):
        return {"action": "finish"}
    return self.to_response(self.queue[self.call_count - 1])  # 后减一

# Agent 修复版（2 次迭代后）
def chat(self, messages):
    if self.call_count >= len(self.queue):
        return {"action": "finish"}
    action = self.queue[self.call_count]
    self.call_count += 1            # 后递增
    return self.to_response(action)
```

**人工干预：** 回复"统一用 Verdict，不额外加兼容别名"。Agent 据此实现。

**学到的教训：** 冷启动暴露的 3 个缺陷中，前 2 个是**真正的文档缺陷**——它们在主开发 session 中不会暴露，因为主 agent 和我在 brainstorming 过程中积累了共享的隐性上下文。核心教训：(1) 类型声明和代码示例必须一致；(2) 环境依赖必须显式声明；(3) 冷启动测试是最接近"同侪评审"的机制。详见 SPEC_PROCESS.md 第 6-7 章。

---

## 2026-08-06/07 — Phase 1-2 基础设施（T01-T06）

**技能：** `subagent-driven-development` + `test-driven-development`

**关键 prompt/context：** 向 subagent 提供的 task brief 包含：PLAN.md 中对应 task 的完整描述、涉及文件列表、预期实现要点、TDD 验证步骤（含失败测试的具体代码）。要求：先写测试（红）→ 最小实现（绿）→ commit。

**Worktree 策略：** 两个 worktree 并行：
- `phase1-infra`：T01-T02（串行）
- `phase2-base`：T03-T06（4 个独立 task，由一个 subagent 串行完成）

### T01: 项目脚手架

**Commit：** `66fc7c5`

**Subagent 输出：** 创建 `.gitignore`、`requirements.txt`、`pytest.ini`、`tests/conftest.py`（含 `tmp_workspace` 和 `sample_action` 等 fixture）。

**人工干预：** 无。

### T02: 数据模型

**Commit：** `66fc7c5`

**Subagent 输出：** `src/models.py`（12 个 dataclass + 4 个 enum），`tests/test_models.py`（7 个测试）。

**关键代码片段：**
```python
class Verdict(Enum):
    SAFE = "SAFE"
    WARN = "WARN"
    BLOCK = "BLOCK"

@dataclass
class GuardDecision:
    verdict: Verdict
    matched_rule: str = "default"
    reason: str = ""
```

**人工干预：** 无。Agent 按 PLAN 和冷启动验证结果统一使用 `Verdict`。

### T03: Mock LLM 抽象

**Commit：** `c70229c`

**Subagent 输出：** `src/mock_llm.py`（`ScriptedMockLLM` 类，FIFO 动作队列），`tests/test_mock_llm.py`。

**关键设计决策：** Mock LLM 完全不读取对话上下文，仅按 FIFO 返回预定义动作。确保测试的确定性——移除 LLM 后每个机制仍可通过单元测试验证。

**人工干预：** 无。

### T04: 配置加载

**Commit：** `ddd5663`

**Subagent 输出：** `src/config.py`（`load_rules()` + `BUILTIN_RULES` 硬编码降级），`tests/test_config.py`。

**关键设计决策：** `BUILTIN_RULES` 硬编码确保 YAML 文件缺失时核心机制不依赖配置文件。

**人工干预：** 无。

### T05-T06: 凭据管理 + 会话存储

**Commit：** `fb818e6`

**Subagent 输出：** `src/credential.py`（set/status/clear，getpass 隐式输入，status 不回显明文），`src/session_store.py`（save/load/search，JSON 文件存储），对应测试。

**人工干预：** 无。

**学到的教训（Phase 1-2 整体）：** 4 个并行独立 task 由一个 subagent 串行完成是高效的——因为 task 间无依赖，subagent 可以连续交付而不需要切换上下文。但前提是 PLAN 足够详细：每个 task 的接口边界、测试用例、预期行为都必须明确，否则 subagent 容易偏离。

---

## 2026-08-07 — Phase 3 治理维度（T07-T10，主要贡献）

**技能：** `subagent-driven-development` + `test-driven-development`

**关键 prompt/context：** 向 subagent 提供 PLAN.md 中 T07-T10 的完整描述。强调 strict serial dependency（T07→T08→T09→T10），要求每个 task 独立 commit 且通过测试后才进入下一个。

**Worktree：** `phase3-governance`

### T07: GuardEngine 骨架

**Commit：** `564c6bd`

**Subagent 输出：** `src/guardrail.py` — `GuardEngine` 类，`check()` 方法按 action_type 路由到对应校验逻辑，多规则匹配取最高优先级。

**关键代码片段：**
```python
VERDICT_PRIORITY = {Verdict.BLOCK: 3, Verdict.WARN: 2, Verdict.SAFE: 1}

class GuardEngine:
    def check(self, action: Action) -> GuardDecision:
        # 1. 分类 action type
        # 2. 匹配规则（pattern 优先）
        # 3. 无 pattern 规则取最高优先级
        # 4. 返回 GuardDecision(verdict, matched_rule, reason)
```

### T08: 路径隔离

**Commit：** `62a96f6`

**Subagent 输出：** `validate_path()` 方法，使用 `Path.resolve().is_relative_to()` 进行物理路径校验。

**关键代码片段：**
```python
def validate_path(self, target: str) -> GuardDecision:
    target_path = Path(target)
    if not target_path.is_absolute():
        resolved = (self.workspace / target_path).resolve()
    else:
        resolved = target_path.resolve()
    if not resolved.is_relative_to(self.workspace):
        return GuardDecision(verdict=Verdict.BLOCK, ...)
    return GuardDecision(verdict=Verdict.SAFE, ...)
```

### T09: Shell 双重校验

**Commit：** `5bf73b6`

**Subagent 输出：** `check_shell_command()` 方法，`shlex.split()` 词法解析 + 正则模式匹配双重校验。

**关键代码片段：**
```python
def check_shell_command(self, command: str) -> GuardDecision:
    try:
        tokens = shlex.split(normalized)
    except ValueError:
        return GuardDecision(verdict=Verdict.BLOCK, reason="命令解析失败")
    for rule in shell_rules:
        if re.search(rule.pattern, normalized) or re.fullmatch(rule.pattern, cmd_name):
            return GuardDecision(verdict=Verdict(rule.verdict), ...)
    joined = shlex.join(tokens)
    for rule in shell_rules:
        if re.search(rule.pattern, joined):
            return GuardDecision(verdict=Verdict(rule.verdict), ...)
```

### T10: 状态机集成

**Commit：** `5f9d8b6`

**Subagent 输出：** 完整状态机 + 23 个参数化测试（覆盖 BLOCK/WARN/SAFE 三类动作 + 路径越界 + sudo 绕过 + shell 命令）。

**人工干预：** 无。

**学到的教训：** 自底向上的 TDD（子组件独立可测 → 最后集成）在治理模块中效果显著。每个子组件（路径校验、Shell 校验）在 T10 集成时已有扎实的测试覆盖，23 个参数化测试一次性通过。这验证了"先写测试再实现"的纪律——subagent 在明确的目标（测试通过）下不会偏离。

---

## 2026-08-07 — Phase 4-6 核心循环（T11-T18）

**技能：** `subagent-driven-development` + `test-driven-development`

**Worktree 策略：** 三个 worktree 并行：
- `phase4-executor`：T11（单 task）
- `phase5-core`：T12-T14（严格串行）
- `phase6-io`：T15-T18（串行）

### T11: 工具执行器

**Commit：** `70a23d4`

**Subagent 输出：** `src/executor.py` — 5 个工具（read_file/write_file/execute_shell/run_tests/run_lint），dispatch 路由，mkdir 保障，environ 白名单，原子写入回滚。

**关键代码片段：**
```python
class Executor:
    def dispatch(self, action: Action) -> ToolResult:
        handler = self.tools.get(action.tool)
        if not handler:
            return ToolResult(exit_code=-2, stderr=f"未知工具: {action.tool}")
        return handler(**action.params)
```

### T12: 反馈引擎

**Commit：** `fd263ea`

**Subagent 输出：** `src/feedback.py` — `FeedbackEngine` 类，7 种分类（COMPILE_ERROR/TEST_FAILURE/LINT_ERROR/RUNTIME_ERROR/TIMEOUT/SUCCESS/UNKNOWN_ERROR），3 次熔断，成功重置计数器。

**关键设计：**
```python
# Round 1: 失败 → 注入完整错误上下文
# Round 2: 再次失败 → 注入精简提示（仅 category + 关键错误行）
# Round 3: 仍失败 → 熔断 → HITL
```

### T13: AgentLoop 主循环

**Commit：** `b30308d`

**Subagent 输出：** `src/harness_core.py` — `AgentLoop` 类，依赖注入（llm, guard, executor, feedback, session_store, io），7 步流程，反馈回灌，invalid_json 熔断。

**关键代码片段：**
```python
class AgentLoop:
    def __init__(self, llm, guard, executor, feedback, session_store, io=None, ...):
        # 依赖注入：测试时 llm=MockLLM(), io=SilentIO()
        # 生产时 llm=DeepSeekClient(), io=CliIO()
```

### T14: 集成测试

**Commit：** `b918c21`

**Subagent 输出：** `tests/test_core.py` — 5 个集成测试覆盖完整流程、熔断、反馈回灌、guardrail 拦截。

### T15: CLI 入口

**Commit：** `38ae1d8`

**Subagent 输出：** `run_cli.py` — 命令行解析（--task/--session/--config/--mock/--strict），`DeepSeekClient`，JSON 容错解析（Markdown 提取 + 尾逗号修复）。

### T16-T18: demo.py + CI + README

**Commit：** `903447d`

**Subagent 输出：** `demo.py`（三项机制演示）、`.github/workflows/test.yml`、`README.md`、`install.sh`/`install.ps1`。

**人工干预：** 无。

**学到的教训（Phase 4-6 整体）：** 依赖注入模式让测试变得极其简单——`AgentLoop` 注入 `ScriptedMockLLM` 和 `SilentIO` 后，所有核心流程可在零网络依赖下通过单元测试验证。CLI 的 `--mock` 开关让这个切换对用户透明。

---

## 2026-08-07 — 代码审查与修复

**技能：** `requesting-code-review`

**关键 prompt/context：** 要求审查全部代码的正确性、安全性、完整性。审查范围：所有 src/ 和 tests/ 文件。

**审查发现：**

| 严重性 | 问题 | 位置 | 根因 |
|--------|------|------|------|
| Critical | 反馈上下文未注入 LLM messages | `harness_core.py:73` | `context_for_llm` 已计算但未拼接到 `messages` 列表，导致反馈闭环完全失效 |
| Critical | YAML 正则转义错误 | `guard_rules.yaml` | `C:\\Windows\\` 在 YAML 解析后变成 `C:\Windows\`，正则匹配失败 |
| Important | Action 导入路径错误 | `models.py` | 循环导入导致运行时崩溃 |
| Important | BLOCK 拒绝后未回灌 | `harness_core.py` | 执行被拒绝后拒绝理由未注入下一轮 LLM 上下文 |
| Important | LINT_ERROR 未分类 | `feedback.py` | lint 行号格式未匹配正则，被归入 UNKNOWN_ERROR |

**修复 commit：** `01550a8`（2 Critical），`a3d6e59`（3 Important）

**人工干预：** 全部 5 个修复都是人工定位和修改的。Subagent 的代码审查输出了问题列表和修复建议，但实际的 patch 由我（用户）编写。

**学到的教训：** 代码审查是 AI 协作的"安全网"——subagent 擅长写代码，但容易在反馈闭环的边界条件上犯错。特别是"反馈上下文已计算但未注入"这个 bug，在单测中不易暴露（因为测试直接检查 messages），只有在端到端流程中才被发现。这验证了"代码审查不可跳过"的纪律。

**遗留问题后续修复：** 原始审查报告还列出了 5 个 Important 问题（session_store 未使用、scope 过滤缺失、conventions 模型缺失、重复迭代检测、STM 测试缺口）。这些在后续开发中逐步修复：`bc40762`（session_store 集成 + conventions）、`beb2d6a`（scope 过滤 + STM 测试）、`1aba491`/`7ce2f94`（重复成功检测）。

---

## 2026-08-09 — GUI 测试辅助（非作业要求）

**技能：** 无（手动开发）

**Commit：** `6df9b1c`（GUI 设计文档），`e193b51`（GUI 实现）

**Subagent 输出：** Tkinter GUI，逐轮展示 AgentLoop 运行状态，HITL 审批可视化。

**人工干预：** 无。GUI 是个人调试工具，非作业要求，完全由 subagent 实现。

---

## 2026-08-12 — 真实 API 测试与系统提示词优化

**技能：** 无（手动调试）

**关键 prompt/context：** 使用真实 DeepSeek API 运行 `run_cli.py`，观察 LLM 行为。

**发现的问题与修复：**

| 问题 | 修复 | Commit | 人工干预内容 |
|------|------|--------|-------------|
| DeepSeek 对中文提示词 JSON 格式执行不稳定 | 改为英文提示词 | `9716974` | 人工定位：中文提示词下 LLM 经常输出非 JSON 格式或错误字段名 |
| 无法看到 LLM 的中间输出 | 添加 CLI verbose 模式 | `57b49d8` | 人工设计：`--verbose` 标志显示每轮完整消息 |
| LLM 使用 `file_path`/`file`/`filepath` 而非 `path` | Executor 兼容多种参数名 | `91a984c` ~ `9e78601` | 人工定位：DeepSeek 的 JSON 输出参数名不稳定，需要代码侧兼容 |
| LLM 成功后陷入重复循环（如连续重写同一个文件） | 重复动作检测 + 5 次后强制结束 | `1aba491` ~ `7ce2f94` | 人工设计：`_action_desc()` 排除 content 后检测重复，5 次连续成功则结束 |

**英文提示词关键片段：**
```
You are a coding agent. Available tools: read_file, write_file, execute_shell, run_tests, run_lint.
You MUST respond with ONLY valid JSON, no extra text:
{"action": "tool_name", "params": {"key": "value"}, "reason": "why you chose this action"}
When task is complete: {"action": "finish"}
```

**学到的教训：** DeepSeek 对英文提示词的 JSON 格式执行稳定性显著优于中文。LLM 在成功完成任务后容易陷入"重复成功循环"——它不会主动说"我完成了"，而是继续做看似有用的修改。这需要 harness 侧的强制结束机制来补偿 LLM 的"不会停"缺陷。

---

## 2026-08-12 — 场景化 MockLLM 与测试增强

**技能：** `test-driven-development`

**Commit：** `2062295`，`d33e7b8`，`d625567`

**Subagent 输出：** `ScenarioMockLLM` 类，支持 6 个预定义场景（完整工作流、护栏拦截、熔断、多文件、文件未找到、严格模式），8 个场景测试。

**关键发现：**
- `read_file`/`write_file` 使用 `Path(params["path"])` 相对 CWD → 应改为 `self.workspace / params["path"]`
- 默认 Mock 模式改为治理场景，不再硬编码 `read_file("README.md")`

**人工干预：** 修复 executor 工作区路径问题。这是真实 API 测试中暴露的 bug——子进程的 CWD 与 workspace 不一致导致路径解析错误。

---

## 2026-08-12/13 — 4 个高级治理任务

**技能：** `test-driven-development`

**Commit：** `8ef1093`，`40d6ec3`

**Subagent 输出：**

| Task | 内容 | 关键发现 |
|------|------|----------|
| 1. 软链接逃逸 | 2 个测试（Windows 跳过） | 路径隔离已使用 `Path.resolve()`，软链接攻击在代码层面已防护 |
| 2. Shell 混淆拦截 | `$IFS` 注入修复 + 5 个测试 | **`$IFS` 注入是真实漏洞**：`rm$IFS-rf$IFS/` 绕过了原有正则匹配，修复为 `normalize.replace('$IFS', ' ')` |
| 3. 拒绝回灌自修正 | 场景 + 测试 | HITL 拒绝后 LLM 应提出替代方案，通过场景测试验证 |
| 4. 超时熔断 | 已有测试覆盖 | 无需新增代码 |

**Filesystem 死代码修复：** `40d6ec3` — `guard_rules.yaml` 的 `fs-delete-system` 规则**从未被检查**：代码只匹配 Shell 动作的 pattern，FileSystem 动作的 pattern 被跳过。修复后 Filesystem pattern 规则被正确检查，新增 3 个测试验证。

**学到的教训：** `$IFS` 注入是 Shell 校验中最隐蔽的绕过方式——它不改变命令语义，只是去掉了空格。`normalize.replace('$IFS', ' ')` 修复极其简单，但发现它需要意识到 Shell 变量的注入能力。Filesystem 死代码暴露了"代码审查只覆盖了 Shell 路径，未检查 FileSystem 路径"的盲区。

---

## 2026-08-13 — 5 个高级鲁棒性任务

**技能：** `test-driven-development`

**Commit：** `91fea0b`

**Subagent 输出：**

| Task | 内容 | 新测试 | 关键发现 |
|------|------|--------|----------|
| 1. 环境变量隔离 | 白名单过滤 + 输出脱敏 | 2 | 子进程继承全部父进程环境变量，LLM 可直接读取 `DEEPSEEK_API_KEY` |
| 2. 死循环熔断 | 已有 circuit_breaker | 0 | 3 次同类失败触发熔断，已有测试覆盖 |
| 3. 输出截断 | 3000 chars 头尾采样 | 2 | 超大输出直接发送给 LLM 会溢出上下文窗口 |
| 4. JSON 容错解析 | Markdown 提取 + 尾逗号修复 + 正则兜底 | 6 | LLM 输出的 JSON 经常被 Markdown 代码块包裹或含尾逗号 |
| 5. 原子写入回滚 | `ast.parse` 语法校验 + 备份恢复 | 2 | 文件写入无语法校验，写入无效 Python 代码后无法恢复 |

**环境变量白名单机制：**
```python
_ALLOWED_ENV = {"PATH", "HOME", "USER", "TEMP", "TMP", "PYTHONPATH", "VIRTUAL_ENV", "CWD"}
```

**JSON 容错解析流水线：**
```python
# 1. 提取 Markdown 代码块（如果被包裹）
# 2. 修复尾逗号
# 3. 正则提取 JSON 对象
# 4. json.loads()
```

**学到的教训：** 5 个鲁棒性任务中，环境变量泄漏和 JSON 容错是最有价值的修复。子进程继承环境变量是 Python 的默认行为，容易被忽略。JSON 容错解析则直接决定了 LLM 的可用性——如果 LLM 输出一个被 Markdown 包裹的 JSON 就直接崩溃，用户会认为是"产品坏了"而非"LLM 输出格式不对"。

---

## 2026-08-13 — 遗留问题修复

**技能：** 无（手动修复）

**Commit：** `beb2d6a`

**修复内容：**

| 问题 | 修复 | 新测试 |
|------|------|--------|
| scope 过滤缺失 | `check()` 和 `check_shell_command()` 新增 `scope` 参数 | 4 个 |
| STM 测试缺口 | 7 个新测试覆盖 load/save/errors/conventions/search/corrupt/limit | 7 个 |

**scope 过滤设计：**
```python
def check(self, action: Action, scope: str | None = None) -> GuardDecision:
    # scope=None → 全量匹配（向后兼容）
    # scope="System" → 只匹配 scope 为 System 的规则
```

**测试结果：** 87 → 98 passed, 2 skipped

**人工干预：** 全部修复由人工完成。scope 过滤的接口设计（可选参数保持向后兼容）是人工决策，subagent 可能倾向于破坏性变更。

---

## 2026-08-13 — 文档完善与最终交付

**技能：** 无（手动编写）

**Commit：** `116ee97`（AGENT_LOG 补充），`360246b`（PLAN 更新 + SPEC_PROCESS 补充），`540186d`（AGENT_LOG 最终更新）

**文档完善内容：**

| 文件 | 补充内容 |
|------|----------|
| AGENT_LOG.md | 补充 2026-08-04 早期内容、修正日期错误、新增 scope/STM 和冷启动分析记录 |
| PLAN.md | 测试数 87→98，补充 scope/STM 修复记录 |
| SPEC_PROCESS.md | 新增第 7 章：冷启动 Agent 对话摘要、缺陷分析、修订 Diff、off-by-one 自修复 |
| HANDOFF.md | 新对话快速对齐上下文，避免重复提问 |

**PR 状态：** 6 个 PR 描述已通过 API 补充 Subagent 标注 + 人工修改说明。

---

## 最终交付

| 指标 | 数值 |
|------|------|
| 测试 | 98 passed, 2 skipped（零网络依赖） |
| 源文件 | 25 个核心文件 |
| Commits | 49 个（含 6 个 merge commit） |
| Worktree 分支 | 6 个（phase1-infra ~ phase6-io） |
| PR | 6 个（全部 open，含 Subagent 标注） |
| 测试覆盖 | 治理 33 个，反馈 9 个，执行器 9 个，场景 8 个，JSON 解析 6 个，核心 5 个，等 |

**Superpowers 反思：**

| 维度 | 反思 |
|------|------|
| TDD 在 AI 协作中 | 是放大器而非阻碍。先写测试让 subagent 有明确的目标，减少了"偏离主题"的几率。但测试质量需要人工审查——subagent 覆盖 happy path 但可能遗漏边界条件 |
| Subagent 颗粒度 | 太大的 task 导致 subagent 偏离（如 T13 AgentLoop 包含过多逻辑），太小的 task 产生过多分支管理开销。18 个 task 的粒度是合适的 |
| SPEC/PLAN 质量 | 直接影响实现质量。冷启动验证暴露的 3 个缺陷验证了"规约不清导致 subagent 偏离"的假设 |
| 凭据与分发 | 迫使想清楚了一台全新机器从零运行的完整流程——从 `git init` 到 `pip install` 到 `credential set` |
| Brainstorming 价值 | 3 轮追问迫使在每个设计决策上有明确立场。5 条 AI 建议被推翻修正（keyring 否决、Shell 匹配逻辑修正、WARN 行为修改、REPL 范围移除、修正轮次计数方式）体现了"工程师的价值不在写出代码，而在判断代码是否正确" |
| 冷启动验证 | 单人项目中最接近"同侪评审"的机制，暴露的不是"代码写错了"，而是"你没写下来的假设" |
| 代码审查 | 不可跳过。2 Critical + 5 Important 问题的发现验证了"即使是 AI 写的代码也需要人工审查"的纪律 |
| 真实 API 测试 | 揭示 LLM 行为的不可预测性（参数名不稳定、重复成功循环、中文提示词不稳定），这些在 mock 测试中无法覆盖 |

---

## 2026-08-13/14 — 交付物合规检查与补齐（OpenCode 会话）

**技能：** 无（手动协作）

**关键 prompt/context：** 用户要求逐项检查交付物清单（通用要求 §五）并补齐缺口。上下文：全部 18 个 task 已完成，98 测试全绿，6 个 PR 待 merge。

### 交付物逐项检查

| # | 要求 | 状态 | 处理 |
|---|------|------|------|
| 1 | SPEC.md / PLAN.md / SPEC_PROCESS.md | ✅ | — |
| 2 | 完整源代码（commit/PR 历史，无凭据） | ✅ | `git log -p -- .env` 确认无凭据提交 |
| 3 | 分发产物与说明 | ⚠️ | 需补充 Dockerfile（容器分发） |
| 4 | README.md | ⚠️ | 缺少前置条件表、分发命令、GitLab CI 说明 |
| 5 | AGENT_LOG.md | ✅ | — |
| 6 | `.gitlab-ci.yml` + `unit-test` job | ❌ | 完全缺失；现有 `.github/workflows/test.yml` job 名叫 `test` 而非 `unit-test` |
| 7 | CI/CD 执行记录 | ⚠️ | 推送到 GitLab 后自动生成 |
| 8 | REFLECTION.md | ⚠️ | 待完成（用户后续处理） |
| 9 | 线上部署 URL | ✅ | 方案一：GitHub Release 链接 |

### 修复过程

**Round 1：补齐基础设施（4ee6f42 → dd98e09）**

| 文件 | 变更 | Commit |
|------|------|--------|
| `Makefile` | 新增：test/install/demo/clean/dist 5 个 target | `9963111` |
| `.github/workflows/test.yml` | 新增：3 平台 × 2 Python 矩阵 CI | `9963111` |
| `README.md` | 新增前置条件表（Python/OS/Shell/架构）、分发章节（make dist + 手动构建 + CI 产物）、完善目录结构注释、安全边界补充（路径隔离/命令校验/默认拒绝）、已知限制补充（REPL 模式、Shell 差异） | `dd98e09` |

**Round 2：GitLab CI 对齐（914f063）**

用户指出作业要求 `.gitlab-ci.yml`（而非 `.github/workflows/`），且 job 必须名为 `unit-test`。

| 文件 | 变更 | Commit |
|------|------|--------|
| `.gitlab-ci.yml` | 新增：`python:3.11` 镜像，单一 `unit-test` job | `914f063` |
| `.github/workflows/test.yml` | job 名 `test` → `unit-test` | `914f063` |

**Round 3：治理成果展示 + 容器分发（4efcf63）**

用户指出"已知限制"中"非沙箱"条目自我否定治理成果，要求改写并补充 Dockerfile。

| 文件 | 变更 | Commit |
|------|------|--------|
| `Dockerfile` | 新增：`python:3.11-slim`，WORKDIR /app，ENTRYPOINT run_cli.py | `4efcf63` |
| `README.md` | 已知限制改写："代码级治理（路径隔离 + Shell 双重校验 + scope 过滤 + HITL）"替代"非沙箱"；分发章节新增 Docker 容器方式（build/run/key 配置） | `4efcf63` |
| `Makefile` | 新增 `docker-build`、`docker-run` 两个 target | `4efcf63` |

**Round 4：清理临时文件**

删除 `.superpowers/` 目录（SDD 内部追踪文件，全部 task 已完成，不再需要）。

### 关键讨论

**治理四种方式全覆盖：** 用户确认项目的治理维度覆盖了作业要求的所有四种方式——护栏（规则引擎）、沙箱（路径隔离）、HITL 状态机（审批流）、范围围栏（scope 过滤），而非四种之一。这是项目的主要贡献维度。

**仅 DeepSeek / 无 REPL：** 用户询问这两项是否加分项。结论：不是。`LLMClient` 接口已抽象好，加实现只是体力活；`AgentLoop.run()` 是纯函数，套 REPL 不体现深度。这两项是 SPEC §10.2 明确划入 v1.0 范围外的决策，理由是"聚焦治理主维度"。补上反而弱化 focus。

**Dockerfile 一举两得：** 同时满足 §3.2 容器分发要求 + 消解"非沙箱"限制（推荐 Docker 运行即可获得 OS 级隔离）。

### 学到的教训

1. **交付物清单的逐项核查是最后一道防线。** 作业要求 9 项交付物，即使全部代码已完成，文档层面的缺口（`.gitlab-ci.yml`、README 前置条件、分发命令）仍可能遗漏。在"代码写完"后专门花时间做合规检查是必要的。
2. **"非沙箱"措辞的自我否定。** 原始 README 写"不在沙箱/容器内运行"听起来像安全漏洞，但实际上项目用代码实现了一套完整的治理沙箱。措辞不当会直接削弱评审印象。改写为"代码级治理 + 推荐 Docker 兜底"既诚实又展示了工程深度。
3. **GitHub vs GitLab CI 的命名差异。** NJU GitLab 仓库要求 `.gitlab-ci.yml`，不能仅凭 GitHub Actions 替代。作业明确要求"通过同一个 NJU Git 仓库链接提交"，CI 配置文件必须对齐 GitLab 平台。
4. **作业通用要求是检查清单，不是参考。** 通用要求 §五的 9 项交付物必须逐项对照，不能凭印象。"REFLECTION.md 1500-2500 字"、"`.gitlab-ci.yml` 含 unit-test job"——这些细节如果不逐字核对很容易遗漏。