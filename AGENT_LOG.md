# AGENT_LOG.md — Coding Agent Harness 开发日志

> AI4SE 期末项目 A · 颜鑫 · 2026-08

## 概述

本项目使用 Superpowers 七步工作流（brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch），通过 6 个 git worktree 分支并行开发，所有核心机制通过 mock LLM 进行确定性单元测试。

**Superpowers 技能使用统计：**
- brainstorming: 1 次（3 轮迭代，需求澄清 + 架构决策）
- writing-plans: 1 次（3 轮迭代，18 个 task 的详细实现计划）
- using-git-worktrees: 1 次（创建 6 个 worktree 分支）
- subagent-driven-development: 6 次（每个 worktree 分支一个 subagent）
- test-driven-development: 贯穿全部 18 个 task
- requesting-code-review: 1 次（发现 2 Critical + 5 Important）
- finishing-a-development-branch: 1 次

---

## 日志

### 2026-08-04 — 项目初始化与 Superpowers 配置

| 时间 | 事件 | Commit |
|------|------|--------|
| 晚上 | 初始提交：创建仓库、导入 Superpowers 全部技能文件（55 个文件，9830 行） | `9051452` |
| 晚上 | 切换至官方 Superpowers plugin 配置 | `b286de4` |
| 晚上 | 移除手动 .opencode plugins，改用官方配置 | `52bff9c` |
| 晚上 | 清理 hom_require 目录中无关文件 | `a63f1b2` |

**关键操作：**
- 在 `.opencode/plugins/superpowers/` 下部署了 brainstorming、writing-plans、using-git-worktrees、subagent-driven-development、test-driven-development、requesting-code-review、receiving-code-review、finishing-a-development-branch、verification-before-completion、writing-skills、dispatching-parallel-agents、systematic-debugging、executing-plans 等全部技能
- 作业要求文件（通用要求、A 类项目要求、PROJECT_AGENT_REFERENCE）放入 `hom_require/` 目录

---

### 2026-08-06 — 需求分析与设计（Brainstorming + Writing-Plans）

详见 [SPEC_PROCESS.md](./SPEC_PROCESS.md)，完整记录了 brainstorming 和 writing-plans 的 3+3 轮迭代过程。

**Brainstorming 阶段（3 轮）：**

| 时间 | 事件 | 详情 |
|------|------|------|
| 上午 | 第 1 轮：大纲输出 + 架构质询 | 智能体阅读三份作业要求后输出 11 章大纲，提出 3 个架构决策问题：反馈闭环粒度（选 C 多轮修正状态机）、记忆方案（选 B 结构化 Session Store）、治理分类体系（选 C 多维度分级） |
| 上午 | 第 2 轮：核心三章草稿 + 再次质询 | 智能体展示功能规约、系统架构、领域与机制设计三章草稿。我修正了 Shell 匹配逻辑 Bug（`tokens[0] + re.fullmatch` 改为 `re.search + re.fullmatch` 双重校验）、补充了文件写入建图保障、规范化了 MockLLM 设计 |
| 上午 | 第 3 轮：签字确认 + 生成完整 SPEC | 核心三章确认后生成完整 SPEC.md（11 章，1169 行）。智能体自行发现并修复 2 个问题：实体关系图不一致、REPL 模式矛盾 |

**第 2 轮关键决策：**

| 质询 | 决策 |
|------|------|
| WARN 是否跳过审批环节 | 默认自动执行 + 日志记录；`--strict` 命令行开关升格为 HITL |
| 修正轮次计数单位 | 按"连续同类失败"计数；成功即重置；失败类型变化亦重置 |
| 是否引入 keyring | 放弃 keyring（回避 WSL/D-Bus 依赖），仅用 `.env` + `getpass` |

**Writing-Plans 阶段（3 轮）：**

| 时间 | 事件 | 详情 |
|------|------|------|
| 下午 | 第 1 轮：Task 拆解框架 + 策略质询 | 按模块分组输出 18 个 task（7 个 Phase），提出 4 个策略问题：Worktree 粒度（选 C 混合）、治理 task 组织（选 A 自底向上）、测试基础设施（选 A 独立前置）、AC 优先级（选 C 关键路径优先） |
| 下午 | 第 2 轮：完整 Task 列表细化 + 边界确认 | 每个 task 含目标、涉及文件、实现要点、验证步骤（含失败测试代码）、commit 信息 |
| 下午 | 第 3 轮：生成 PLAN.md + 质量审查 | 生成完整 PLAN.md（2442 行，18 个 task）。智能体自行发现并修复 3 个问题：`ApprovalResult` 重复定义、导入路径错误、`DeepSeekClient` 缺失 |

