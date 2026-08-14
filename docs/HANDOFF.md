# 项目上下文（新对话快速对齐）

## 项目定位
AI4SE 期末项目 A：**Coding Agent Harness**。核心等式：Agent = LLM + Harness。从零构建一个纯 CLI 的 coding agent，**重点维度是治理（多维度规则引擎 + HITL 状态机）**。

## 关键约束（必须遵守）
- **Python 3.11+**，禁止 LangChain / AutoGen / CrewAI / LlamaIndex
- **核心机制仅用标准库**（pathlib, shlex, json, re, subprocess, getpass, dataclasses），外部依赖仅 httpx / pytest / python-dotenv / pyyaml
- **核心/IO 分离**：Core 层通过依赖注入组装，不直接 print/input
- **所有测试在 mock LLM 模式下运行**，零网络依赖
- **凭据**：`.env` + `getpass`，绝不硬编码、不提交 Git、不写入日志
- **每个改动必须 TDD**：先写失败测试 → 最小实现

## 当前状态
- **测试**：98 passed, 2 skipped（零网络依赖）
- **Commit**：49 个（含 6 merge），HEAD 领先 origin/master 3 个 commit（网络问题暂未推送）
- **6 个 worktree 分支**（phase1-infra ~ phase6-io）已合并到 master，对应 6 个 GitHub PR 均为 open 状态
- 所有核心模块已实现完毕，代码审查发现的 2 Critical + 5 Important 问题全部修复

## 核心文件结构
```
src/
  models.py         — 12 个 dataclass + 4 个 enum（Action, Session, Turn, GuardRule 等）
  harness_core.py   — AgentLoop 主循环（DI 注入，7 步流程，反馈回灌，invalid_json 熔断）
  guardrail.py      — GuardEngine（SAFE/WARN/BLOCK 状态机，路径隔离，Shell shlex+regex 双重校验，$IFS 注入防护，scope 过滤）
  executor.py       — 5 个工具（read_file/write_file/execute_shell/run_tests/run_lint），环境变量白名单，原子写入回滚
  feedback.py       — FeedbackEngine（8 种分类，3 次熔断，输出截断 3000 chars，重复成功检测）
  mock_llm.py       — ScriptedMockLLM + ScenarioMockLLM（6 场景）
  session_store.py  — JSON 会话存储（save/load/search）
  config.py         — YAML 配置加载 + BUILTIN_RULES 降级
  credential.py     — .env + getpass 凭据管理
  io_interface.py   — IOInterface Protocol + SilentIO + CliIO + GuiIO
run_cli.py          — CLI 入口，DeepSeekClient + JSON 容错解析
demo.py             — 三项机制演示（护栏拦截、反馈修正、熔断）
guard_rules.yaml    — 治理规则配置文件（可选）
tests/              — 10 个测试文件，98 个测试用例
```

## 关键设计文档
| 文件 | 作用 |
|------|------|
| `docs/SPEC.md`（1169 行） | 11 章完整设计，含问题陈述、5 个 INVEST 用户故事、功能/非功能规约、架构、数据模型、凭据与分发、领域与机制设计 |
| `docs/PLAN.md`（2520 行） | 18 个 task 的 TDD 实现计划，全部 checkbox 已标记完成，含 commit hash 记录 |
| `docs/SPEC_PROCESS.md`（330+ 行） | 与 Superpowers 协作的 3+3 轮迭代记录、冷启动验证、修订 diff、反思 |
| `docs/AGENT_LOG.md`（640+ 行） | 按时间线记录的完整开发日志 |

## 已完成的工作（无需重做）
1. 全部 18 个 PLAN task（T01-T18）已实现
2. 代码审查 2 Critical + 5 Important 全部修复
3. 4 个高级治理任务（symlink, shell obfuscation, rejection self-correct, timeout）
4. 5 个高级鲁棒性任务（env scrubbing, stagnation, truncation, JSON recovery, atomic rollback）
5. 6 个 PR 描述已补充 Subagent 标注 + 人工修改说明
6. SPEC_PROCESS.md 冷启动分析补充完毕

## 待完成（需你处理）
- **网络恢复后推送**：`git push origin master`（3 个 commit 待推送）
- **6 个 PR 需在 GitHub 上手动 merge**（phase1→phase2→phase3→phase4→phase5→phase6 顺序）
- **可选**：任何老师提出的新要求

## 工作方式
- 先读 docs/SPEC.md 和 docs/PLAN.md 了解全局设计
- 修改代码前先读对应的测试文件，遵循现有 TDD 模式
- 改动后运行 `pytest tests/` 验证不破坏现有功能
- 不要引入新依赖（除非有充分理由）
- 不要重写已有模块——仅做增量修改