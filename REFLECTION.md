# REFLECTION.md — 反思报告

> AI4SE 期末项目 A · 颜鑫 · 2026-08

---

## 1. 哪些 Superpowers 技能发挥了最大作用？

### 1.1 最大作用：brainstorming（3 轮迭代）

three rounds of brainstorming were the single highest-ROI phase of the entire project. its
HARD-GATE mechanism prevented any "skip directly to coding" impulse. the agent
proactively asked 3 architecture questions (feedback granularity, memory strategy, governance
taxonomy) before i had even articulated them myself. each forced a conscious design decision
rather than a "let's just start coding" intuition.

concrete evidence: the agent's proposed Shell matching logic (`tokens[0] + re.fullmatch`) had a
security-critical `sudo` bypass bug. i caught it in round 2 review because the
"chunked presentation + sign-off" workflow let me deep-dive on one section at a time. had the
agent generated the full 11-chapter spec in one shot, i would almost certainly have missed it.

### 1.2 第二作用：subagent-driven-development（6 个 worktree 分支）

parallel execution across 6 git worktrees compressed what would have been a 2-week serial
effort into ~2 days. each subagent received a task brief extracted from PLAN.md, worked
independently, and produced commits that merged cleanly. the key enabler was the PLAN.md task
granularity—each task was self-contained enough that subagents rarely needed cross-branch
coordination.

### 1.3 第三作用：requesting-code-review（1 次）

the review caught 2 Critical bugs (feedback context not injected into LLM messages, YAML
regex escaping broken) and 5 Important issues. the Critical bug where `context_for_llm` was
computed but never appended to `messages` would have silently broken the entire feedback
loop—every test would pass (they test individual components), but the agent would never learn
from its mistakes in production.

### 1.4 第三作用：cold-start validation（§4.5）

not technically a skill, but the most valuable quality signal. a fresh agent running on SPEC
+ PLAN alone hit 3 blockers, two of which were genuine documentation defects (type
declaration inconsistency, missing `git init`). this is the closest thing a solo project gets
to peer review.

---

## 2. 哪些技能"形式大于实质"？

### 2.1 finishing-a-development-branch

the skill's workflow assumes a multi-developer team with PR review, CI checks, and
deployment pipelines. in a solo project, "finishing" a branch meant `git merge` and `git
branch -d`. the skill's checklist of "verify all tests pass, review diff, update CHANGELOG"
was redundant with the TDD discipline already in place.

### 2.2 verification-before-completion

the skill's instruction to "run verification commands and confirm output before making any
success claims" overlaps 100% with the TDD cycle. after every commit, `pytest` was already
running. the skill added no new information.

### 2.3 writing-skills

this skill was loaded but never invoked—it's a meta-skill for creating new skills, not
relevant to building a coding agent harness.

### 2.4 判断标准

a skill is "形式大于实质" when: (a) its instructions overlap with a discipline already
enforced by TDD, or (b) it assumes a team context that doesn't apply to a solo project. the
skills that added real value were those that forced a decision before action (brainstorming),
parallelized independent work (subagent-driven), or caught errors after the fact (code review).

---

## 3. TDD 在 AI 协作下是阻碍还是放大器？

**放大器，但有前提条件。**

### 3.1 为什么是放大器

- **明确的目标**：subagent 拿到"先写这个测试，让它失败，然后实现"的指令后，方向极其明确。它不会花时间"理解需求"或"探索代码库"，而是直接定位到测试文件，写断言，跑测试，实现最小代码。
- **自我纠错**：冷启动 agent 在 T03 实现中写的 off-by-one bug（`call_count` 先递增后减一），是通过运行自己的测试发现的，并在 2 次迭代内修复。没有 TDD，这个 bug 会进入主仓库。
- **防止偏离**：subagent 在实现过程中有时会"想多了"——加一个 PLAN 没提到的功能。测试失败（因为新功能引入了新测试）会立刻把它的注意力拉回 PLAN 的范围。

### 3.2 前提条件

