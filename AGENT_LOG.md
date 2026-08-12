# AGENT_LOG.md — Coding Agent Harness 开发日志

> AI4SE 期末项目 A · 颜鑫 · 2026-08

## 概述

本项目使用 Superpowers 七步工作流（brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch），通过 6 个 git worktree 分支并行开发，所有核心机制通过 mock LLM 进行确定性单元测试。

**Superpowers 技能使用统计：**
- brainstorming: 1 次（需求澄清）
- writing-plans: 1 次（18 个 task 的详细实现计划）
- using-git-worktrees: 1 次（创建 6 个 worktree 分支）
- subagent-driven-development: 6 次（每个 worktree 分支一个 subagent）
- test-driven-development: 贯穿全部 18 个 task
- requesting-code-review: 1 次（发现 2 Critical + 5 Important）
- finishing-a-development-branch: 1 次

---

## 日志

### 2026-08-09 — 需求分析与设计

| 时间 | 事件 | 技能 | 详情 |
|------|------|------|------|
| 全天 | 需求分析 | brainstorming | 分析作业 A 要求，确定治理为重点维度，技术栈选 Python 3.11+，禁框架 |
| 全天 | 设计文档 | writing-plans | 输出 SPEC.md（11 章，1169 行）和 PLAN.md（18 task，2465 行） |
| 全天 | 冷启动验证 | — | 用全新 agent 验证 SPEC/PLAN 可执行性，发现 3 个缺陷（GuardDecision 类型不一致、缺 git init、pytest 未安装）并修复 |

**关键决策：**
- 放弃 keyring 库，仅用 `.env` + `getpass`（规避 WSL 无 GUI 环境 D-Bus 风险）
- 护栏采用路径隔离 + Shell 双重校验（shlex 词法解析 + 正则模式匹配）
- 凭据威胁模型：防护 Git 泄漏和终端历史，不防护操作系统级攻击

---

### 2026-08-09 — Phase 1-2 基础设施

| 时间 | 事件 | Worktree | Commit |
|------|------|----------|--------|
| 下午 | T01-T02: 脚手架 + 数据模型 | phase1-infra | `66fc7c5` |
| 下午 | T03: Mock LLM | phase2-base | `c70229c` |
| 下午 | T04: 配置加载（含 BUILTIN_RULES） | phase2-base | `ddd5663` |
| 下午 | T05-T06: 凭据管理 + 会话存储 | phase2-base | `fb818e6` |

**Subagent 策略：** T03, T04, T05, T06 为 4 个并行独立 task，由一个 subagent 在 phase2-base 分支中串行完成。

**关键工艺：**
- `BUILTIN_RULES` 硬编码在 `config.py` 中，YAML 文件缺失时自动降级，确保核心机制不依赖配置文件
- Mock LLM 设计为 FIFO 队列，完全不读取对话上下文，确保测试的确定性

---

### 2026-08-09 — Phase 3 治理维度（主要贡献）

| 时间 | 事件 | Worktree | Commit |
|------|------|----------|--------|
| 下午 | T07: GuardEngine 骨架 | phase3-governance | `564c6bd` |
| 下午 | T08: 路径隔离（resolve + is_relative_to） | phase3-governance | `62a96f6` |
| 下午 | T09: Shell 双重校验（shlex + regex） | phase3-governance | `5bf73b6` |
| 下午 | T10: 护栏状态机集成（23 个参数化测试） | phase3-governance | `5f9d8b6` |

**Subagent 策略：** T07→T08→T09→T10 为严格串行依赖，由一个 subagent 在 phase3-governance 分支中完成。

**关键工艺：**
- `validate_path()` 使用 `Path.resolve()` 解析软链接，防止符号链接绕过
- `check_shell_command()` 使用 `shlex.split()` 词法解析 + 正则双重校验，防止 `sudo`、`env` 等前缀绕过
- 护栏规则：SAFE/WARN/BLOCK 三级判决，多规则匹配时取最高优先级

