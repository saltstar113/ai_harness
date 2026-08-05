
> 本文档供 OpenCode Agent 在执行 AI4SE 期末项目 A（Coding Agent Harness）时使用。包含项目约束、文档模板、作业要求映射和参考信息。


## 一、项目元信息

- **项目类型**：Coding Agent Harness（作业 A）
- **技术栈**：Python（用户指定）
- **交付形态**：纯 CLI 工具 + GitHub Release 源码压缩包
- **核心等式**：Agent = LLM + Harness
- **开发工具**：OpenCode + Superpowers 框架


## 二、Agent 的角色与行为约束

**你的角色**：本项目的开发助手。你在辅助用户完成一个 Harness 的实现。

**关键行为规则**：

1. **禁止跳过 Spec 直接写代码** — 必须先完成 `SPEC.md`，用户确认后才能进入编码阶段（对应 Superpowers brainstorming Skill）
2. **禁止跳过测试直接写实现** — 所有核心机制必须有 mock-LLM 驱动的确定性单元测试（对应 TDD Skill）
3. **禁止建议使用现成 Agent 框架** — 不能建议用 LangChain、LangGraph、AutoGen、CrewAI、LlamaIndex 等高层框架。用户必须自己实现主循环
4. **机制必须是代码，不能是提示词** — 护栏、反馈闭环等必须落实为用户编写的确定性代码，不能只是系统提示里的一句话
5. **永远不要读取 `.env` 文件的内容** — 里面存有 API Key，绝对不可见


## 三、项目文件结构

项目根目录下需要按以下结构组织：

```
ai_harness/
├── .gitignore                    # 必须包含 .env
├── opencode.json                 # DeepSeek 接入 + 权限配置
├── AGENTS.md                     # 项目地图（用户需创建）
├── SPEC.md                       # 设计文档（第1-2天产出）
├── CHECKLIST.md                  # 验收清单
├── PLAN.md                       # 实现计划（第2天产出）
├── SPEC_PROCESS.md               # 过程文档（第2天产出）
├── AGENT_LOG.md                  # 日志（第10天）
├── REFLECTION.md                 # 反思报告（第11天）
├── README.md                     # 项目说明（第9天）
├── gate-checklist.md             # 阶段门禁
├── harness_core.py               # 主循环（第3天）
├── mock_llm.py                   # Mock LLM 抽象层（第3天）
├── guardrail.py                  # 护栏（第5天）
├── executor.py                   # 工具执行（第4天）
├── run_cli.py                    # CLI 入口（第7天）
├── demo.py                       # 机制演示（第7天）
├── test_core.py                  # 核心单测（第3天）
├── test_guardrail.py             # 护栏单测（第5天）
├── .github/
│   └── workflows/
│       └── ci.yml                # 必须包含 unit-test job（第8天）
├── docs/
│   └── KEY_REFERENCE.md          # 本文件
└── hom_require/                  # 作业要求文档
```


## 四、文档模板（供生成时套用）

### 4.1 SPEC.md 必须包含的章节（通用要求 §4.2 + A.5）

生成 SPEC.md 时必须包含以下 11 个部分：

1. **问题陈述**：要解决什么问题？目标用户是谁？为什么值得做？
2. **用户故事**：至少 5 个，遵循 INVEST 原则
3. **功能规约**：按模块拆分，每项描述输入/行为/输出/边界条件/错误处理
4. **非功能性需求**：性能、安全（含凭据威胁模型）、可用性、可观测性
5. **系统架构**：组件图、数据流、外部依赖（含 LLM 供应商、外部工具）
6. **数据模型**：主要实体、字段、关系、约束
7. **凭据与分发设计**：key 的存储方案与录入/更新/清除流程；分发形态（源码压缩包 + GitHub Release）与目标平台、key 在目标机的安全配置方式
8. **技术选型与理由**：Python、LLM 供应商（DeepSeek）、分发方式
9. **验收标准**：每个功能"完成"的客观判定标准
10. **风险与未决问题**：预见到的可能让 Agent 出问题的环节
11. **领域与机制设计**（A 类项目额外要求）：该领域（coding）的反馈信号、危险动作、所需工具、记忆需求分别是什么？让哪个维度成为重点，为什么？这些机制将如何编码实现（呼应 §A.4）

### 4.2 CHECKLIST.md 四维度验收

| 维度 | 检查内容 |
| :--- | :--- |
| **功能** | 主循环能跑、护栏能拦截、反馈能回灌、CLI 能启动 |
| **工程** | 模块职责清晰、代码可维护、有单测 |
| **安全** | 无 API Key 硬编码、无危险命令自动执行 |
| **退出** | 全部必选项通过；否则记录降级或人工接管 |