- **测试必须由人审查**：subagent 写的测试覆盖了 happy path 但可能遗漏边界条件。典型例子：Shell 匹配的 `sudo` 绕过——subagent 写的测试只覆盖了 `rm -rf /`，没有覆盖 `sudo rm -rf /`。这需要我作为 reviewer 在测试文件中补充边界条件。
- **测试必须足够具体**：如果 PLAN 中写"测试反馈引擎"，subagent 可能只写 1 个测试。如果 PLAN 中写"测试分类 TEST_FAILURE→exit_code=1, stderr=AssertionError"，subagent 会写 5 个测试覆盖所有分类。

### 3.3 结论

TDD 在 AI 协作下不是阻碍——subagent 很乐意写测试。问题在于测试的**质量**而非**意愿**。TDD 的纪律（红→绿→重构）让 subagent 的方向感极强，但测试的边界条件需要人工补充。

---

## 4. Subagent-driven 工作流能让智能体自主运行多久？

**在 SPEC 和 PLAN 质量足够高时，一个 subagent 可以自主完成 2-4 个 task（约 1-2 小时）而不偏离主题。**

具体数据：

| 工作复杂度 | 自主运行时间 | 偏离情况 |
|-----------|-------------|---------|
| 单 task（如 T11 工具执行器） | ~30 min | 无偏离 |
| 串行 4 task（如 T07-T10 治理） | ~1.5 hr | 无偏离——严格串行依赖确保前一个 task 的输出是后一个的输入 |
| 并行 4 task（如 T03-T06 基础模块） | ~1 hr | 轻微偏离：subagent 在 T04 完成后尝试优化 T03 的 Mock LLM 设计，被 PLAN 的 task 边界拉回 |
| 串行 3 task（如 T12-T14 核心循环） | ~1.5 hr | 中等偏离：T13 AgentLoop 的复杂度导致 subagent 在"依赖注入"和"反馈回灌"的实现细节上多做了几轮迭代 |

### 4.1 偏离的根因

偏离几乎总是发生在**task 边界模糊**的地方。T13 AgentLoop 是最大的 single task——它同时涉及 LLM 调用、guard 集成、feedback 回灌、HITL 审批、停机判断。subagent 在处理"反馈回灌"时多做了 2 轮迭代，因为 PLAN 中"反馈上下文注入 LLM messages"的具体实现方式不够明确。

### 4.2 结论

subagent 可以自主运行 1-2 小时而不偏离，前提是 task 粒度足够细（每个 task 只做一件事）且 PLAN 对接口边界的描述足够具体。偏离通常发生在"这个 task 到底该做什么"不明确的时候。

---

## 5. 什么样的 task 颗粒度最优？

**最优粒度："一个人能在 30 分钟内手写完成"的单元。**

具体标准：

| 判断标准 | 好例子 | 坏例子 |
|----------|--------|--------|
| 单一职责 | T08（路径隔离）— 只做 `validate_path()` | T13（AgentLoop）— 同时做 LLM 调用、guard 集成、feedback 回灌、HITL 审批、停机判断 |
| 接口明确 | T11（工具执行器）— 输入 Action，输出 ToolResult | T13 — 输入 Task + Session，输出 TaskResult，但中间涉及 5 种外部依赖 |
| 可独立测试 | T09（Shell 校验）— 直接调用 `check_shell_command()` | T13 — 需要注入 MockLLM + SilentIO + 构造 Session 才能测试 |
| PLAN 覆盖度 | T04（配置加载）— PLAN 有 3 步实现 + 4 个测试用例 | T13 — PLAN 有 7 步但"反馈回灌"的细节只写了 1 行 |

**T13 是反面教材：** 它太大、太复杂，导致 subagent 在实现中多做了 2 轮迭代。如果重做，我会拆成 T13a（AgentLoop 骨架 + 工具分发）、T13b（反馈回灌 + 停机判断）、T13c（HITL 审批集成）。

---

## 6. SPEC / PLAN 质量如何影响实现质量？

**举一个具体案例：冷启动验证暴露的 `GuardDecision.verdict` 类型不一致。**

### 6.1 问题

SPEC 第 6 章数据模型声明：
```python
class GuardDecision:
    verdict: str  # SAFE | WARN | BLOCK
```