**冷启动验证（§4.5 自我验证）：**

| 时间 | 事件 | Commit |
|------|------|--------|
| 下午 | 使用全新 agent 仅凭 SPEC + PLAN 实现 T01-T02，暴露 3 个缺陷 | `a3f7fbf` |
| 下午 | 修复：`GuardDecision.verdict` 类型 `str` → `Verdict` 枚举 | `a3f7fbf` |
| 下午 | 修复：PLAN T01 新增 `git init` 步骤 | `daa47ab` |
| 下午 | 低优先级：pytest 未安装（agent 未执行 `pip install` 步骤） | 无需修改文档 |

**冷启动验证暴露的 3 个问题：**

| # | 问题 | 根因 | 严重性 |
|---|------|------|--------|
| 1 | `GuardDecision.verdict` 声明为 `str` 但代码示例使用 `Ver.BLOCK` | SPEC 类型声明与 PLAN 代码示例不一致 | 中 |
| 2 | `git check-ignore .env` 失败：目录不是 Git 仓库 | PLAN 缺少 `git init` 步骤 | 高 |
| 3 | `pytest` 未安装 | agent 未按顺序执行 `pip install`，非文档缺陷 | 低 |

**关键决策汇总：**
- 放弃 keyring 库，仅用 `.env` + `getpass`（规避 WSL 无 GUI 环境 D-Bus 风险）
- 护栏采用路径隔离 + Shell 双重校验（shlex 词法解析 + 正则模式匹配）
- 凭据威胁模型：防护 Git 泄漏和终端历史，不防护操作系统级攻击
- 反馈闭环：第 1 次全量错误上下文 → 第 2 次精简范围提示 → 第 3 次熔断并暂停等待人工介入
- 治理分类：操作类型 × 风险等级 × 作用域 三维矩阵，YAML 配置驱动

---

### 2026-08-06/07 — 规约修正 + Phase 1-2 基础设施

| 时间 | 事件 | Worktree | Commit |
|------|------|----------|--------|
| 下午 | 根据冷启动验证结果更新 SPEC 和 PLAN | master | `c70229c` |
| 下午 | T01-T02: 脚手架 + 数据模型 | phase1-infra | `66fc7c5` |
| 晚上 | T03: Mock LLM（ScriptedMockLLM FIFO 队列） | phase2-base | `c70229c` |
| 晚上 | T04: 配置加载（含 BUILTIN_RULES 降级） | phase2-base | `ddd5663` |
| 晚上 | T05-T06: 凭据管理 + 会话存储 | phase2-base | `fb818e6` |

**Subagent 策略：** T03, T04, T05, T06 为 4 个并行独立 task，由一个 subagent 在 phase2-base 分支中串行完成。

**关键工艺：**
- `BUILTIN_RULES` 硬编码在 `config.py` 中，YAML 文件缺失时自动降级，确保核心机制不依赖配置文件
- Mock LLM 设计为 FIFO 队列，完全不读取对话上下文，确保测试的确定性

---

### 2026-08-07 — Phase 3 治理维度（主要贡献）

| 时间 | 事件 | Worktree | Commit |
|------|------|----------|--------|
| 上午 | T07: GuardEngine 骨架 + 规则匹配 | phase3-governance | `564c6bd` |
| 上午 | T08: 路径隔离（resolve + is_relative_to） | phase3-governance | `62a96f6` |
| 上午 | T09: Shell 双重校验（shlex + regex） | phase3-governance | `5bf73b6` |
| 上午 | T10: 护栏状态机集成（23 个参数化测试） | phase3-governance | `5f9d8b6` |

**Subagent 策略：** T07→T08→T09→T10 为严格串行依赖，由一个 subagent 在 phase3-governance 分支中完成。

**关键工艺：**
- `validate_path()` 使用 `Path.resolve()` 解析软链接，防止符号链接绕过
- `check_shell_command()` 使用 `shlex.split()` 词法解析 + 正则双重校验，防止 `sudo`、`env` 等前缀绕过
- 护栏规则：SAFE/WARN/BLOCK 三级判决，多规则匹配时取最高优先级