---

### 2026-08-09 — Phase 4-6 核心循环

| 时间 | 事件 | Worktree | Commit |
|------|------|----------|--------|
| 下午 | T11: 工具执行器（5 个工具 + mkdir 保障） | phase4-executor | `70a23d4` |
| 下午 | T12: 反馈引擎（7 种分类 + 熔断） | phase5-core | `fd263ea` |
| 下午 | T13: AgentLoop 主循环（依赖注入 + 7 步） | phase5-core | `b30308d` |
| 下午 | T14: 集成测试 | phase5-core | `b918c21` |
| 下午 | T15: CLI 入口 + DeepSeekClient | phase6-io | `38ae1d8` |
| 下午 | T16-T18: demo.py + CI + README | phase6-io | `903447d` |

**Subagent 策略：** T11 独立 subagent → T12-T14 串行 subagent → T15-T18 串行 subagent。

**关键工艺：**
- AgentLoop 通过构造函数依赖注入所有外部依赖（llm, guard, executor, feedback, io），测试时替换为 mock/stub
- 反馈引擎：SUCCESS 重置计数器，3 次同类失败触发熔断（circuit_breaker）
- CLI 通过 `--mock` 开关切换 MockLLM/DeepSeekClient，零修改

---

### 2026-08-09 — 代码审查与修复

| 时间 | 事件 | Commit |
|------|------|--------|
| 下午 | 代码审查 | requesting-code-review |
| 下午 | 修复 Critical: 反馈上下文注入 LLM | `01550a8` |
| 下午 | 修复 Critical: YAML 正则转义 | `01550a8` |
| 下午 | 修复: Action 导入错误 + BLOCK 拒绝回灌 + LINT_ERROR 分类 | `a3d6e59` |