但 SPEC 第 11 章和 PLAN 的所有代码示例都使用：
```python
GuardDecision(verdict=Ver.BLOCK, ...)
```

冷启动 agent 在 T02 实现时暂停提问："PLAN 里写 `Ver`，SPEC 用 `Verdict`，不一致。我该用哪个？"

### 6.2 如果 agent 没暂停

如果这是一个"不暂停就猜"的 agent，它可能选择 `str` 类型（因为 SPEC 数据模型是权威来源）。这会直接导致 `guardrail.py` 中所有枚举比较逻辑失效：

```python
# 如果 verdict 是 str，这段代码会崩溃
if path_decision.verdict == Verdict.BLOCK:  # AttributeError: 'str' has no attribute 'BLOCK'
```

### 6.3 根因

主开发 agent 和我在 brainstorming 过程中积累了共享的隐性上下文——"我们都知道 `Verdict` 就是枚举"。但 PLAN 是给陌生 agent 的执行手册，必须从零开始描述每一步。类型声明和代码示例必须一致，否则对陌生 agent 是歧义源。

### 6.4 修复

SPEC 第 6 章：`verdict: str` → `verdict: Verdict`。PLAN 和 SPEC 统一使用枚举类型。

### 6.5 教训

"规约不清晰"在 subagent 最集中的表现是**类型不一致**和**环境假设**。这两个问题在主开发会话中不会暴露（因为主 agent 有共享上下文），但会在冷启动验证中被陌生 agent 的每个"暂停提问"处暴露。

---

## 7. 最有效的 prompt / context 策略是什么？

### 7.1 策略一：英文提示词（对 LLM）

**为什么有效：** DeepSeek 对英文 JSON 指令的执行稳定性显著优于中文。中文提示词下 LLM 经常输出非 JSON 格式（如 `{action: "read_file", ...}` 少了引号）或错误字段名（如 `filename` 而非 `path`）。

**关键片段：**
```
You are a coding agent. Available tools: read_file, write_file, execute_shell, run_tests, run_lint.
You MUST respond with ONLY valid JSON, no extra text:
{"action": "tool_name", "params": {"key": "value"}, "reason": "why"}
When task is complete: {"action": "finish"}
Do NOT include markdown, backticks, or any text outside the JSON object.
```

**效果：** 切换英文提示词后，JSON 格式正确率从约 60% 提升到约 95%。

### 7.2 策略二：task brief 包含完整测试用例（对 subagent）

**为什么有效：** subagent 拿到"先写这个测试，让它失败，然后实现"的指令后，方向极其明确。它不会花时间"理解需求"或"探索代码库"，而是直接定位到测试文件，写断言，跑测试，实现最小代码。

**关键片段（来自 PLAN.md T11 task brief）：**
```python
# Step 1: 写失败测试
def test_read_file(tmp_path):
    executor = Executor(workspace=tmp_path)
    (tmp_path / "test.txt").write_text("hello")
    result = executor.dispatch(Action(tool="read_file", params={"path": "test.txt"}))
    assert result.stdout == "hello"
    assert result.exit_code == 0
```

### 7.3 策略三：分块签字而非一次性交付（对 brainstorming agent）

**为什么有效：** 核心三章（功能规约、系统架构、领域与机制设计）先草稿→签字→再生成其余 8 章。每一轮我都有机会在局部范围内深入质询，而非面对一整份文档无从下手。这让我在第二轮发现了 Shell 匹配的逻辑 Bug。

### 7.4 策略四：`--verbose` 模式（调试用）

**为什么有效：** 真实 API 测试时，LLM 的中间输出（它到底返回了什么 JSON）是调试的关键。不加 `--verbose` 时只能看到最终结果，加了之后能看到每轮完整的 messages 和 LLM 响应。这帮我发现了参数名不一致（`file_path` vs `path`）和重复成功循环两个问题。

---

## 8. 凭据与分发的要求迫使你想清楚了什么？

### 8.1 凭据

**迫使想清楚的问题：** 一台全新机器，从零开始，如何安全地配置 API Key？

