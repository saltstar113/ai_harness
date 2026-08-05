# SPEC.md — Coding Agent Harness

> **项目类型**：AI4SE 期末项目 A · Coding Agent Harness
> **核心等式**：Agent = LLM + Harness
> **技术栈**：Python 3.11+ · DeepSeek LLM · CLI 工具
> **作者**：颜鑫
> **日期**：2026-08

---

## 目录

1. [问题陈述](#1-问题陈述)
2. [用户故事](#2-用户故事)
3. [功能规约](#3-功能规约)
4. [非功能性需求](#4-非功能性需求)
5. [系统架构](#5-系统架构)
6. [数据模型](#6-数据模型)
7. [凭据与分发设计](#7-凭据与分发设计)
8. [技术选型与理由](#8-技术选型与理由)
9. [验收标准](#9-验收标准)
10. [风险与未决问题](#10-风险与未决问题)
11. [领域与机制设计](#11-领域与机制设计)

---

## 1. 问题陈述

### 1.1 要解决什么问题

LLM 能完成大部分"思考"——决定下一步做什么。但要把一个只会产生下一步设想的 LLM 封装成一台能稳定、可靠工作的 coding agent，需要大量的工程基础设施：决策封装、工具分发、治理护栏、反馈闭环、上下文管理、凭据安全。这些工程层构成了 **Harness**。

当前市面上的 agent 框架（LangChain、AutoGen、CrewAI 等）将这些工程层封装为黑盒配置，开发者只需写提示词。但这也意味着：护栏只是一句"请不要删除文件"，反馈只是一句"请检查你的代码"——这些机制实质上依赖 LLM 的遵从，而非确定性的代码保证。

本项目要构建一个 **Coding Agent Harness**，其核心机制（治理、反馈、工具分发、记忆）全部由确定性代码实现，而非提示词。移除 LLM 后，每个机制仍能通过单元测试验证。

### 1.2 目标用户

- 希望用 AI 辅助编码但需要安全边界的个人开发者
- 需要在团队中引入 AI coding agent 但担心安全风险的工程团队
- 学习 agentic SE 方法论的学生和研究者

### 1.3 为什么值得做

当 LLM 能完成大部分编码工作时，工程师的真正价值落在 Harness 这层工程上。本项目通过亲手实现一个 harness 内核，回答一个核心问题：**移除 LLM 后，你的仓库里还剩多少可独立验证的工程？** 这也是作业 A 的核心命题。

---

## 2. 用户故事

| # | 用户故事 | 验收条件 | I-N-V-E-S-T 评估 |
|---|---------|---------|-------------------|
| US1 | **作为开发者**，我希望 agent 能读取我的代码、执行测试，并根据测试失败信息自动修正代码，**以便** 我能把重复的 TDD 红绿循环交给 agent 完成。 | agent 在 mock LLM 下收到 `TEST_FAILURE` 反馈后，下一轮动作是修改源文件。 | I: 独立可测；N: 可协商实现方式；V: 对开发效率有价值；E: 可估算（2-3 天）；S: 小到可在一个 subagent 内完成；T: 有明确测试标准 |
| US2 | **作为开发者**，我希望 agent 在执行 `rm -rf /` 或 `shutdown` 等危险命令时被拦截并等待我确认，**以便** 我不会因为 agent 的误操作导致系统损坏。 | 在 mock LLM 下注入危险动作，断言返回 `BLOCK` 且进入 HITL 审批。 | I: 独立可测；N: 规则可配置；V: 安全刚需；E: 可估算；S: 单一职责；T: 可测试 |
| US3 | **作为开发者**，我希望 agent 能记住我的项目约定（如"用 pytest 而非 unittest"），**以便** 我不需要每轮对话都重复同样的偏好。 | 新会话启动时，通过关键词检索到历史会话中的 conventions 并注入上下文。 | I: 独立可测；N: 存储格式可协商；V: 减少重复沟通；E: 可估算；S: 小；T: 可测试 |
| US4 | **作为开发者**，我希望 agent 在连续修正同一个问题 3 次仍失败后能自动暂停并交给我处理，**以便** 避免 agent 无限循环浪费 token 和时间。 | 注入 3 次连续同类失败，断言 `should_retry=False` 且触发 HITL。 | I: 独立可测；N: 轮次阈值可配置；V: 防止资源浪费；E: 可估算；S: 小；T: 可测试 |
| US5 | **作为开发者**，我希望首次使用时系统能引导我安全地录入 API Key，且之后可以查看状态（仅显示"已配置"而不回显明文），**以便** 我不会不小心把 key 泄漏到 git 或日志里。 | `getpass` 隐式输入；`status()` 仅返回 "已配置/未配置"；`.env` 在 `.gitignore` 中。 | I: 独立可测；N: 存储方式可协商；V: 安全刚需；E: 可估算；S: 小；T: 可测试 |
| US6 | **作为开发者**，我希望 agent 不能读写 workspace 之外的任何文件，**以便** 即使 agent 产生幻觉也不会访问我的系统敏感文件。 | 构造 `path="../etc/passwd"` 写操作，断言 `BLOCK`。 | I: 独立可测；N: 边界策略可协商；V: 安全刚需；E: 可估算；S: 小；T: 可测试 |

---

## 3. 功能规约

### 3.1 模块总览

| 模块 | 文件 | 职责 |
|------|------|------|
| CLI 入口 | `run_cli.py` | 命令行解析、会话启动/恢复、IO 适配层 |
| Agent 主循环 | `harness_core.py` | 组织上下文 → 调用 LLM → 解析动作 → 分发执行 → 回灌结果 → 停机判断 |
| 工具执行器 | `executor.py` | 动作分发：读/写文件、执行 shell、运行测试/lint |
| 治理引擎 | `guardrail.py` | 多维度危险动作识别 → 分类 → HITL 审批状态机 |
| 反馈闭环 | `harness_core.py`（反馈逻辑） | 解析产物 → 结构化分类 → 多轮修正熔断 |
| 记忆模块 | `session_store.py` | 结构化 JSON 会话存储、跨会话检索与注入 |
| 配置加载 | `config.py` | 加载 YAML 规则文件（治理规则、工具白名单、项目约定） |
| 凭据管理 | `credential.py` | `.env` 加载 + `getpass` 隐藏输入引导 + 查看/更新/清除（不回显明文） |
| Mock LLM 抽象 | `mock_llm.py` | 可注入的 LLM 替身，用于离线确定性测试 |

### 3.2 模块详细规约

#### 3.2.1 CLI 入口 (`run_cli.py`)

| 项目 | 内容 |
|------|------|
| 输入 | 命令行参数：`--task "描述"` / `--session <id>` / `--config <path>` / `--mock` / `--strict` |
| 行为 | 解析参数 → 初始化 Core 模块（依赖注入真实 LLM 或 Mock LLM）→ 启动主循环 |
| 输出 | 每轮动作的决策摘要 + 最终结果到 stdout；详细日志到文件 |
| 边界条件 | 无参数时展示帮助；`--session` 不存在时提示创建新会话；`--mock` 模式跳过凭据检查 |
| 错误处理 | 配置文件解析失败 → 提示并退出；LLM 连接失败 → 重试 3 次后退出；Ctrl+C → 优雅保存会话并退出 |

#### 3.2.2 Agent 主循环 (`harness_core.py`)

```
while not done:
    1. 构造上下文（系统提示 + 会话记忆 + 当前任务 + 工具描述）
    2. 调用 LLM（返回结构化动作 JSON）
    3. 解析动作（JSON Schema 校验）
    4. 治理引擎介入（识别 → 分类 → 审批）
       - SAFE → 执行
       - WARN  → 记录高亮日志 + 执行（--strict 模式下升格为 HITL）
       - BLOCK → HITL 审批（通过 io.request_approval()）→ 批准则执行 / 拒绝则回灌拒绝理由
    5. 执行动作
    6. 反馈闭环介入（解析结果 → 分类 → 判定是否需要修正）
       - 成功 → 重置计数器，记录结果，进入下一轮
       - 失败第 1 次 → 完整错误上下文回灌
       - 失败第 2 次 → 精简提示回灌
       - 失败第 3 次 → 熔断，HITL
    7. 停机判断（任务完成 / 达到最大轮次 / 用户中断 / 熔断）
```

| 项目 | 内容 |
|------|------|
| 输入 | `Task` 对象（描述 + 上下文）+ `Session` 对象（历史记忆） |
| 行为 | 循环执行上述 7 步，每步输出结构化 `Turn` 记录 |
| 输出 | `Turn` 列表 + 最终 `TaskResult`（`success` / `aborted` / `circuit_breaker`） |
| 边界条件 | 最大轮次默认 50，可通过 `--max-turns` 配置；空动作 → 视为 NOP 不计轮次 |
| 错误处理 | LLM 返回非结构化输出 → 重试解析（最多 2 次），仍失败则记录并 HITL |

#### 3.2.3 工具执行器 (`executor.py`)

| 工具 | 操作 | 参数 |
|------|------|------|
| `read_file` | 读取文件内容 | `path: str` |
| `write_file` | 写入/创建文件 | `path: str, content: str` |
| `execute_shell` | 执行 shell 命令 | `command: str, cwd: str?` |
| `run_tests` | 运行 pytest | `target: str?` |
| `run_lint` | 运行 lint 工具 | `target: str?` |

**`write_file` 路径隔离与建图保障：**

在执行写入前：
1. 调用 `pathlib.Path(path).resolve().is_relative_to(workspace)` 进行物理路径校验，防止路径遍历攻击。
2. 校验通过后，调用 `target.parent.mkdir(parents=True, exist_ok=True)` 确保父目录存在，避免因缺少中间目录导致的写入失败。

| 项目 | 内容 |
|------|------|
| 输入 | 结构化 `Action` 对象（`{tool, params}`） |
| 行为 | 路由到对应工具函数 → 执行 → 捕获 stdout/stderr/exit_code |
| 输出 | `ToolResult`（`{stdout, stderr, exit_code, duration_ms}`） |
| 边界条件 | `write_file` 路径必须在 workspace 内（范围围栏）；`execute_shell` 黑白名单预检 |
| 错误处理 | 工具不存在 → 返回 `UNKNOWN_TOOL`；执行超时（默认 30s）→ 返回 `TIMEOUT` |

#### 3.2.4 治理引擎 (`guardrail.py`)

**分类维度：**

| 维度 | 取值 |
|------|------|
| 操作类型 | `FileSystem` / `Shell` / `Network` / `Package` |
| 风险等级 | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| 作用域 | `Workspace`（项目目录内）/ `Project`（项目相关但非目录内）/ `System`（全局） |

**判定矩阵（默认规则，可通过配置文件覆盖）：**

| 操作类型 | 作用域 | 风险等级 | 判定 |
|----------|--------|----------|------|
| FileSystem: read | 任意 | LOW | SAFE |
| FileSystem: write | Workspace | MEDIUM | SAFE |
| FileSystem: write | Project | MEDIUM | WARN |
| FileSystem: delete | Workspace | MEDIUM | WARN |
| FileSystem: delete | System | CRITICAL | BLOCK |
| Shell: read-only（ls/cat/dir） | Workspace | LOW | SAFE |
| Shell: read-only | System | MEDIUM | WARN |
| Shell: 有副作用（pip/npm install） | Workspace | MEDIUM | WARN |
| Shell: 危险命令（rm -rf /、shutdown 等） | 任意 | CRITICAL | BLOCK |
| Network: outbound | 任意 | HIGH | BLOCK |
| Package: install | Workspace | MEDIUM | WARN |
| Package: install | System | HIGH | BLOCK |

**路径隔离机制：**

所有文件操作在执行前必须通过路径边界校验。使用 `pathlib.Path(target).resolve().is_relative_to(workspace)` 进行物理路径解析，而非字符串前缀匹配。这防止了 `../`、符号链接等路径遍历攻击。

```python
def validate_path(self, target: str, action: str) -> GuardDecision:
    resolved = pathlib.Path(target).resolve()
    if not resolved.is_relative_to(self.workspace):
        return GuardDecision(
            verdict=Ver.BLOCK,
            matched_rule="path-boundary",
            reason=f"路径越界：{target} 不在 workspace {self.workspace} 内"
        )
    return GuardDecision(verdict=Ver.SAFE, ...)
```

**Shell 命令安全解析：**

命令安全匹配采用 Python 标准库 `shlex` 词法解析 + 正则模式双重校验。`shlex.split()` 正确处理引号、转义和空格，防止注入绕过。匹配逻辑同时检查完整命令和首词，防止 `sudo`、`env` 等前缀绕过。

```python
import shlex
import re

def check_shell_command(self, command: str) -> GuardDecision:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return GuardDecision(verdict=Ver.BLOCK, reason="命令解析失败")

    cmd_name = tokens[0] if tokens else ""

    # 完整命令匹配 或 首词命中危险指令 → 均触发拦截
    is_matched = any(
        re.search(rule.pattern, command) or re.fullmatch(rule.pattern, cmd_name)
        for rule in self.shell_rules
    )

    if is_matched:
        matched = next(r for r in self.shell_rules
                       if re.search(r.pattern, command) or re.fullmatch(r.pattern, cmd_name))
        return GuardDecision(
            verdict=matched.verdict,
            matched_rule=matched.id,
            reason=matched.description
        )

    return GuardDecision(verdict=Ver.SAFE, matched_rule="default", reason="")
```

**HITL 审批流：**

```
BLOCK 判定 → 调用 io.request_approval(action, risk_info)
           → 返回 ApprovalResult(approved=True/False, reason="用户输入的理由")
           → approved=True  → 执行
           → approved=False → 将 reason 回灌给 LLM，要求替代方案
```

**WARN 行为：**

- **默认模式**：WARN 输出高亮警告日志（`⚠️ [WARN] 动作: xxx | 风险: MEDIUM | 自动执行中...`），不阻塞流水线。
- **`--strict` 模式**：WARN 升格为 HITL，通过 `io.request_approval()` 等待用户按键确认后执行。
- 命令行参数：`python run_cli.py --strict` 开启严格模式。

| 项目 | 内容 |
|------|------|
| 输入 | 结构化 `Action` + 当前 workspace 路径 |
| 行为 | 解析类型/作用域 → 物理路径校验 → shlex 命令解析 → 规则匹配 → 输出 `GuardDecision` |
| 输出 | `GuardDecision(verdict, reason)` |
| 边界条件 | 规则文件不存在 → 使用内置默认规则；规则冲突 → 取最高风险判定 |
| 错误处理 | 规则解析失败 → 降级为全量 BLOCK 模式（安全第一） |

#### 3.2.5 反馈闭环（`harness_core.py` 内）

**结构化分类器：**

| 类别 | 判定依据 | 示例 |
|------|----------|------|
| `COMPILE_ERROR` | exit_code != 0 + stderr 含 `SyntaxError` 或 `IndentationError` | `SyntaxError: invalid syntax` |
| `TEST_FAILURE` | pytest/flake8/ruff exit_code != 0 | `FAILED test_foo.py::test_bar` |
| `LINT_ERROR` | lint 工具 exit_code != 0 | `E501 line too long` |
| `RUNTIME_ERROR` | exit_code != 0 + stderr 含 `Traceback` | `TypeError: ...` |
| `TIMEOUT` | 执行超过阈值（默认 30s） | >30s |
| `SUCCESS` | exit_code == 0 | |
| `UNKNOWN_ERROR` | 无法归入以上类别 | 兜底分类 |

**修正轮次计数规则：**

按"连续同类失败"计数：
- 每次工具执行成功（exit_code == 0）→ 重置计数器为 0
- 同类失败（如连续 3 次 `TEST_FAILURE`）→ 按轮次升级策略
- 失败类型变化（`TEST_FAILURE` → `COMPILE_ERROR`）→ 重置计数器为 1（视为新问题，因为修复引入了新错误）

**多轮修正状态机：**

```
Round 1: 失败 → 注入完整错误上下文（stdout + stderr + category）→ LLM 修正
Round 2: 再次失败 → 注入精简提示（仅 category + 关键错误行）→ LLM 修正
Round 3: 仍失败 → 熔断 → HITL："连续 3 次同类失败，已触发熔断，请人工介入"
```

| 项目 | 内容 |
|------|------|
| 输入 | `ToolResult` + 当前修正轮次 + 上一次失败类别 |
| 行为 | 分类 → 比较类别是否与上次相同 → 更新计数器 → 根据轮次构造回灌上下文 → 返回修正指令 |
| 输出 | `FeedbackResult`（`{category, round, should_retry, context_for_llm}`） |
| 边界条件 | 成功 → 重置计数器；非修正类任务（如纯查询 `read_file`）→ 不触发反馈 |
| 错误处理 | 无法分类 → 归为 `UNKNOWN_ERROR`，按第 1 轮逻辑处理 |

#### 3.2.6 记忆模块 (`session_store.py`)

**数据结构：**

```json
{
  "session_id": "uuid",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T01:00:00Z",
  "task_description": "重构 user 模块",
  "decisions": [
    {"turn": 3, "decision": "使用 dataclass 替代 namedtuple", "reason": "类型检查更友好"}
  ],
  "conventions": [
    {"key": "test_framework", "value": "pytest"},
    {"key": "lint_tool", "value": "ruff"}
  ],
  "errors": [
    {"turn": 5, "category": "TEST_FAILURE", "summary": "test_auth 超时"}
  ],
  "tags": ["refactoring", "user-module"],
  "summary": "重构了 user 模块的数据模型，引入了 dataclass"
}
```

**检索策略：**

新会话启动时，按关键词匹配 `tags` 和 `task_description`，取最近 5 个相关会话的 `conventions` 和 `decisions` 注入上下文。

| 项目 | 内容 |
|------|------|
| 输入 | 读写操作：`save_session(Session)` / `load_session(id)` / `search_sessions(keywords)` |
| 行为 | 读写 `~/.ai_harness/sessions/` 下的 JSON 文件 |
| 输出 | `Session` 对象 / 列表 |
| 边界条件 | 会话目录不存在 → 自动创建；文件损坏 → 跳过并 warn |
| 错误处理 | 磁盘满 → 提示并降级为无记忆模式 |

#### 3.2.7 配置加载 (`config.py`)

| 项目 | 内容 |
|------|------|
| 输入 | YAML 配置文件路径（`--config` 参数或默认 `guard_rules.yaml`） |
| 行为 | 解析 YAML → 构造 `GuardRule` 列表 |
| 输出 | `List[GuardRule]` |
| 边界条件 | 文件不存在 → 使用内置默认规则；字段缺失 → 使用默认值填充 |
| 错误处理 | YAML 语法错误 → 输出具体错误行号，降级为全量 BLOCK 模式 |

#### 3.2.8 凭据管理 (`credential.py`)

| 项目 | 内容 |
|------|------|
| 输入 | 命令行子命令：`credential set` / `credential status` / `credential clear` |
| 行为 | `set`: 使用 `getpass.getpass()` 隐式读取，写入 `.env`；`status`: 返回"已配置"或"未配置"（不回显明文）；`clear`: 删除 `.env` 中对应条目 |
| 输出 | 状态消息到 stdout |
| 边界条件 | `.env` 不存在时 `set` 自动创建；`clear` 时如 `.env` 不存在则提示无需操作 |
| 错误处理 | 文件权限不足 → 提示手动检查权限 |

---

## 4. 非功能性需求

### 4.1 性能

| 指标 | 目标 |
|------|------|
| 单轮循环延迟（不含 LLM 调用） | < 50ms（工具执行 + 治理 + 反馈开销） |
| 会话加载时间 | < 100ms（从 JSON 文件加载） |
| 最大轮次 | 默认 50，可配置 |
| 工具执行超时 | 默认 30s，可配置 |

### 4.2 安全

**凭据威胁模型：**

| 威胁 | 对策 |
|------|------|
| API Key 硬编码在源码中 | 禁止硬编码；仅通过 `.env` 或 `getpass` 输入获取 |
| API Key 提交到 Git | `.gitignore` 包含 `.env`；CI 检查是否有敏感文件提交 |
| API Key 出现在日志/终端 | 日志系统过滤 key 模式；`credential status` 仅显示"已配置/未配置" |
| `.env` 文件明文存储 | 在文档中明确标注风险：`.env` 为明文，对文件系统有读权限的进程均可读取 |
| 进程环境变量可见 | 标注风险：`os.environ` 可被同进程及其子进程读取 |
| 路径遍历攻击 | `pathlib.resolve().is_relative_to()` 物理路径校验 |
| 命令注入 | `shlex.split()` 词法解析 + 正则双重校验 |

**安全设计原则：**

- 默认拒绝：guardrail 规则解析失败时，降级为全量 BLOCK 模式
- 最小权限：agent 仅能访问 workspace 内的文件
- 纵深防御：路径校验 + 命令解析 + 规则匹配三层防护

### 4.3 可用性

| 要求 | 说明 |
|------|------|
| 有意义的错误消息 | 所有错误输出包含原因和修复建议，不输出裸 traceback |
| 引导式首次配置 | 首次运行自动检测 `.env` 缺失，引导用户通过 `credential set` 配置 |
| 清晰的 CLI 帮助 | `--help` 输出完整参数说明和示例 |
| 进度可见 | 每轮循环输出当前轮次、动作、结果摘要 |

### 4.4 可观测性

| 要求 | 说明 |
|------|------|
| 结构化日志 | 每轮 Turn 记录为结构化 JSON，包含时间戳、动作、结果、反馈类别 |
| 日志级别 | INFO（正常流程）/ WARN（治理拦截）/ ERROR（执行失败） |
| 可追溯 | 每个会话的完整 Turn 历史可回放审计 |

---

## 5. 系统架构

### 5.1 核心/IO 分离架构

```
┌──────────────────────────────────────────────────┐
│                    IO Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ CLI Adapter  │  │ Credential   │  │ Logger  │ │
│  │ (stdin/out)  │  │ Prompter     │  │         │ │
│  └──────┬───────┘  └──────┬───────┘  └────┬────┘ │
│         │                 │                │      │
│  ┌──────┴─────────────────┴────────────────┴────┐ │
│  │              IO Interface (Protocol)          │ │
│  │  output(msg) / input(prompt) /                │ │
│  │  request_approval(action, risk) → ApprovalRes │ │
│  └──────────────────────┬───────────────────────┘ │
└─────────────────────────┼─────────────────────────┘
                          │
┌─────────────────────────┼─────────────────────────┐
│                    Core Layer                      │
│                         │                          │
│  ┌──────────────────────┴──────────────────────┐  │
│  │              AgentLoop                       │  │
│  │  run(task, session) → TaskResult             │  │
│  │  (依赖注入: llm, guard, executor, feedback,  │  │
│  │   session_store, io)                         │  │
│  └──┬───────┬────────┬────────┬────────┬───────┘  │
│     │       │        │        │        │          │
│  ┌──▼──┐ ┌─▼────┐ ┌─▼────┐ ┌─▼────┐ ┌─▼──────┐  │
│  │LLM  │ │Guard │ │Exec  │ │Feed  │ │Session │  │
│  │Client│ │Engine│ │utor  │ │back  │ │Store   │  │
│  │(接口)│ │      │ │      │ │Engine│ │        │  │
│  └─────┘ └──────┘ └──────┘ └──────┘ └────────┘  │
│                                                   │
│  ┌────────────────────────────────────────────┐   │
│  │              Config Parser                  │   │
│  └────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
```

### 5.2 接口契约

**依赖注入模式：**

`AgentLoop` 所有外部依赖通过构造函数注入。测试时替换 `llm=ScriptedMockLLM()`, `io=SilentIO()`，生产时替换为 `llm=DeepSeekClient()`, `io=CliIO()`。这确保了：
- 测试无需真实 LLM 或网络连接
- WebUI 可替换 IO 实现而不改 Core 一行代码
- 每个模块可独立单测

```python
# harness_core.py
class AgentLoop:
    def __init__(self, llm: LLMClient, guard: GuardEngine,
                 executor: Executor, feedback: FeedbackEngine,
                 session_store: SessionStore, io: IOInterface):
        """
        依赖注入构造器。
        测试时：llm=ScriptedMockLLM(), io=SilentIO()
        生产时：llm=DeepSeekClient(), io=CliIO()
        """
        self.llm = llm
        self.guard = guard
        self.executor = executor
        self.feedback = feedback
        self.session_store = session_store
        self.io = io

    def run(self, task: Task, session: Session) -> TaskResult:
        """返回结构化 TaskResult，不直接 IO。"""
        ...

# IO 接口（Protocol）
class IOInterface(Protocol):
    def output(self, message: str) -> None: ...
    def input(self, prompt: str) -> str: ...
    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult:
        """
        HITL 审批接口。
        展示动作+风险信息，等待用户决定。
        返回 ApprovalResult(approved, reason)，reason 可包含用户拒绝时的具体修改意见，将回灌给 LLM。
        """
        ...

@dataclass
class ApprovalResult:
    approved: bool
    reason: str = ""  # 拒绝时由用户填写，回灌给 LLM

# LLM 抽象接口
class LLMClient(Protocol):
    def chat(self, messages: list[dict]) -> dict:
        """发送消息列表，返回 LLM 响应。"""
        ...

# ScriptedMockLLM：用于确定性测试
class ScriptedMockLLM:
    """
    支持注入 List[Action] 动作队列，用于离线自动化测试多轮修正状态机。
    每次调用 chat() 按 FIFO 顺序返回队列中的下一个动作。
    队列耗尽后返回 FINISH 停机信号。
    """
    def __init__(self, actions: list[Action]):
        self.queue = actions
        self.call_count = 0

    def chat(self, messages: list[dict]) -> dict:
        if self.call_count >= len(self.queue):
            return {"action": "finish", "reason": "queue exhausted"}
        action = self.queue[self.call_count]
        self.call_count += 1
        return {"action": action.tool, "params": action.params}
```

**关键设计决策：**

| 决策 | 理由 |
|------|------|
| 依赖注入 | 测试时 `llm=ScriptedMockLLM()`, `io=SilentIO()` 无缝替换 |
| Core 不直接 print/input | WebUI 可替换 IO 实现而不改 Core 一行代码 |
| Core 返回结构化数据 | 便于单测断言（无需捕获 stdout） |
| GuardEngine 只做判定，不做 IO | 审批的"等待用户输入"由 AgentLoop 通过 `io.request_approval()` 完成，GuardEngine 保持纯函数 |
| LLMClient 是抽象接口 | MockLLM 和 RealLLM 实现同一接口，测试时无缝替换 |
| `request_approval()` 替代简单 `confirm()` | 支持用户拒绝时输入具体修改意见，意见回灌给 LLM 作为反馈 |

### 5.3 数据流（一次完整 Turn）

```
Task "修复 test_auth 失败"
  │
  ▼
AgentLoop.run()
  │
  ├─ 1. SessionStore.search("test_auth") → 注入历史 conventions
  ├─ 2. LLMClient.chat(context) → Action("execute_shell", "pytest test_auth.py")
  ├─ 3. GuardEngine.check(action) → GuardDecision(WARN, "shell 执行, 记录日志")
  ├─ 4. (WARN, 非 strict 模式) 跳过 HITL → 输出高亮警告 → 执行
  ├─ 5. Executor.dispatch(action) → ToolResult(exit_code=1, stderr="AssertionError...")
  ├─ 6. FeedbackEngine.analyze(result, round=1) → FeedbackResult(TEST_FAILURE, round=1, should_retry=True)
  ├─ 7. 回灌 → LLMClient.chat(context + full_error) → Action("write_file", "test_auth.py", ...)
  ├─ 8. GuardEngine.check(action) → GuardDecision(SAFE)
  ├─ 9. Executor.dispatch(action) → ToolResult(exit_code=0)
  ├─ 10. FeedbackEngine.analyze(result) → FeedbackResult(SUCCESS)
  └─ 11. 停机判断 → TaskResult(success=True)
```

### 5.4 外部依赖

| 依赖 | 用途 | 版本 | 选型理由 |
|------|------|------|----------|
| `httpx` | LLM API HTTP 调用 | ≥0.27 | 异步支持好，API 简洁，纯 Python |
| `pytest` | 测试框架 | ≥8.0 | 业界标准，fixture 和 parametrize 支持 |
| `python-dotenv` | `.env` 文件加载 | ≥1.0 | 轻量，零依赖 |
| `pyyaml` | 配置文件解析 | ≥6.0 | 纯 Python，标准 YAML 解析器 |

**零外部依赖原则：** 所有核心机制（治理、反馈、记忆、路径校验、命令解析）仅使用 Python 标准库（`pathlib`, `shlex`, `json`, `re`, `subprocess`, `getpass`, `dataclasses`），确保 Mock LLM 模式下无网络依赖即可运行全部测试。

---

## 6. 数据模型

### 6.1 实体定义

```python
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional

class Tool(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_SHELL = "execute_shell"
    RUN_TESTS = "run_tests"
    RUN_LINT = "run_lint"

class Verdict(Enum):
    SAFE = "SAFE"
    WARN = "WARN"
    BLOCK = "BLOCK"

class FeedbackCategory(Enum):
    SUCCESS = "SUCCESS"
    COMPILE_ERROR = "COMPILE_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    LINT_ERROR = "LINT_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class TaskStatus(Enum):
    SUCCESS = "success"
    ABORTED = "aborted"
    CIRCUIT_BREAKER = "circuit_breaker"

@dataclass
class Action:
    """LLM 返回的结构化动作"""
    tool: str                              # 工具名
    params: dict                           # 工具参数
    reason: str = ""                       # LLM 给出的执行理由

@dataclass
class ToolResult:
    """工具执行结果"""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0

@dataclass
class GuardRule:
    """治理规则"""
    id: str
    action_type: str                       # FileSystem | Shell | Network | Package
    scope: str                             # Workspace | Project | System
    risk_level: str                        # LOW | MEDIUM | HIGH | CRITICAL
    verdict: str                           # SAFE | WARN | BLOCK
    pattern: Optional[str] = None          # 正则匹配模式
    description: str = ""

@dataclass
class GuardDecision:
    """治理判定结果"""
    verdict: str                           # SAFE | WARN | BLOCK
    matched_rule: str = "default"
    reason: str = ""

@dataclass
class RiskInfo:
    """传递给 HITL 审批的风险信息"""
    action_summary: str                    # 动作摘要
    verdict: str                           # 风险等级
    matched_rule: str                      # 命中规则
    reason: str                            # 拦截原因

@dataclass
class ApprovalResult:
    """HITL 审批结果"""
    approved: bool
    reason: str = ""                       # 拒绝时用户填写的修改意见

@dataclass
class FeedbackResult:
    """反馈分析结果"""
    category: str
    round: int                             # 当前连续失败轮次
    should_retry: bool
    context_for_llm: str = ""              # 回灌给 LLM 的上下文

@dataclass
class Turn:
    """一次完整循环的记录"""
    turn_number: int
    timestamp: str
    action: Action
    guard_decision: GuardDecision
    approval: Optional[ApprovalResult] = None
    result: Optional[ToolResult] = None
    feedback: Optional[FeedbackResult] = None

@dataclass
class Task:
    """用户任务"""
    description: str
    context: dict = field(default_factory=dict)

@dataclass
class TaskResult:
    """任务执行结果"""
    status: str                            # success | aborted | circuit_breaker
    turns: list[Turn] = field(default_factory=list)
    summary: str = ""

@dataclass
class Session:
    """会话记录"""
    session_id: str
    created_at: str
    updated_at: str
    task_description: str
    decisions: list[dict] = field(default_factory=list)
    conventions: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    summary: str = ""
```

### 6.2 实体关系

```
Session 1 ──── * Decision
Session 1 ──── * Convention
Session 1 ──── * Error
Task    1 ──── 1 TaskResult
TaskResult 1 ──── * Turn
Turn    1 ──── 1 Action
Turn    1 ──── 1 GuardDecision
Turn    0..1 ── 1 ApprovalResult
Turn    0..1 ── 1 ToolResult
Turn    0..1 ── 1 FeedbackResult
```

### 6.3 约束

| 约束 | 说明 |
|------|------|
| `session_id` 唯一 | UUID v4，不可重复 |
| `Turn.turn_number` 递增 | 同会话内单调递增 |
| `GuardDecision.verdict` 枚举 | 仅允许 `SAFE` / `WARN` / `BLOCK` |
| `FeedbackResult.round` ≥ 1 | 最小为 1 |
| `Tool.exit_code` 约定 | 0 = 成功，非 0 = 失败，-1 = 超时，-2 = 工具不存在 |

---

## 7. 凭据与分发设计

### 7.1 凭据存储方案

**选型：`.env` 文件 + `getpass` 隐式输入**

放弃 `keyring` 库的原因：`keyring` 在 Linux 上依赖 D-Bus（WSL 和无 GUI 环境不可用），在 Windows 上依赖 Windows Credential Manager（需要额外配置）。为保持跨平台零配置可用性，采用 `.env` + `getpass` 方案。

**存储流程：**

1. 首次运行 `python run_cli.py` 时，检测 `.env` 是否存在且包含 `DEEPSEEK_API_KEY`。
2. 若不存在，提示用户运行 `python run_cli.py credential set`。
3. `credential set` 使用 `getpass.getpass("Enter API Key: ")` 隐式读取（不回显），写入 `.env`。
4. `.gitignore` 必须包含 `.env`，CI 中检查 `.env` 是否被误提交。

**查看/更新/清除：**

- `credential status`：仅输出"已配置"或"未配置"，不显示明文。
- `credential set`：覆盖现有 key。
- `credential clear`：删除 `.env` 中对应条目。

**风险标注（必须在 README 和 SPEC 中明确）：**

| 风险 | 说明 |
|------|------|
| `.env` 为明文 | 任何对文件系统有读权限的进程均可读取 |
| 进程环境可见 | `os.environ` 可被同进程及其子进程读取 |
| 不防内存 dump | 运行中的进程内存可能包含 key |
| 不防恶意依赖 | 第三方 Python 包可通过 `os.environ` 窃取 key |

**威胁模型：** 本方案防护的范围是"防止 key 通过 Git 泄漏"和"防止 key 出现在终端历史/日志中"。它不防护操作系统级攻击（如恶意软件读取文件系统或进程内存）。

### 7.2 分发设计

**形态：源码压缩包 + GitHub Release**

1. 源码通过 `git archive` 或 GitHub 的 "Download ZIP" 功能打包为 `.zip` / `.tar.gz`。
2. 每次 Release 附带源码压缩包。
3. `README.md` 提供一键安装脚本。

**安装脚本（`install.sh` / `install.ps1`）：**

```bash
# install.sh (Linux/macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "Installation complete. Run 'python run_cli.py credential set' to configure your API key."
```

```powershell
# install.ps1 (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Write-Host "Installation complete. Run 'python run_cli.py credential set' to configure your API key."
```

**目标平台：**

| 平台 | 架构 | 前提条件 |
|------|------|----------|
| Linux | x86_64 | Python 3.11+, pip |
| macOS | arm64 / x86_64 | Python 3.11+, pip |
| Windows | x86_64 | Python 3.11+, pip, PowerShell 5.1+ |

**已知限制：**

- 不支持 Python 3.10 及以下版本（依赖 `dataclasses` 标准库和 `pathlib.is_relative_to`）
- Shell 命令执行依赖于系统 shell（Linux/macOS: `/bin/sh`, Windows: `cmd.exe`）
- 不在沙箱/容器内运行 agent 时，工具执行器直接操作宿主机文件系统

---

## 8. 技术选型与理由

### 8.1 语言选型：Python 3.11+

| 考量 | 理由 |
|------|------|
| 开发效率 | 动态类型 + 丰富标准库，适合快速原型和迭代 |
| 标准库支持 | `pathlib`, `shlex`, `subprocess`, `json`, `dataclasses`, `getpass` 均为标准库，零额外依赖即可实现核心机制 |
| 可读性 | 代码即文档，便于评审和教学 |
| 生态 | `pytest` 测试框架成熟，`httpx` HTTP 客户端简洁 |
| 平台兼容 | 跨平台（Linux/macOS/Windows），无需编译 |
| 约束满足 | 符合"提供源码压缩包"的分发要求 |

### 8.2 LLM 供应商：DeepSeek

| 考量 | 理由 |
|------|------|
| API 兼容 | 兼容 OpenAI Chat Completions API 格式，`httpx` 直接调用 |
| 成本 | 性价比高，适合学生项目 |
| 能力 | DeepSeek V4 Pro 具备足够的代码生成和推理能力 |
| 接入方式 | 通过 `https://api.deepseek.com` 的 Chat Completions 端点 |

### 8.3 框架选型：不使用 Agent 编排框架

| 不使用 | 原因 |
|--------|------|
| LangChain / LangGraph | 作业 A.4-A 明确禁止使用现成 agent 编排框架的高层循环 |
| AutoGen / CrewAI | 同上，且这些框架将治理和反馈封装为提示词而非确定性代码 |
| LlamaIndex agent | 同上 |

**替代方案：** 使用 `httpx` 直接调用 LLM API，所有编排逻辑（循环、治理、反馈、记忆）由自己的代码实现。

### 8.4 测试框架：pytest

| 考量 | 理由 |
|------|------|
| 业界标准 | 最广泛使用的 Python 测试框架 |
| fixture 支持 | 适合 Mock LLM 和依赖注入的测试场景 |
| parametrize | 适合多维度规则测试（批量测试不同输入组合） |
| CI 集成 | 与 GitHub Actions 无缝集成 |

### 8.5 分发方式：源码压缩包 + GitHub Release

| 考量 | 理由 |
|------|------|
| 无需编译 | Python 源码可直接运行 |
| 跨平台 | 不绑定特定 CPU 架构 |
| 透明可审计 | 用户可审查源码 |
| 符合要求 | 用户明确选择"方案一：源码压缩包" |

---

## 9. 验收标准

| # | 验收项 | 可验证标准 | 验证方式 |
|---|--------|-----------|----------|
| AC1 | 主循环能跑 | 注入 `ScriptedMockLLM(action_queue)` 包含 3 个动作，`AgentLoop.run()` 完成全部 3 轮并返回 `TaskResult` | `pytest test_core.py` |
| AC2 | 治理护栏拦截危险动作 | `guard.check(Action("execute_shell", {"command": "rm -rf /"}))` 返回 `GuardDecision(verdict=Ver.BLOCK)` | `pytest test_guardrail.py` |
| AC3 | 治理护栏放行安全动作 | `guard.check(Action("read_file", {"path": "src/main.py"}))` 返回 `GuardDecision(verdict=Ver.SAFE)` | `pytest test_guardrail.py` |
| AC4 | 路径隔离拦截越界 | `guard.validate_path("../../../etc/passwd")` 返回 `BLOCK` | `pytest test_guardrail.py` |
| AC5 | Shell 命令双重校验 | `guard.check_shell_command("sudo rm -rf /")` 返回 `BLOCK`（不被 `sudo` 前缀绕过） | `pytest test_guardrail.py` |
| AC6 | 反馈分类器正确分类 | `feedback.analyze(ToolResult(exit_code=1, stderr="AssertionError"))` 返回 `TEST_FAILURE` | `pytest test_core.py` |
| AC7 | 多轮修正第 3 次熔断 | 注入连续 3 次 `TEST_FAILURE`，断言 `should_retry=False` | `pytest test_core.py` |
| AC8 | 成功重置计数器 | 失败 2 次 → 成功 1 次 → 失败 1 次，断言 `round=1`（非 3） | `pytest test_core.py` |
| AC9 | 失败类型变化重置计数器 | `TEST_FAILURE` → `COMPILE_ERROR`，断言 `round=1` | `pytest test_core.py` |
| AC10 | 记忆模块读写 | `save(session)` → `load(id)`，断言所有字段完整恢复 | `pytest test_session_store.py` |
| AC11 | 记忆模块检索 | `search("refactoring")` 返回 tags 包含 "refactoring" 的会话 | `pytest test_session_store.py` |
| AC12 | 凭据状态不回显明文 | `credential status` 输出不含 key 的明文内容 | `pytest test_credential.py` |
| AC13 | 配置文件加载 | `config.load("guard_rules.yaml")` 返回 `List[GuardRule]` | `pytest test_config.py` |
| AC14 | WARN 默认自动执行 | `guard.check(action)` 返回 `WARN`，主循环执行该动作 | `pytest test_core.py` |
| AC15 | `--strict` 模式 WARN 升格 | `guard.check(action)` 返回 `WARN`，strict 模式下触发 `request_approval()` | `pytest test_core.py` |
| AC16 | HITL 拒绝回灌 | `request_approval()` 返回 `ApprovalResult(approved=False, reason="改用 pip")`，断言 `reason` 被注入下一轮 LLM 上下文 | `pytest test_core.py` |
| AC17 | 机制演示三项 | ① 护栏拦截 ② 反馈修正 ③ 熔断 HITL — 三项全在 mock LLM 下确定性地通过 `python demo.py` | `python demo.py` |
| AC18 | 一键测试全绿 | `pytest` 无网络依赖，全部通过 | `pytest` |
| AC19 | CI 通过 | GitHub Actions 中 `unit-test` job 全部通过 | CI 日志 |
| AC20 | 无真实凭据提交 | `git log -p` 无任何 API Key 明文 | 人工检查 |

---

## 10. 风险与未决问题

### 10.1 已识别风险

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|----------|
| LLM 输出非结构化 JSON | 动作解析失败，循环中断 | 中 | 重试解析（最多 2 次）+ 正则兜底提取 + 失败后 HITL |
| 上下文腐化（Context Rot） | 多轮后 LLM 遗忘早期约束，行为偏离 | 高 | 关键约束在每轮上下文末尾重复注入；定期摘要机制 |
| 无限修正循环 | 即使有熔断，LLM 可能在 3 轮内做出表面的"不同"修复但本质未解决 | 中 | 引入 diff 相似度检测（如连续 2 次 diff 相似度 > 90% 则提前熔断） |
| 命令注入绕过 | 攻击者构造特殊 payload 绕过 shlex 或正则 | 低 | 双重校验 + 白名单优先于黑名单 |
| 跨平台 shell 差异 | `shlex.split()` 在 Windows 和 Linux 上行为可能不同 | 低 | CI 中同时在 Ubuntu 和 Windows 上运行测试 |
| 大规模会话文件 | 长期使用后 session JSON 文件过大 | 低 | 文件大小超过 1MB 时自动归档并创建新会话 |
| `.env` 明文泄漏 | 文件系统权限配置不当导致 key 泄漏 | 中 | 文档明确标注风险；安装脚本提示设置文件权限 `chmod 600 .env` |
| 依赖注入复杂度 | 构造函数参数过多，可读性下降 | 低 | 引入简单的 `HarnessBuilder` 工厂模式 |

### 10.2 v1.0 范围决策

以下事项已在进入 PLAN 阶段前确定为 v1.0 版本的明确范围：

| 问题 | v1.0 决策 | 理由 |
|------|-----------|------|
| 记忆模块检索算法 | 采用简单关键词/Tag 严格匹配，TF-IDF 划入 Future Work | 降低初版复杂度，聚焦治理主维度 |
| 多 LLM 供应商切换 | 仅实现 DeepSeek Client，接口抽象（LLMClient）预留扩展性 | 避免过度设计 |
| 命令行交互模式 | 仅实现 `--task` 单次任务模式，REPL 交互模式划入 Future Work | 聚焦核心闭环验证，降低 CLI 复杂度 |
| 最大轮次阈值 | 固定 50 轮，后续根据实际日志优化 | 提供确定性的默认熔断上界 |
| Docker 沙箱执行 | 不实现，纯本地 Workspace 目录隔离 | 减少环境依赖 |

---

## 11. 领域与机制设计（重点章节）

### 11.1 领域分析：Coding 场景的四类机制

#### 动作/工具

Coding agent 需要与代码仓库交互。以下工具覆盖了"读代码 → 改代码 → 验证代码"的完整闭环：

| 工具 | 编码实现 | 说明 |
|------|----------|------|
| `read_file` | `pathlib.Path(path).read_text()` | 读取文件内容，需通过路径边界校验 |
| `write_file` | `pathlib.Path(path).write_text(content)` + `parent.mkdir(parents=True, exist_ok=True)` | 写入文件，自动创建父目录，需通过路径边界校验 |
| `execute_shell` | `subprocess.run(command, shell=True, timeout=30, capture_output=True, text=True, cwd=workspace)` | 执行 shell 命令，需通过 shlex + 正则双重校验 |
| `run_tests` | `subprocess.run(["pytest", target, "-q"])` | 运行测试，返回 exit code 和输出 |
| `run_lint` | `subprocess.run(["ruff", "check", target])` | 运行 lint，返回 exit code 和输出 |

**工具分发机制：** `Executor` 维护一个 `{tool_name: callable}` 注册表，`dispatch(action)` 按 `action.tool` 路由到对应函数。新增工具只需注册，无需修改主循环。

#### 客观反馈信号

Coding 领域的反馈信号天然是客观的——进程 exit code 和结构化输出不依赖 LLM 的"判断"：

| 信号来源 | 编码实现 | 客观性 |
|----------|----------|--------|
| 测试结果 | 解析 pytest exit code + 输出 | 0 = 通过，非 0 = 失败，完全确定 |
| Lint 结果 | 解析 ruff exit code + 输出 | 同上 |
| Shell 命令 | 解析 exit code + stderr | 同上 |
| 类型检查 | 子进程调用 mypy/pyright | 同上 |

**反馈回灌机制：** `FeedbackEngine.analyze(result)` 解析 `ToolResult` → 结构化分类 → 按轮次策略构造不同粒度的上下文 → 注入下一轮 LLM 请求的 messages 中。

#### 危险动作

Coding agent 最危险的场景是：读写文件系统、执行 shell 命令、访问网络。以下危险类别必须被治理：

| 危险类别 | 示例 | 风险等级 |
|----------|------|----------|
| 破坏性文件操作 | `rm -rf /`, 删除 `.git/`, 覆盖系统配置文件 | CRITICAL |
| 系统级命令 | `shutdown`, `reboot`, `chmod 777 /`, `mkfs` | CRITICAL |
| 网络外发 | `curl ... | bash`, `wget -O - | sh` | HIGH |
| Git 破坏性操作 | `git push --force`, `git reset --hard HEAD~N` | HIGH |
| 越权访问 | 读写 workspace 外的文件 | CRITICAL |
| 包管理 | `pip install` 不受信任的包 | MEDIUM |

#### 记忆需求

| 需要记住 | 原因 | 实现方式 |
|----------|------|----------|
| 项目约定 | 避免每轮重复询问（如"用 pytest 还是 unittest"） | `Session.conventions` 字典 |
| 历史决策 | 防止重复犯错（如"上次 `dataclass` 方案被否决是因为序列化问题"） | `Session.decisions` 列表 |
| 错误模式 | 识别反复出现的同类错误，提前熔断 | `Session.errors` 列表 + 计数器 |
| 任务摘要 | 跨会话理解上下文 | `Session.summary` + `tags` |

### 11.2 重点维度：治理（Governance）

**为什么选治理作为 Main Contribution：**

1. **天然确定性**：治理的每个环节（识别、分类、审批、执行/阻止）都是代码逻辑，移除 LLM 后仍可完全测试。
2. **工程深度**：多维度规则引擎 + 配置文件驱动 + HITL 状态机 + 路径隔离 + 命令解析，构成了一个完整的防御体系。
3. **安全价值**：coding agent 的治理是"能不能用"的前提——没有可靠护栏的 agent 在真实项目中不可部署。
4. **与作业 A.4-C 对齐**：治理完全满足"移除 LLM 后仍能单测验证"的硬标准。

### 11.3 治理引擎深度设计

#### 规则模型

```python
@dataclass
class GuardRule:
    id: str
    action_type: str          # FileSystem | Shell | Network | Package
    scope: str                # Workspace | Project | System
    risk_level: str           # LOW | MEDIUM | HIGH | CRITICAL
    verdict: str              # SAFE | WARN | BLOCK
    pattern: Optional[str]    # 可选：正则匹配命令内容
    description: str
```

#### 状态机

```
                 ┌──────────┐
                 │  Action  │
                 └────┬─────┘
                      │
              ┌───────▼───────┐
              │   IDENTIFY    │  解析 action 类型、作用域、匹配规则
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   CLASSIFY    │  按维度匹配规则 → 输出 verdict
              └───┬───┬───┬───┘
                  │   │   │
         SAFE     │  WARN    BLOCK
          │       │   │       │
          │   ┌───▼───▼──┐ ┌──▼──────────┐
          │   │  LOG +   │ │  APPROVAL   │
          │   │  EXECUTE │ │  (HITL)     │
          │   │(--strict?│ │  via        │
          │   │ →HITL)   │ │  request_   │
          │   └───┬──────┘ │  approval() │
          │       │        └──┬────┬─────┘
          │       │           │    │
          │       │      Approve │ Reject
          │       │           │    │
          └───────┴───────────┘    │
                  │                │
          ┌───────▼───────┐ ┌──────▼──────────┐
          │    EXECUTE    │ │    BLOCK         │
          │  (分发执行)   │ │ (回灌拒绝理由     │
          │              │ │  给 LLM)          │
          └──────────────┘ └──────────────────┘
```

#### 路径隔离

所有文件操作在执行前必须通过路径边界校验。**使用 `pathlib.Path(target).resolve().is_relative_to(workspace)` 进行物理路径解析**，而非字符串前缀匹配。这防止了 `../`、符号链接、硬链接等路径遍历攻击。

```python
def validate_path(self, target: str) -> GuardDecision:
    resolved = pathlib.Path(target).resolve()
    if not resolved.is_relative_to(self.workspace):
        return GuardDecision(
            verdict=Ver.BLOCK,
            matched_rule="path-boundary",
            reason=f"路径越界：{target} 不在 workspace {self.workspace} 内"
        )
    return GuardDecision(verdict=Ver.SAFE, matched_rule="default", reason="")
```

#### Shell 命令安全解析

命令安全匹配采用 **Python 标准库 `shlex` 词法解析 + 正则模式双重校验**：

- `shlex.split()` 正确处理引号、转义和空格，防止注入绕过
- 匹配逻辑同时检查**完整命令**（`re.search`）和**首词**（`re.fullmatch`），防止 `sudo`、`env`、`nice` 等前缀绕过

```python
import shlex
import re

def check_shell_command(self, command: str) -> GuardDecision:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return GuardDecision(verdict=Ver.BLOCK, reason="命令解析失败")

    cmd_name = tokens[0] if tokens else ""

    # 完整命令匹配 或 首词命中危险指令 → 均触发拦截
    is_matched = any(
        re.search(rule.pattern, command) or re.fullmatch(rule.pattern, cmd_name)
        for rule in self.shell_rules
    )

    if is_matched:
        matched = next(r for r in self.shell_rules
                       if re.search(r.pattern, command) or re.fullmatch(r.pattern, cmd_name))
        return GuardDecision(
            verdict=matched.verdict,
            matched_rule=matched.id,
            reason=matched.description
        )

    return GuardDecision(verdict=Ver.SAFE, matched_rule="default", reason="")
```

#### 配置文件驱动

```yaml
# guard_rules.yaml
rules:
  - id: "fs-delete-system"
    action_type: "FileSystem"
    scope: "System"
    risk_level: "CRITICAL"
    verdict: "BLOCK"
    pattern: "delete|rm|unlink"
    description: "禁止删除系统级文件"

  - id: "shell-dangerous"
    action_type: "Shell"
    scope: "System"
    risk_level: "CRITICAL"
    verdict: "BLOCK"
    pattern: "rm -rf /|shutdown|reboot|mkfs|:.*:.*:"
    description: "禁止执行危险系统命令"

  - id: "shell-sudo-rm"
    action_type: "Shell"
    scope: "System"
    risk_level: "CRITICAL"
    verdict: "BLOCK"
    pattern: "rm\\s+(-[a-zA-Z]*r[a-zA-Z]*f?|-rf|--recursive)"
    description: "禁止递归删除命令（含 sudo 前缀也能匹配）"

  - id: "network-outbound"
    action_type: "Network"
    scope: "System"
    risk_level: "HIGH"
    verdict: "BLOCK"
    pattern: "curl.*\\|.*(bash|sh|python|perl)|wget.*-O.*\\|.*sh"
    description: "禁止从网络下载并执行脚本"

  - id: "git-force-push"
    action_type: "Shell"
    scope: "Project"
    risk_level: "HIGH"
    verdict: "BLOCK"
    pattern: "git\\s+push\\s+.*(--force|-f)"
    description: "禁止强制推送"
```

### 11.4 机制可测试性验证

所有机制在移除真实 LLM 后，通过 `ScriptedMockLLM` 注入预定义动作序列，进行确定性单元测试：

| 机制 | Mock LLM 下的单测示例 | 断言 |
|------|----------------------|------|
| 治理拦截 | `guard.check(Action("execute_shell", {"command": "rm -rf /"}))` | `BLOCK` |
| `sudo` 不绕过 | `guard.check_shell_command("sudo rm -rf /")` | `BLOCK` |
| 路径隔离 | `guard.validate_path("../etc/passwd")` | `BLOCK` |
| 安全动作放行 | `guard.check(Action("read_file", {"path": "src/main.py"}))` | `SAFE` |
| 反馈分类 | `feedback.analyze(ToolResult(exit_code=1, stderr="AssertionError"))` | `TEST_FAILURE` |
| 多轮修正 | 注入 ScriptedMockLLM([Action("run_tests"), Action("write_file"), Action("run_tests")]) + 连续 3 次失败结果 | `should_retry=False` (第 3 轮) |
| 熔断 | `feedback.analyze(ToolResult(exit_code=1), round=3)` | `should_retry=False` |
| 成功重置 | 失败 2 次 → 成功 1 次 → 失败 1 次 | `round=1` |
| 记忆读写 | `store.save(session)` → `store.load(id)` | 字段完整恢复 |
| 记忆检索 | `store.search(["refactoring"])` | 返回匹配会话 |
| 主循环完整流程 | 注入 ScriptedMockLLM([Action("read_file"), Action("write_file"), Action("run_tests")]) → `agent.run(task, session)` | `TaskResult.status=SUCCESS`, `len(turns)=3` |

### 11.5 机制演示设计

`demo.py` 在 mock LLM 模式下确定性地复现以下三项行为：

1. **治理护栏拦截危险动作**：注入 `Action("execute_shell", {"command": "rm -rf /"})` → 断言 `GuardDecision(verdict=BLOCK)` → 终端输出拦截信息。
2. **反馈闭环驱动修正**：注入 `ScriptedMockLLM` 序列：`run_tests` → 注入 `TEST_FAILURE` → `write_file` → `run_tests` → 注入 `SUCCESS`。断言 agent 在收到失败反馈后改变了下一步动作。
3. **熔断 HITL**：连续注入 3 次 `TEST_FAILURE`，断言第 3 次后触发熔断，`should_retry=False`。

```bash
python demo.py
# 输出：
# [PASS] Demo 1: Guardrail blocked "rm -rf /"
# [PASS] Demo 2: Feedback loop corrected action after test failure
# [PASS] Demo 3: Circuit breaker triggered after 3 consecutive failures
# All 3 demos passed.
```
### 11.6 与作业 A.4-C 的对齐：移除 LLM 后的可测试性

作业要求：移除真实 LLM 后，每个核心机制仍能通过确定性单元测试验证。本设计全部满足：

| 机制 | 移除 LLM 后的测试方式 | 对应 AC |
|------|----------------------|---------|
| 治理护栏 | 直接调用 `guard.check()`，传入构造的 Action | AC2-AC5 |
| 反馈分类 | 直接调用 `feedback.analyze()`，传入构造的 ToolResult | AC6 |
| 多轮修正 | 通过 `ScriptedMockLLM` 注入失败/成功序列 | AC7-AC9 |
| 路径隔离 | 直接调用 `validate_path()`，传入构造的路径 | AC4 |
| 记忆读写 | 直接调用 `store.save()` / `load()` / `search()` | AC10-AC11 |
| 主循环流程 | `AgentLoop` 注入 `ScriptedMockLLM` + `SilentIO` | AC1, AC13-AC15 |

所有机制测试均不依赖网络、不调用真实 LLM API，100% 运行于纯本地环境。
---

> **最终决策小结**
>
> **采纳/确定：**
> - Q1 = C（多轮修正状态机：结构化分类 + 连续同类失败计数 + 3 轮熔断）
> - Q2 = B（结构化 JSON Session Store，关键词匹配检索，无向量库/RAG）
> - Q3 = C（多维度治理分级：SAFE/WARN/BLOCK，YAML 配置文件驱动）
> - WARN 行为：默认自动执行 + `--strict` 命令行开关升格为 HITL
> - 修正轮次：按连续同类失败计数，成功即重置；失败类型变化亦重置
> - 凭据方案：放弃 keyring，仅用 `.env` + `getpass` 隐式输入
> - 路径隔离：`pathlib.Path.resolve().is_relative_to()` 物理路径校验
> - Shell 命令：`shlex` 词法解析 + `re.search` 完整命令 + `re.fullmatch` 首词双重校验，防 `sudo` 绕过
> - IO 接口：`request_approval()` 替代 `confirm()`，支持用户拒绝时输入修改意见回灌 LLM
> - 依赖注入：`AgentLoop` 构造函数注入所有依赖，测试时无缝替换
> - Mock LLM：`ScriptedMockLLM` 设计，支持注入 `List[Action]` 动作队列
> - `write_file` 建图保障：`target.parent.mkdir(parents=True, exist_ok=True)`
>
> **否决/修改：**
> - keyring 方案被否决（WSL/无 GUI 环境 D-Bus 依赖风险）
> - WARN 审批环节被修改为"默认自动执行 + `--strict` 开关"
> - Shell 匹配逻辑从 `tokens[0] + re.fullmatch` 修改为 `re.search(command) or re.fullmatch(cmd_name)` 双重校验
>
> **签字确认：** 用户已授权生成完整 SPEC.md