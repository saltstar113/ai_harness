# REFLECTION.md — 反思报告

> AI4SE 期末项目 A · 颜鑫 · 2026-08

---

## 1. 哪些 Superpowers 技能发挥了最大作用？

### 1.1 最大作用：brainstorming（3 轮迭代）

三轮 brainstorming 是整个项目中投资回报率最高的阶段。它的 "HARD-GATE" 机制（逐章签字确认）阻止了任何"跳过设计直接写代码"的冲动。智能体在我自己还没想清楚之前，就主动提出了 3 个架构决策问题（反馈闭环粒度、记忆方案、治理分类体系）。每个问题都迫使我在模糊的直觉上形成明确的立场，而不是"先写着再说"。

具体证据：智能体初稿中的 Shell 命令匹配逻辑（`tokens[0] + re.fullmatch`）存在一个安全关键的 `sudo` 绕过漏洞。我在第二轮审查中发现了它，因为"分块呈现 + 逐章签字"的流程让我能每次只深入审查一个章节。如果智能体一次性生成全部 11 章 SPEC，我几乎肯定会遗漏这个 Bug。

### 1.2 第二作用：subagent-driven-development（6 个 worktree 分支）

6 个 git worktree 的并行执行把原本需要约 2 周的串行开发压缩到了约 2 天。每个 subagent 收到从 PLAN.md 提取的 task brief，独立工作，产出的 commit 都能干净地合并。关键前提是 PLAN.md 的 task 粒度——每个 task 足够自包含，subagent 几乎不需要跨分支协调。

### 1.3 第三作用：requesting-code-review（1 次）

代码审查发现了 2 个 Critical 问题（反馈上下文未注入 LLM messages、YAML 正则转义错误）和 5 个 Important 问题。其中 `context_for_llm` 已计算但从未拼接到 `messages` 列表的 Critical Bug 会无声地让整个反馈闭环失效——所有测试都会通过（它们测试的是单个组件），但 agent 在生产环境中永远不会从错误中学习。

### 1.4 第四作用：冷启动验证（§4.5）

严格来说不是一项技能，但是最有价值的质量信号。一个全新的 agent 仅凭 SPEC + PLAN 就遇到了 3 个阻断点，其中 2 个是真正的文档缺陷（类型声明不一致、缺少 `git init`）。这是单人项目中最接近"同侪评审"的机制。

---

## 2. 哪些技能"形式大于实质"？

### 2.1 finishing-a-development-branch

这个技能的工作流假设了多开发者团队、PR review、CI 检查、部署流水线等场景。在单人项目中，"完成一个分支"就是 `git merge` 和 `git branch -d`。技能提供的"验证所有测试通过、审查 diff、更新 CHANGELOG"等 checklist 与 TDD 纪律完全重叠，没有新增信息。

### 2.2 verification-before-completion

该技能要求"运行验证命令并确认输出后再声称成功"，这与 TDD 循环 100% 重叠。每次 commit 后 `pytest` 已经在运行，技能没有提供任何额外价值。

### 2.3 writing-skills

这个技能被加载了但从未被调用——它是一个元技能，用于创建新技能，与构建 coding agent harness 无关。

### 2.4 判断标准

一项技能"形式大于实质"的判断标准是：(a) 它的指令与 TDD 已有的纪律重叠，或 (b) 它假设了不适用于单人项目的团队协作场景。真正发挥价值的技能是那些在行动前强制决策（brainstorming）、并行化独立工作（subagent-driven）、或事后发现错误（code review）的技能。

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

## 11. Agent 测试的缺陷与人工干预的价值

### 11.1 概述：一个贯穿始终的主题

本项目最意外的发现是：**agent 在测试方面的不足，不是"写得太少"，而是"写得不够深"**。agent 乐于写测试，甚至主动建议 `@pytest.mark.parametrize`。但它的测试几乎总是覆盖 happy path 而遗漏边界条件、安全漏洞和真实环境中的异常行为。这些遗漏的测试缺口，恰恰是人工干预发挥最大价值的地方。

以下按发现阶段，完整列出 agent 遗漏的 16 个问题，以及它们暴露的 agent 测试盲区。