- `.env` 明文存储的风险：任何对文件系统有读权限的进程均可读取。我在 README 和 SPEC 中明确标注了这个风险，但没有试图"解决"它（因为解决需要操作系统级加密，超出项目范围）。
- `getpass` 的跨平台兼容性：`getpass` 在 Windows/Linux/macOS 上行为一致，但 WSL 环境下需要特殊处理。最终选择不处理 WSL 特殊 case，在文档中标注已知限制。
- 子进程环境变量泄漏：`subprocess.run()` 默认继承父进程的全部环境变量，包括 `DEEPSEEK_API_KEY`。这迫使我在 executor 中实现了环境变量白名单过滤。
- 输出脱敏：即使 key 不在代码中，它可能出现在 LLM 输出或 shell 命令输出中。这迫使我在 executor 中实现了正则脱敏（`sk-[a-zA-Z0-9]{20,}` → `***REDACTED***`）。

**原本会忽略的问题：** 如果没有"凭据"这条要求，我大概率不会想到子进程环境变量泄漏和输出脱敏。这两个问题不在"安全"的典型讨论范围内（大家通常只关心 `.env` 在 `.gitignore` 中），但在真实使用场景中，它们比 Git 泄漏更隐蔽。

### 8.2 分发

**迫使想清楚的问题：** 另一台机器要运行这个项目，需要什么？

- `install.sh` / `install.ps1` 的完整流程：从 `python3 -m venv .venv` 到 `pip install -r requirements.txt` 到 `python run_cli.py credential set`。这迫使我把"环境配置"显式化——在此之前，我自己的机器上已经有 Python 3.11+、pytest、httpx 等，从未想过"从零开始"需要什么。
- 跨平台 Shell 差异：`install.sh`（bash）和 `install.ps1`（PowerShell）的语法完全不同。这迫使我在 CI 中同时配置 Ubuntu 和 Windows 两个 runner。
- 不支持 Python 3.10：因为依赖 `pathlib.is_relative_to`（Python 3.9+ 才引入）和 `dataclasses` 标准库，最低版本要求 Python 3.11。这迫使我在 README 和 SPEC 中明确声明版本约束。

**原本会忽略的问题：** 如果没有"分发"这条要求，我大概率只会写一个 `pip install -r requirements.txt` 的 README 注释，不会考虑跨平台安装脚本、CI 多平台测试、版本约束声明。

---

## 9. 如果重做你会改变什么？

### 9.1 拆细 T13 AgentLoop

T13 是最大的单个 task，它同时涉及 LLM 调用、guard 集成、feedback 回灌、HITL 审批、停机判断。拆成 3 个 task（T13a 骨架 + 分发、T13b 反馈回灌 + 停机、T13c HITL 集成）会显著减少 subagent 的偏离。

### 9.2 先做真实 API 测试，再做高级治理任务

当前流程是：mock 测试全部通过 → 代码审查 → 高级治理任务 → 真实 API 测试。这导致真实 API 测试中发现的 10+ 个问题（英文提示词、参数名兼容、重复成功循环、invalid_json 熔断等）在高级治理任务之后才修复，部分修复影响了高级治理任务的代码。

如果重做，我会在代码审查后立即做真实 API 测试，然后根据发现的问题调整高级治理任务的设计。

### 9.3 冷启动验证应该覆盖更多 task

当前冷启动验证只覆盖了 T01-T05。如果覆盖到 T07-T10（治理模块），可能会暴露更多 SPEC/PLAN 的隐性上下文问题。但因为时间限制，没有做。

### 9.4 不做 GUI

GUI 是个人调试工具，非作业要求。它花费了约 4 个 commit，但最终只在调试真实 API 时用了 1-2 次。如果重做，我会把 GUI 的时间投入到更全面的冷启动验证中。

### 9.5 在 SPEC 中更早明确"治理规则 YAML 的 scope 字段必须被 guardrail 过滤"

scope 字段在 `GuardRule` 中定义，在 `config.py` 中加载，但最初的 `guardrail.py` 从未使用它过滤规则。这个"死字段"存活了 6 个 commit 才被发现。如果 SPEC 中明确写了"scope 字段用于过滤规则匹配范围"，subagent 在 T07 实现时就会加上 scope 过滤。