---

### 2026-08-07 — Phase 4-6 核心循环

| 时间 | 事件 | Worktree | Commit |
|------|------|----------|--------|
| 下午 | T11: 工具执行器（5 个工具 + mkdir 保障） | phase4-executor | `70a23d4` |
| 下午 | T12: 反馈引擎（7 种分类 + 熔断） | phase5-core | `fd263ea` |
| 下午 | T13: AgentLoop 主循环（依赖注入 + 7 步） | phase5-core | `b30308d` |
| 下午 | T14: 集成测试 | phase5-core | `b918c21` |
| 下午 | T15: CLI 入口 + DeepSeekClient | phase6-io | `38ae1d8` |
| 晚上 | T16-T18: demo.py + CI + README | phase6-io | `903447d` |

**Subagent 策略：** T11 独立 subagent → T12-T14 串行 subagent → T15-T18 串行 subagent。

**关键工艺：**
- AgentLoop 通过构造函数依赖注入所有外部依赖（llm, guard, executor, feedback, io），测试时替换为 mock/stub
- 反馈引擎：SUCCESS 重置计数器，3 次同类失败触发熔断（circuit_breaker）
- CLI 通过 `--mock` 开关切换 MockLLM/DeepSeekClient，零修改

---

### 2026-08-07 — 代码审查与修复