### 11.2 设计阶段：Brainstorming 中纠正的 3 个架构级漏洞

| # | 问题 | 发现方式 | Agent 的盲区 | 人工干预 |
|---|------|----------|-------------|---------|
| 1 | Shell 匹配 `sudo` 绕过 | 我在第二轮草稿审查中发现 | Agent 只测试了 `rm -rf /`，未测试 `sudo rm -rf /`。它的测试覆盖了"命令匹配"，但未覆盖"前缀绕过"这一安全边界 | 将 `tokens[0] + re.fullmatch` 改为 `re.search(command) or re.fullmatch(pattern, cmd_name)` 双重校验 |
| 2 | keyring 过度设计 | 我在第二轮质询中否决 | Agent 在 WSL 兼容性约束下仍建议引入 keyring 库，未考虑 D-Bus 依赖风险 | 否决 keyring，仅用 `.env` + `getpass` |
| 3 | 修正轮次计数方式 | 我在第二轮质询中修正 | Agent 原方案按"同一动作"计数，未考虑失败类型变化说明修复引入了新问题 | 改为按"连续同类失败"计数，类型变化即重置 |

**暴露的测试盲区：** Agent 在设计阶段写的"伪代码"（如 Shell 匹配逻辑）在架构层面看不出问题，但代码实现上存在安全漏洞。它的测试思维停留在"验证功能正确"而非"验证不可绕过"。

### 11.3 代码审查阶段：requesting-code-review 发现的 5 个实现级 Bug