---

## 10. 对 Superpowers 方法论的批判

### 10.1 Superpowers 的假设

Superpowers 的核心假设是"Agent 是一个热情但无品味、无判断力、厌恶测试的初级工程师"。具体来说：
- **无品味**：Agent 能写出功能正确的代码，但不会主动做好的设计决策
- **无判断力**：Agent 不会主动区分"必须做"和"可以做"
- **厌恶测试**：Agent 会跳过测试，需要 TDD 纪律强制

### 10.2 这些假设在我的项目里成立吗？

**"无品味"——成立。** agent 在架构层面表现优秀，但代码细节需要纠正。典型例子：Shell 匹配逻辑的 `sudo` 绕过漏洞。agent 能画出正确的架构图，但代码实现上的安全漏洞需要我来发现。

**"无判断力"——成立。** agent 在没有明确要求的情况下建议了 keyring 和 REPL 交互模式。这两个建议在技术上合理，但在项目约束下（WSL 兼容性、v1.0 范围）是过度设计。agent 不会主动区分"必须做"和"可以做"。

**"厌恶测试"——不成立。** agent 很乐意写测试代码，甚至主动建议 `@pytest.mark.parametrize`。问题不在于测试的意愿，而在于测试的**质量**：它写的测试覆盖了 happy path 但可能遗漏边界条件（如 Shell 匹配的 `sudo` 绕过）。这需要我作为 reviewer 来补充。

**修正后的假设应该是：** "Agent 是一个热情但无品味、无判断力、**测试质量不足**的初级工程师。"

### 10.3 Superpowers 最大的价值

Superpowers 最大的价值不是"让 AI 写出更好的代码"，而是**强制人做出更好的决策**。brainstorming 的逐章签字机制迫使我在每个设计决策上有明确立场，writing-plans 的 task 拆解迫使我想清楚每个模块的接口边界。这些"人的工作"才是项目质量的真正决定因素。

### 10.4 Superpowers 的局限

1. **对"形式大于实质"的敏感度不够**：在 PLAN.md 初稿中，T14 Step 3 写的是"检查 AgentLoop.run() 中熔断判断的位置和逻辑"，但没有给出具体的代码修改。这本质上是一个"描述性步骤"而非"可执行步骤"。agent 有时会产出"看起来完整但实际空洞"的内容。

2. **假设了团队协作场景**：finishing-a-development-branch 和 verification-before-completion 等技能假设了多开发者协作、CI 流水线、PR review 等团队流程。在单人项目中，这些技能的大部分指令是形式大于实质。

3. **冷启动验证是隐藏的"高分技能"**：冷启动验证不是 Superpowers 的正式技能，但它在我的项目中是最有价值的质量信号。Superpowers 应该将"冷启动验证"作为一个正式技能，尤其是在 SPEC 生成后强制要求。

4. **技能加载的"仪式感"有时是负担**：每次开始新阶段都需要加载技能、阅读长长的 SKILL.md 文件。当我已经熟悉工作流后，这些仪式感变成了噪音。Superpowers 应该有一个"精简模式"，对于已经熟练的用户跳过详细的指令，只保留 checklist。

---

## 11. 总结：一个数字

| 维度 | 数据 |
|------|------|
| 技能使用 | 7 个技能，其中 3 个发挥了最大作用（brainstorming, subagent-driven, code-review），3 个形式大于实质 |
| 人工干预 | 5 条 AI 建议被推翻修正（keyring 否决、Shell 匹配修正、WARN 行为修改、REPL 范围移除、修正轮次计数方式） |
| Cold-start 缺陷 | 3 个阻断，其中 2 个是真正的文档缺陷 |
| 代码审查 | 2 Critical + 5 Important 问题 |
| 真实 API 问题 | 10+ 个发现（英文提示词、参数名兼容、重复成功循环、JSON 解析、环境变量泄漏等） |
| 测试 | 98 passed, 2 skipped（零网络依赖） |
| 如果重做 | 拆细 T13、先做真实 API 测试、冷启动覆盖更多 task、不做 GUI |