| 时间 | 事件 | Commit |
|------|------|--------|
| 晚上 | 代码审查 | requesting-code-review |
| 晚上 | 修复 Critical: 反馈上下文注入 LLM | `01550a8` |
| 晚上 | 修复 Critical: YAML 正则转义（`C:\\Windows\\` → `C:\Windows\`） | `01550a8` |
| 晚上 | 修复: Action 导入错误 + BLOCK 拒绝回灌 + LINT_ERROR 分类 | `a3d6e59` |

**2 个 Critical Bug：**
1. `src/harness_core.py`: `context_for_llm` 已计算但未注入 LLM messages，导致反馈闭环失效
2. `guard_rules.yaml`: `C:\\Windows\\` 反斜杠转义后变成 `C:\Windows\`，正则匹配失败

**3 个 Important Bug：**
- `src/models.py`: `Action` 导入路径错误
- BLOCK 拒绝回灌：执行被拒绝后未将反馈注入下一轮 LLM 上下文
- LINT_ERROR 分类：FeedbackEngine 未识别 lint 错误为特定类别

**留下的 5 个 Important 问题（不阻塞合并）：**
- ~~session_store 注入但未使用~~ → 已修复（`bc40762`：`load_session()`/`save_session()` 集成到 AgentLoop）
- ~~缺少 scope 过滤~~ → 已修复（`116ee97`：`check()` 和 `check_shell_command()` 新增 `scope` 参数，4 个新测试）
- ~~缺少 conventions 模型~~ → 已修复（`bc40762`：`Session.conventions` + `_build_system_prompt()` 注入）
- ~~重复迭代检测~~ → 已修复（`1aba491`/`4d123eb`/`7ce2f94`：重复成功 5 次强制结束）
- ~~STM 测试缺口~~ → 已修复（`116ee97`：7 个新测试覆盖 load/save/errors/conventions/search/corrupt/limit）

---

### 2026-08-09 — GUI 测试辅助

| 时间 | 事件 | Commit |
|------|------|--------|
| 上午 | GUI 设计文档（Tkinter，零新依赖） | `6df9b1c` |
| 上午 | GUI 实现（逐轮展示 + HITL 审批） | `e193b51` |

**说明：** GUI 为个人调试测试工具，非作业要求。

---

### 2026-08-12 — 真实 API 测试与系统提示词优化

| 时间 | 事件 | Commit |
|------|------|--------|
| 上午 | 英语提示词（DeepSeek 对英文 JSON 指令更稳定） | `9716974` |
| 上午 | CLI verbose 模式 | `57b49d8` |
| 上午 | 参数名兼容（file_path, file, filepath） | `91a984c` ~ `9e78601` |
| 上午 | 重复成功循环检测（5 次后强制结束） | `1aba491` ~ `7ce2f94` |
| 上午 | 会话持久化接入 AgentLoop | `bc40762` |
| 上午 | GUI API Key 输入框 | `a3f483e` |

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

### 2026-08-12/13 — 4 个高级治理任务

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

### 2026-08-13 — 5 个高级鲁棒性任务

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

### 2026-08-13 — 遗留问题修复

| 时间 | 事件 | Commit |
|------|------|--------|
| 下午 | 修复 scope 过滤：`check()` 和 `check_shell_command()` 新增 `scope` 参数，4 个新测试 | `beb2d6a` |
| 下午 | 修复 STM 测试缺口：7 个新测试覆盖 load/save/errors/conventions/search/corrupt/limit | `beb2d6a` |
| 下午 | 测试从 87 → 98 passed | `beb2d6a` |

**关键工艺：**
- `check(action, scope=None)` 可选参数保持向后兼容，不传 scope 时全量匹配
- STM 测试覆盖：非存在 session 返回 None、errors 字段保存、conventions dict 格式、task description 搜索、corrupt JSON 容错、5 结果上限、全字段完整性

---

### 2026-08-13 — 文档完善

| 时间 | 事件 | Commit |
|------|------|--------|
| 下午 | 补充 AGENT_LOG 缺失的早期内容（2026-08-04 项目初始化、2026-08-06 需求分析），修正日期错误 | `116ee97` |
| 下午 | PLAN.md 更新测试数 87→98，补充 scope/STM 修复记录 | `360246b` |
| 下午 | SPEC_PROCESS.md 新增第 7 章：冷启动 Agent 行为分析（3 次暂停提问、5 个 Task 产出评估、Spec 写错 vs Agent 读错分析、修订前后关键 Diff、off-by-one 自修复记录） | `360246b` |

**SPEC_PROCESS.md 补充内容：**
- 7.1：冷启动 Agent 对话摘要 — Agent 依次完成 T01-T05，在 T02 命名不一致处暂停提问，在 T03 自修复 off-by-one bug
- 7.2：缺陷分析 — 明确标注缺陷 1/2 是"spec 写错"（类型声明不一致、缺少 git init），缺陷 3 是"agent 读错"（未按顺序执行 pip install）
- 7.3：修订前后 Diff — 两条实际 diff：`verdict: str` → `verdict: Verdict`、PLAN T01 新增 Step 0 `git init`
- 7.4：Agent 的 off-by-one 自修复 — `call_count` 先递增后减一导致跳过动作，Agent 自行发现并通过 2 次迭代修复

---

### 2026-08-13 — 最终交付

| 时间 | 事件 | Commit |
|------|------|--------|
| 下午 | 更新 PLAN.md 补充所有 18 个 task 的 commit hash | `ed2a925` |
| 下午 | 创建 AGENT_LOG.md（完整开发日志） | `ed2a925` |
| 下午 | 6 个 PR 描述补充 Subagent 标注 + 人工修改说明 | API PATCH |
| 下午 | 推送 master 至 GitHub | `ed2a925` |

---

## 最终交付

| 指标 | 数值 |
|------|------|
| 测试 | 98 passed, 2 skipped（零网络依赖） |
| 文件 | 25 个核心源文件 |
| Commits | 47 个（含 6 个 merge commit） |
| Worktree 分支 | 6 个（phase1-infra ~ phase6-io） |
| PR | 6 个（全部 open，含 Subagent 标注） |
| 测试覆盖 | 治理 33 个，反馈 9 个，执行器 9 个，场景 8 个，JSON 解析 6 个，核心 5 个，等 |

**Superpowers 反思：**
- TDD 在 AI 协作下是放大器而非阻碍：先写测试让 subagent 有明确的目标，减少了"偏离主题"的几率
- subagent-driven 工作流的关键在于 task 颗粒度：太大的 task 导致 subagent 偏离，太小的 task 产生过多分支
- SPEC/PLAN 质量直接影响实现质量：冷启动验证暴露的 3 个缺陷验证了"规约不清导致 subagent 偏离"的假设
- 凭据与分发要求迫使想清楚了一台全新机器从零运行的完整流程
- brainstorming 的 3 轮追问迫使在每个设计决策上有明确立场，SPEC_PROCESS.md 记录的 5 条 AI 建议被推翻修正体现了"工程师的价值不在写出代码，而在判断代码是否正确"