| # | 问题 | 严重性 | Agent 的盲区 | 人工干预 |
|---|------|--------|-------------|---------|
| 4 | 反馈上下文已计算但未注入 LLM messages | **Critical** | Agent 的测试只验证了 `FeedbackEngine.analyze()` 返回正确的 `context_for_llm`，但未验证这个值是否真的被拼接到发往 LLM 的 messages 列表中。测试覆盖了"组件行为"，但未覆盖"集成行为" | 在 `harness_core.py` 中补充 `messages.append({"role": "user", "content": context_for_llm})` |
| 5 | YAML 正则转义错误 | **Critical** | Agent 的测试使用 `BUILTIN_RULES`（硬编码规则）而非 `guard_rules.yaml`（配置文件）。YAML 解析后 `C:\\Windows\\` 变成 `C:\Windows\`，正则匹配失效，但测试从未加载真实 YAML 文件 | 修复 YAML 中的转义写法 |
| 6 | Action 导入路径错误 | Important | Agent 的测试只验证了 models.py 的字段定义，未验证跨模块导入 | 修正导入路径 |
| 7 | BLOCK 拒绝后未回灌 | Important | Agent 的测试验证了 `guard.check()` 返回 BLOCK，但未验证 BLOCK 后的拒绝理由是否注入下一轮 LLM 上下文 | 在 AgentLoop 中补充拒绝理由回灌逻辑 |
| 8 | LINT_ERROR 未分类 | Important | Agent 的测试覆盖了 TEST_FAILURE 和 COMPILE_ERROR，但遗漏了 LINT_ERROR 的行号格式匹配 | 补充 lint 输出正则匹配 |

**暴露的测试盲区：** Agent 的测试是"组件级"的——它验证每个函数在隔离状态下正确，但几乎从不验证"组件之间的数据流"。Bug #4（反馈上下文未注入）是最典型的例子：`FeedbackEngine` 和 `AgentLoop` 各自的单元测试都通过，但两者之间的"胶水代码"缺失了。

### 11.4 真实 API 测试阶段：与 DeepSeek 交互中发现的 4 个运行时问题

| # | 问题 | 发现方式 | Agent 的盲区 | 人工干预 |
|---|------|----------|-------------|---------|
| 9 | 中文提示词导致 JSON 格式不稳定 | 真实 API 调用 | Mock LLM 测试中，LLM 总是返回预定义的格式正确的 JSON。真实 DeepSeek 对中文提示词的 JSON 执行不稳定，经常输出缺少引号的格式或错误字段名 | 改为英文系统提示词 |
| 10 | LLM 参数名不一致（`file_path`/`file`/`filepath` vs `path`） | 真实 API 调用 | Mock LLM 的测试总是使用固定的 `{"path": "test.py"}`，但真实 LLM 输出的参数名不可预测 | Executor 兼容多种参数名 |
| 11 | LLM 成功后陷入重复循环 | 真实 API 调用 | Mock LLM 在返回 FINISH 信号后自动停止，但真实 LLM 不会主动说"我完成了"——它会在成功后继续做看似有用的修改 | 添加重复成功检测（5 次连续相同动作后强制结束） |
| 12 | LLM 返回非 JSON 格式（invalid_json 熔断） | 真实 API 调用 | Mock LLM 总是返回格式正确的 JSON，但真实 LLM 偶尔返回 Markdown 包裹的 JSON 或纯文本 | 添加 JSON 容错解析 + 3 次 invalid_json 后熔断 |

**暴露的测试盲区：** Mock LLM 测试是"理想的"——它模拟的是一个完美的 LLM，总是返回格式正确的 JSON，总是使用正确的参数名，总是知道何时停止。但真实 LLM 的行为充满了不确定性。Mock 测试能验证"harness 逻辑是否正确"，但不能验证"harness 在真实 LLM 的不确定性下是否仍然鲁棒"。

### 11.5 高级治理任务：攻击性测试中发现的 2 个安全漏洞

| # | 问题 | 发现方式 | Agent 的盲区 | 人工干预 |
|---|------|----------|-------------|---------|
| 13 | `$IFS` 注入绕过 | 构造攻击性测试用例 | Agent 的 Shell 测试覆盖了 `rm -rf /`、`sudo rm -rf /`、`env rm -rf /`，但从未测试 `rm$IFS-rf$IFS/`。它不知道 Shell 变量可以替代空格 | 在 `check_shell_command()` 中添加 `normalize.replace('$IFS', ' ')` |
| 14 | Filesystem 规则 pattern 从未被检查（死代码） | 审查 guardrail.py 的控制流 | Agent 的测试只覆盖了 Shell 动作的 pattern 匹配，Filesystem 动作的 pattern 匹配代码存在但从未被调用。`guard_rules.yaml` 中的 `fs-delete-system` 规则是"死规则" | 修复控制流，确保 Filesystem 规则也被检查 |

**暴露的测试盲区：** Agent 的测试是"正向的"——它验证了"已知的攻击向量被拦截"，但从未尝试"构造新的攻击向量"。`$IFS` 注入和 Filesystem 死代码都是"你不测试就不知道存在"的漏洞。

### 11.6 高级鲁棒性任务：环境与边界条件中发现的 4 个缺陷

| # | 问题 | 发现方式 | Agent 的盲区 | 人工干预 |
|---|------|----------|-------------|---------|
| 15 | 子进程继承全部环境变量（含 `DEEPSEEK_API_KEY`） | 审查 `subprocess.run()` 的默认行为 | Agent 的测试只验证了 `execute_shell` 能执行命令，未验证环境变量是否被正确隔离 | 实现环境变量白名单过滤 |
| 16 | 超大输出未截断 | 考虑上下文窗口限制 | Agent 的测试只使用了短输出（如 `"hello"`），未测试 `cat large_file.log` 这类超大输出场景 | 添加 3000 chars 头尾采样截断 |

**暴露的测试盲区：** Agent 的测试是"功能性的"——它验证代码在正常输入下工作，但从不验证代码在异常输入（超大输出）或环境副作用（子进程继承环境变量）下的行为。

### 11.7 冷启动验证：独立 Agent 暴露的 1 个实现级 Bug

| # | 问题 | 发现方式 | Agent 的盲区 |
|---|------|----------|-------------|
| 17 | T03 MockLLM off-by-one bug | 冷启动 Agent 运行自己的测试时发现 | 主 agent 实现的 `ScriptedMockLLM` 中 `call_count` 先递增后减一，导致第 3 次调用跳过了第 3 个动作。冷启动 Agent 通过 TDD 自行发现并修复 |

**暴露的测试盲区：** 这个 bug 暴露的不是"测试不足"，而是"测试驱动开发的价值"——冷启动 Agent 通过先写测试再实现，在自己的测试中发现了这个 off-by-one 错误。主 agent 的原始实现中，这个 bug 被遗漏了——因为主 agent 的测试用例中动作数量恰好只有 2 个，没有触发"第 3 个动作被跳过"的边界条件。

### 11.8 Agent 测试缺陷的根因分析

以上 17 个问题可以归纳为 5 类 agent 测试盲区：

| 盲区类型 | 典型表现 | 问题数量 | 根本原因 |
|----------|---------|----------|----------|
| **安全边界遗漏** | 测试了"命令被拦截"但未测试"绕过方式" | 3 个（#1, #13, #14） | Agent 理解"规则"但不懂"漏洞"——它不知道攻击者会尝试绕过 |
| **集成测试缺失** | 组件级测试通过，但组件间数据流断裂 | 4 个（#4, #5, #6, #7） | Agent 的测试思维是"函数级"的，无法自然跨越模块边界 |
| **Mock 与现实脱节** | Mock LLM 测试通过，但真实 LLM 行为不可预测 | 4 个（#9, #10, #11, #12） | Agent 无法区分"模拟的 LLM"和"真实的 LLM"之间的行为差异 |
| **环境副作用忽视** | 测试了功能正确性，但未考虑环境继承 | 2 个（#15, #16） | Agent 不关心操作系统级的副作用（环境变量、文件系统） |
| **边界条件不足** | 测试用例数量太少，未触发 off-by-one 等边界 bug | 1 个（#17） | Agent 倾向于写"刚好通过"的测试，而非"全面覆盖"的测试 |

### 11.9 人工干预的价值：为什么工程师不能只做"验收"

如果我只是做"验收"——等 agent 写完代码后跑测试、看结果——以上 17 个问题中，至少有 10 个会进入生产环境：

- **Bug #4（反馈上下文未注入）**：所有测试通过，但 agent 永远不会从错误中学习。用户会困惑"为什么 agent 一直重复同样的错误"。
- **Bug #13（`$IFS` 注入）**：所有 Shell 测试通过，但攻击者可以通过 `$IFS` 绕过护栏。这是一个真正的安全漏洞。
- **Bug #14（Filesystem 死代码）**：所有测试通过，但 `fs-delete-system` 规则从未生效。用户会困惑"为什么我配置的规则不工作"。
- **Bug #9（中文提示词）**：Mock 测试通过，但真实 API 调用中 JSON 格式错误率高达 40%。用户会认为"这个产品坏了"。

**人工干预不是"帮 agent 修 bug"，而是"做 agent 做不到的事"**：agent 能生成代码，能写测试，能在给定明确目标时高效执行。但它做不到的是：(1) 从攻击者视角审视代码、(2) 跨越模块边界追踪数据流、(3) 在真实环境中验证行为、(4) 质疑"为什么这个测试通过了但功能不工作"。

**这个项目的核心教训是：** AI 协作下的工程师角色，从"写代码的人"变成了"判断代码是否正确的人"。而"判断正确性"需要的不只是跑测试，而是对代码的系统性怀疑——这个怀疑是 agent 不具备的，也是人工干预的核心价值。

---

## 12. 总结：一个数字

| 维度 | 数据 |
|------|------|
| 技能使用 | 7 个技能，其中 3 个发挥了最大作用（brainstorming, subagent-driven, code-review），3 个形式大于实质 |
| 人工干预 | 17 个问题通过人工审查发现并修复（3 设计阶段 + 5 代码审查 + 4 真实 API + 2 安全漏洞 + 2 环境缺陷 + 1 cold-start），5 条 AI 建议被推翻修正 |
| Agent 测试盲区 | 5 类根因：安全边界遗漏、集成测试缺失、Mock 与现实脱节、环境副作用忽视、边界条件不足 |
| Cold-start 缺陷 | 3 个阻断，其中 2 个是真正的文档缺陷 |
| 代码审查 | 2 Critical + 5 Important 问题 |
| 真实 API 问题 | 10+ 个发现（英文提示词、参数名兼容、重复成功循环、JSON 解析、环境变量泄漏等） |
| 测试 | 98 passed, 2 skipped（零网络依赖） |
| 如果重做 | 拆细 T13、先做真实 API 测试、冷启动覆盖更多 task、不做 GUI |