### 4.3 AGENTS.md 必须包含的内容

```markdown
# AGENTS.md

## 项目目标
构建一个 Coding Agent Harness，纯 CLI 工具，Python 实现。

## 技术栈
- Python 3.11+
- pytest（测试框架）
- 依赖：openai SDK 或 httpx（仅用于调用 LLM API，不用于 Agent 编排）

## 常用命令
- `pytest` — 运行所有单测
- `python run_cli.py` — 启动 CLI

## 优先阅读
- SPEC.md
- CHECKLIST.md
- AGENT_LOG.md
- docs/KEY_REFERENCE.md

## 禁止事项
- 不读取 .env
- 不引入 LangChain/LangGraph/AutoGen/CrewAI 等 Agent 框架
- 不硬编码 API Key
- 不在提示词里实现护栏/反馈（必须用代码）
```

### 4.4 gate-checklist.md 模板

```markdown
# gate-checklist.md

## 当前阶段：[阶段名]

## 必须通过
- [ ] [检查项1]
- [ ] [检查项2]
- [ ] [检查项3]

## 退出决定
- [ ] 通过，进入下一阶段
- [ ] 未通过，回到修复
- [ ] 范围过大，降级
```

### 4.5 AGENT_LOG.md 每条记录格式

每条记录包含：
- 时间戳与 task 编号
- 触发的 Superpowers 技能
- 关键 prompt / context 配置
- subagent 输出的关键片段或 commit hash
- 人工干预（修改了什么、为什么）
- 学到的教训


## 五、OpenCode 配置参考

### 5.1 opencode.json（DeepSeek 接入）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "deepseek/deepseek-v4-pro",
  "provider": {
    "deepseek": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "DeepSeek",
      "options": {
        "baseURL": "https://api.deepseek.com",
        "apiKey": "env:DEEPSEEK_API_KEY"
      },
      "models": {
        "deepseek-v4-pro": {
          "name": "DeepSeek V4 Pro"
        }
      }
    }
  }
}
```

### 5.2 权限配置（opencode.json 中的 permission 部分）

```json
{
  "permission": {
    "*": "ask",
    "read": {
      "*": "allow",
      ".env": "deny",
      ".env.*": "deny",
      ".env.example": "allow"
    },
    "edit": {
      "*": "ask"
    },
    "bash": {
      "*": "ask",
      "pwd": "allow",
      "ls": "allow",
      "git status": "allow",
      "pytest": "allow",
      "python run_cli.py": "allow"
    }
  }
}
```

### 5.3 OpenCode 常用命令

| 命令 | 用途 |
| :--- | :--- |
| `/connect` | 接模型 |
| `/models` | 选模型 |
| `/init` | 生成 AGENTS.md |
| `@file` | 引用上下文文件 |


## 六、作业 A 四个必须设计的机制（A.3）

在 SPEC 中必须明确这四个机制，并在代码中实现：

| 机制 | 说明 | 代码文件 |
| :--- | :--- | :--- |
| **动作/工具** | agent 能执行读写文件、执行 shell、运行测试 | `executor.py` |
| **客观反馈信号** | 运行测试/lint/类型检查，客观判定结果并回灌 | `harness_core.py` 中的反馈逻辑 |
| **危险动作** | 识别危险命令（rm -rf、shutdown 等），拦截并交人工确认 | `guardrail.py` |
| **记忆** | 跨会话记住项目约定、历史决策，按需提供给 LLM | `harness_core.py` 中的 state/Scratchpad |


## 七、关键判断标准（A.4-C）

**移除真实 LLM 后，机制还能用单测验证吗？**

- ✅ **算你实现的机制**：替换为 mock/stub LLM 后，仍能用确定性单元测试验证它工作
- ❌ **不算你实现的机制**：一旦离开真实 LLM 就无法测试（本质上是一句提示词）

**示例对比**：

| 方式 | 代码 | 能否单测 |
| :--- | :--- | :--- |
| ❌ 提示词版 | 在系统提示中写"不可以执行 rm -rf" | 不能，取决于 LLM 是否遵从 |
| ✅ 代码版 | `def guardrail(action): if "rm -rf" in action: return "blocked"` | 能，直接传入构造动作断言 |


## 八、测试要求（A.6）

1. **所有核心机制必须有 mock-LLM 驱动的确定性单元测试** — 不依赖网络与真实 LLM
2. **机制演示**：在 mock LLM 下确定性地复现：
   - ① 治理护栏拦截一个危险动作
   - ② 注入一次失败，反馈闭环使 agent 收到反馈并据此改变下一步动作
   - ③ 你重点维度的一个确定性行为
3. **一键运行**：`pytest` 或 `make test` 必须能跑通全部单测
4. **CI 配置**：`.github/workflows/ci.yml` 必须包含名为 `unit-test` 的 job


## 九、关键技术选型限制（A.4-A）

| 允许 | 禁止 |
| :--- | :--- |
| LLM 供应商的单次对话补全 API | LangChain `AgentExecutor` |
| HTTP 库（httpx/requests） | AutoGen |
| 向量库（如需记忆检索） | CrewAI |
| 解析库 | LlamaIndex agent |
| — | 任何编码智能体 SDK 自带的 agent runner |

**原则**：把底层零件组装成"循环 + 治理 + 反馈"，必须由用户自己的代码完成。


## 十、凭据安全要求（通用要求 3.1）

- key **绝不硬编码**进源码
- **绝不提交**进 Git（含历史）
- **绝不写入**日志 / 终端 history / 明文配置文件
- 使用 `.env` 文件加载（须说明明文风险）
- 首次运行应能**引导用户安全录入** key（如隐藏输入）
- 能查看/更新/清除（查看状态时不得回显明文）


## 十一、分发要求（通用要求 3.2 + 用户选择）

- **形态**：源码压缩包 + GitHub Release（方案一）
- README 必须写清：
  - 获取方式
  - 运行命令
  - key 如何在目标机器上安全配置
  - 已知限制（平台/架构/依赖前提）


## 十二、阶段提示模板（来自夏令营课件 Page 43）

当用户要求进入某个开发阶段时，按此模板组织 prompt：

```
你是本项目的前端实现助手（此处改为"后端/CLI 实现助手"）。