**人工修改：**
- `src/harness_core.py`: `context_for_llm` 已计算但未注入 LLM messages，导致反馈闭环失效
- `guard_rules.yaml`: `C:\\Windows\\` 反斜杠转义后变成 `C:\Windows\`，正则匹配失败
- `src/models.py`: `Action` 导入路径错误

**留下的 5 个 Important 问题（不阻塞合并）：**
- session_store 注入但未使用
- 缺少 scope 过滤
- 缺少 conventions 模型
- 重复迭代检测
- STM 测试缺口

---

### 2026-08-12 — GUI 测试辅助

| 时间 | 事件 | Commit |
|------|------|--------|
| 上午 | GUI 设计文档（Tkinter，零新依赖） | `6df9b1c` |
| 上午 | GUI 实现（逐轮展示 + HITL 审批） | `e193b51` |
| 上午 | 会话持久化接入 AgentLoop | `bc40762` |
| 上午 | GUI API Key 输入框 | `a3f483e` |

**说明：** GUI 为个人调试测试工具，非作业要求。

---

### 2026-08-12 — 真实 API 测试与系统提示词优化

| 时间 | 事件 | Commit |
|------|------|--------|
| 上午 | 英语提示词（DeepSeek 对英文 JSON 指令更稳定） | `9716974` |
| 上午 | CLI verbose 模式 | `57b49d8` |
| 上午 | 参数名兼容（file_path, file, filepath） | `91a984c` ~ `9e78601` |
| 上午 | 重复成功循环检测（5 次后强制结束） | `1aba491` ~ `7ce2f94` |

**关键发现：**
- DeepSeek 对中文提示词 JSON 格式执行不稳定，英文提示词显著改善
- LLM 在成功完成任务后容易陷入重复循环（如连续重写同一个文件），添加了重复动作检测和强制结束机制
- LLM 使用的参数名（`file_path`, `file`, `filepath`）与代码期望的 `path` 不一致，Executor 需要兼容多种参数名

---

### 2026-08-12 — 场景化 MockLLM 与测试增强

| 时间 | 事件 | Commit |
|------|------|--------|
| 上午 | ScenarioMockLLM（6 场景 + 7 测试） | `2062295` |
| 上午 | 治理场景 + CLI --scenario 标志 | `d33e7b8` ~ `d625567` |
| 上午 | 修复 executor 工作区路径（相对路径改为 workspace/path） | `2062295` |

**关键发现：**
- `read_file`/`write_file` 使用 `Path(params["path"])` 相对 CWD，应改为 `self.workspace / params["path"]`
- 默认 Mock 模式改为治理场景，不再硬编码 `read_file("README.md")`

---

### 2026-08-12 — 4 个高级治理任务

| 时间 | 事件 | Commit |
|------|------|--------|
| 上午 | Task 1: 软链接逃逸（2 测试，Windows 需管理员权限） | `8ef1093` |
| 上午 | Task 2: Shell 混淆拦截（`$IFS` 注入修复 + 5 测试） | `8ef1093` |
| 上午 | Task 3: 拒绝回灌自修正（场景 + 测试） | `8ef1093` |
| 上午 | Task 4: 超时熔断（已有测试） | `8ef1093` |
| 上午 | 修复: Filesystem 规则 pattern 从未被检查（死代码） | `40d6ec3` |

**关键发现：**
- `$IFS` 注入是真实漏洞：`rm$IFS-rf$IFS/` 绕过了正则匹配，修复为 `normalize.replace('$IFS', ' ')`
- `guard_rules.yaml` 的 `fs-delete-system` 规则从未被检查：代码只匹配 Shell 动作的 pattern，FileSystem 动作的 pattern 被跳过
- 路径隔离已使用 `Path.resolve()`，软链接攻击在代码层面已防护（Windows 上需管理员权限创建软链接）

---

### 2026-08-12 — 5 个高级鲁棒性任务

| 时间 | 事件 | Commit |
|------|------|--------|
| 下午 | Task 1: 环境变量隔离（白名单 + 输出脱敏，2 测试） | `91fea0b` |
| 下午 | Task 2: 死循环熔断（已有 circuit_breaker） | `91fea0b` |
| 下午 | Task 3: 输出截断（3000 chars 头尾采样，2 测试） | `91fea0b` |
| 下午 | Task 4: JSON 容错解析（Markdown 提取 + 尾逗号修复，6 测试） | `91fea0b` |
| 下午 | Task 5: 原子写入回滚（`ast.parse` 校验 + 备份恢复，2 测试） | `91fea0b` |

**关键发现：**
- 子进程继承了全部父进程环境变量，LLM 可直接读取 `DEEPSEEK_API_KEY`，修复为白名单环境变量
- 超大输出（如 `cat large_file.log`）直接发送给 LLM 会溢出上下文窗口，添加 3000 chars 截断
- JSON 解析器过于脆弱，只接受完美 JSON，添加了 Markdown 代码块提取、尾逗号修复、正则兜底
- 文件写入无语法校验，修复为 `ast.parse` 校验 + 自动回滚

---

## 最终交付

| 指标 | 数值 |
|------|------|
| 测试 | 87 passed, 2 skipped（零网络依赖） |
| 文件 | 25 个核心源文件 |
| Commits | 44 个（含 6 个 merge commit） |
| Worktree 分支 | 6 个（phase1-infra ~ phase6-io） |
| 测试覆盖 | 治理 33 个，反馈 9 个，执行器 9 个，场景 8 个，JSON 解析 6 个，核心 5 个，等 |

**Superpowers 反思：**
- TDD 在 AI 协作下是放大器而非阻碍：先写测试让 subagent 有明确的目标，减少了"偏离主题"的几率
- subagent-driven 工作流的关键在于 task 颗粒度：太大的 task 导致 subagent 偏离，太小的 task 产生过多分支
- SPEC/PLAN 质量直接影响实现质量：冷启动验证暴露的 3 个缺陷验证了"规约不清导致 subagent 偏离"的假设
- 凭据与分发要求迫使想清楚了一台全新机器从零运行的完整流程