请阅读 @SPEC.md @CHECKLIST.md @AGENTS.md @context-pack.md。

当前阶段：[阶段名]

阶段 Spec：
- [只做什么]

阶段 Checklist：
- [如何判断通过]

约束：
- 不重写全文件
- 不引入外部依赖
- 不读取 .env

请先给计划：步骤、涉及文件、风险、检查方式。等我确认后再修改文件。
```


## 十三、Superpowers 框架关键信息

### 13.1 方法论定位

Superpowers 是 Spec-Driven Development 的产品化实现。完整生命周期：SDD + TDD + Code Review。

**对 Agent 的假设**：
> "Agent 是一个热情但无品味、无判断力、无项目上下文、厌恶测试的初级工程师。Harness 的存在就是为了约束这样的 Agent。"

### 13.2 核心技能

| 技能 | 触发时机 | 作用 |
| :--- | :--- | :--- |
| `brainstorming` | 用户提出新项目想法时 | 拦截"跳过 Spec 直接写代码"，强制先完成设计 |
| `writing-plans` | Spec 完成后 | 将设计拆解为细粒度 task 列表 |
| `test-driven-development` | 开始编码时 | 强制先写测试（红）→ 再写实现（绿）→ 再重构 |
| `subagent-driven-development` | 执行 PLAN 中的 task 时 | 为每个 task 派发独立 subagent |
| `using-git-worktrees` | 开始新功能时 | 为每个功能创建隔离的 worktree |

### 13.3 四项局限（需知悉）

1. 重型流程不适合探索性任务（目标模糊时会卡在 brainstorming 无限循环）
2. 依赖测试基础设施的成熟度（没有测试框架 TDD Skill 跑不起来）
3. 对模型能力有最低要求（弱模型上易问出无关问题或给出虚假"通过"判断）
4. 重型 Harness 的认知开销（工程师也需按 SDD 思维工作）


## 十四、关键概念速查

| 概念 | 定义 |
| :--- | :--- |
| **前馈（Guides）** | Agent 行动前塑造其行为，让它少犯错（AGENTS.md、权限配置、架构约束） |
| **反馈（Sensors）** | Agent 行动后纠偏（测试结果、lint 报错、CI 反馈） |
| **HITL（Human in the Loop）** | 不可逆动作必须由人确认（合并主分支、删除数据、发送邮件） |
| **Context Rot（上下文腐化）** | 多轮对话中早期约束被遗忘、注意力被稀释；对策：关键约束置尾、定期摘要、中间结果剔除 |


## 十五、参考来源说明

本文档提取自以下课程材料：
- 《AI for Coding 6 小时夏令营 HTML 课件》—— AgentOS 视角下的项目级 AI4Coding
- 《演示文稿1》—— 从 Prompt Engineering 到 Context Engineering 到 Harness Engineering

所有模板和约束均与用户作业要求（通用要求 + A 类项目要求）对齐。


**Agent 使用说明**：当用户要求你生成 SPEC.md、CHECKLIST.md、AGENTS.md 或任何阶段的代码时，请参考本文档中对应的模板和约束。如果用户的要求与本文档中的约束冲突，请提醒用户并引用作业要求。