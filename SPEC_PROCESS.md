# SPEC_PROCESS.md — 规约与计划生成过程文档

> 记录与 Superpowers（OpenCode + brainstorming + writing-plans）协作生成 SPEC.md 和 PLAN.md 的全过程。

---

## 一、Brainstorming 阶段

### 1.1 第一轮：大纲输出 + 架构质询

**时间**：2026-08-06

智能体首先完整阅读了三份作业要求文件（通用要求、A 类项目要求、PROJECT_AGENT_REFERENCE），然后输出了 11 章大纲结构，完全对齐作业要求的 SPEC 章节。

**智能体提出的三个高价值问题：**

| 问题 | 我的选择 | 理由 |
|------|----------|------|
| Q1：反馈闭环粒度（A 简单回灌 / B 结构化分类 / C 多轮修正状态机） | **C** | 结构化分类 + 熔断是确定性代码，而非提示词，符合作业 A.4-C 判据 |
| Q2：记忆方案（A Flat Scratchpad / B 结构化 Session Store / C 向量化 RAG） | **B** | 结构化 JSON 可在 mock LLM 下 100% 可测试；拒绝向量库避免过度工程 |
| Q3：治理分类体系（A 二元 / B 三级 / C 多维度分级） | **C** | 治理是 Main Contribution，多维度规则引擎 + YAML 配置驱动最能体现工程深度 |

**我的修正**：这三个问题让我明确了反馈闭环的"熔断"机制——此前我只模糊地想过"失败后重试"，但未意识到需要区分"第 1 次全量上下文 → 第 2 次精简 → 第 3 次熔断"的递进策略。同样，治理维度的"操作类型 × 风险等级 × 作用域"三维矩阵也是在 Q3 的引导下成型的。

---

### 1.2 第二轮：核心三章草稿 + 再次质询

**智能体展示了第三章（功能规约）、第五章（系统架构）、第十一章（领域与机制设计）的草稿**，并提出了三个质询点：

**我的修正与补充：**

1. **Shell 命令匹配逻辑 Bug**：智能体初版用 `tokens[0] + re.fullmatch` 匹配，我指出这无法匹配 `rm -rf /` 这类带参数的模式，且会被 `sudo` 前缀绕过。修正为 `re.search(command) or re.fullmatch(pattern, cmd_name)` 双重校验。

2. **文件写入建图保障**：我要求在 `write_file` 规约中补充 `target.parent.mkdir(parents=True, exist_ok=True)`，确保写入深层路径时不会因缺少父目录失败。

3. **MockLLM 设计规范化**：我要求明确 `ScriptedMockLLM` 采用 `List[Action]` 动作队列注入，`chat()` 按 FIFO 返回，队列耗尽返回 FINISH 信号。

**质询点决策：**

| 质询 | 我的决策 |
|------|----------|
| A. WARN 是否跳过审批环节 | 默认自动执行 + 日志记录；提供 `--strict` 命令行开关升格为 HITL |
| B. 修正轮次计数单位 | 按"连续同类失败"计数；成功即重置；失败类型变化亦重置 |
| C. 是否引入 keyring | 放弃 keyring（回避 WSL/D-Bus 依赖），仅用 `.env` + `getpass` |

**反思**：第二轮是我与智能体交互最密集的阶段。智能体在初稿中已经给出了相当完整的设计，但三个细节问题（Shell 匹配、建图、MockLLM 设计）暴露了它在"微观实现正确性"上的不足——它能画出正确的架构图，但代码级别的逻辑漏洞需要我来发现和修正。这恰恰印证了作业的核心命题：**工程师的价值不在"写出代码"，而在"判断代码是否正确"**。

---

### 1.3 第三轮：签字确认 + 生成完整 SPEC.md

我对核心三章签字确认后，智能体生成了包含全部 11 章的完整 SPEC.md（1169 行）。

**Spec 自审发现的问题**（智能体自行发现并修复）：
- 实体关系图中 `Session 1 ──── * Turn` 与 `Session` dataclass 矛盾 → 修正为 `Session 1 ──── * Error`
- v1.0 范围决策中声称支持 REPL 模式，但 CLI 规约未定义 → 修正为"仅 `--task` 单次模式"

---

## 二、Writing-Plans 阶段

### 2.1 第一轮：Task 拆解框架 + 策略质询

智能体按模块分组输出了 18 个 task 的框架（7 个 Phase），并提出 4 个策略问题：

| 问题 | 我的选择 | 理由 |
|------|----------|------|
| Q1：Worktree 粒度（A 每 task 一个 / B 每 Phase 一个 / C 混合） | **C** | 治理和核心循环独立 worktree，其余 Phase 合并，平衡隔离性与管理开销 |
| Q2：治理 task 组织方式（A 自底向上 / B 自顶向下 / C TDD 驱动） | **A** | 每个子组件独立可测，T10 集成时已有扎实基础 |
| Q3：测试基础设施（A 独立前置 / B 各模块自带 / C 折中） | **A** | 共享 fixture 避免治理模块 4 个 task 的重复代码 |
| Q4：AC 优先级分组（A 编号顺序 / B 模块分组 / C 关键路径优先） | **C** | 最早在 Phase 5 就能看到端到端闭环 |

---

### 2.2 第二轮：完整 Task 列表细化 + 边界确认

智能体输出了 18 个 task 的完整拆解，每个 task 包含：目标、涉及文件、预期实现要点、验证步骤（含失败测试的具体代码）、commit 信息。

**第二轮质询确认：**
- A. Task 数量/粒度是否合适 → **合适**
- B. Worktree 分配是否合理 → **合理**
- C. 是否需要显式标注"重构"步骤 → **不需要**

---

### 2.3 第三轮：生成 PLAN.md + 质量审查

智能体生成了完整的 PLAN.md（2442 行），包含 18 个 task 的完整 TDD 步骤、依赖关系图、并行策略、AC 覆盖映射。

**质量审查发现的 3 个问题**（智能体自行发现并修复）：
1. `ApprovalResult` 在 `models.py` 和 `io_interface.py` 中重复定义 → 去重，统一从 `models.py` 导入
2. T14 测试从 `src.io_interface` 导入 `RiskInfo`（实际在 `src.models`） → 修正导入路径
3. `run_cli.py` 引用 `DeepSeekClient` 但无 task 实现 → 补充薄封装实现

---

## 三、AI 建议采纳/修正分析

### 3.1 我采纳的 AI 建议（及理由）

| 建议 | 来源 | 采纳理由 |
|------|------|----------|
| 多轮修正状态机（3 轮熔断） | brainstorming Q1 | 递进式失败策略是确定性代码，完全满足作业 A.4-C 判据 |
| 结构化 JSON Session Store | brainstorming Q2 | 纯 Python 逻辑，mock LLM 下 100% 可测试 |
| 多维度治理分级（SAFE/WARN/BLOCK） | brainstorming Q3 | 三维矩阵 + YAML 配置驱动，体现工程深度 |
| `pathlib.resolve().is_relative_to()` 路径隔离 | 第二轮草稿 | 物理路径解析，防符号链接绕过 |
| `shlex` 词法解析 + 正则双重校验 | 第二轮草稿 | 标准库方案，零依赖 |
| `request_approval()` 替代 `confirm()` | 第二轮草稿 | 支持用户拒绝时输入修改意见回灌 LLM |
| 依赖注入模式 | 第二轮草稿 | 测试时 `llm=MockLLM(), io=SilentIO()` 无缝替换 |
| `ScriptedMockLLM` 动作队列 | 第二轮草稿 | 支持离线确定性测试多轮修正状态机 |
| 混合 worktree 策略 | writing-plans Q1 | 治理和核心循环独立隔离，其余 Phase 合并 |
| 自底向上 TDD（治理模块） | writing-plans Q2 | 每个子组件独立可测，最后集成 |
| 独立 conftest.py | writing-plans Q3 | 共享 fixture 避免 4 个治理 task 重复代码 |
| 关键路径 AC 优先 | writing-plans Q4 | 最早 Phase 5 即可端到端闭环 |

### 3.2 我推翻或修正的 AI 建议（及理由）

| 建议 | 修正结果 | 理由 |
|------|----------|------|
| Shell 匹配用 `tokens[0] + re.fullmatch` | 改为 `re.search(command) or re.fullmatch(pattern, cmd_name)` | 原方案无法匹配 `rm -rf /` 带参数模式，且 `sudo` 可绕过 |
| WARN 跳过审批环节 | 改为默认自动执行 + `--strict` 开关升格 | 兼顾 DX 体验与安全合规 |
| 引入 keyring 做二层凭据存储 | 放弃，仅用 `.env` + `getpass` | WSL/无 GUI 环境 D-Bus 依赖风险 |
| 支持 REPL 交互模式 | 从 v1.0 范围移除 | 聚焦核心闭环验证，降低 CLI 复杂度 |
| 修正轮次按"同一动作"计数 | 改为按"连续同类失败"计数 | 失败类型变化说明修复引入了新问题，应重新计数 |

---

## 四、反思：Brainstorming 技能的得与失

### 4.1 做得好的地方

1. **强制"先设计后编码"的纪律**：brainstorming 技能的 HARD-GATE 机制阻止了任何"跳过 spec 直接写代码"的冲动。在我没有明确要求的情况下，它主动追问"反馈闭环粒度""记忆方案""治理分类体系"，迫使我做出有意识的设计决策，而非凭直觉"先写着看"。

2. **分块呈现 + 逐步签字**的工作流极高：不是一次性输出 11 章，而是先大纲 → 核心三章 → 完整文档。每一轮我都有机会在局部范围内深入质询，而非面对一整份文档无从下手。这让我在第二轮发现了 Shell 匹配的逻辑 Bug——如果是一口气生成全文，我大概率会漏掉。

3. **问题质量高**：两个阶段共提出 7 个架构决策问题（brainstorming 3 个 + writing-plans 4 个），每一个都触及了设计中的模糊地带。特别是"反馈闭环的熔断机制"和"治理的 WARN 是否跳过审批"，在智能体提问之前我并未意识到这些是需要决策的点。

4. **SPEC 自审（Spec Self-Review）机制有效**：智能体在生成 SPEC.md 后自行发现了实体关系图不一致和 REPL 模式矛盾两个问题，并主动修复。这种"自己检查自己"的纪律在单人项目中尤为珍贵。

### 4.2 让我不满的地方

1. **代码级正确性不足**：智能体在架构层面表现优秀，但在代码细节上需要我纠正。典型的例子是 Shell 匹配逻辑——`tokens[0] + re.fullmatch` 在架构图层面看不出问题，但代码实现上存在 `sudo` 绕过漏洞。这导致我在"审阅代码"上花费了超出预期的时间。

2. **偶尔的"过度设计"倾向**：在没有明确要求的情况下，智能体建议了 keyring 和 REPL 交互模式。虽然它接受了我的否决，但这种"多做一点"的倾向在缺乏约束时可能引入不必要的复杂度。

3. **对"形式大于实质"的敏感度不够**：在 PLAN.md 初稿中，T14 Step 3 写的是"检查 AgentLoop.run() 中熔断判断的位置和逻辑"，但没有给出具体的代码修改。这本质上是一个"描述性步骤"而非"可执行步骤"。虽然最终不影响实现（因为 T13 已包含正确逻辑），但暴露了它有时会产出"看起来完整但实际空洞"的内容。

### 4.3 对 Superpowers 方法论的批判性见解

Superpowers 的核心假设是"Agent 是一个热情但无品味、无判断力、厌恶测试的初级工程师"。这个假设在我的项目中基本成立：

- **成立的部分**：智能体确实需要 SPEC 和 PLAN 的约束才能产出正确的代码。没有 brainstorming 的 3 轮追问，我自己的设计也是模糊的。没有 PLAN 的详细 task 拆解，TDD 纪律很容易在"先写着看"的心态中丢失。

- **不成立的部分**：智能体不是"厌恶测试"的——它很乐意写测试代码，甚至主动建议 `@pytest.mark.parametrize`。问题不在于意愿，而在于**测试的质量**：它写的测试覆盖了 happy path 但可能遗漏边界条件（如 Shell 匹配的 `sudo` 绕过），这需要我作为 reviewer 来补充。

- **最大的价值**：Superpowers 最大的价值不是"让 AI 写出更好的代码"，而是**强制人做出更好的决策**。brainstorming 的逐章签字机制迫使我在每个设计决策上有明确立场，writing-plans 的 task 拆解迫使我想清楚每个模块的接口边界。这些"人的工作"才是项目质量的真正决定因素。

---

## 五、关键迭代节选

### 迭代 1：反馈闭环粒度的确定（brainstorming 第一轮）

> **智能体**：反馈闭环应该做到什么程度？A）简单回灌 B）结构化分类 C）多轮修正状态机
>
> **我**：C。在结构化解析报错的基础上，引入重试计数与熔断升级策略，避免 Agent 无限死循环。
>
> **决策**：采纳 C，并进一步细化：第 1 次全量错误上下文 → 第 2 次精简范围提示 → 第 3 次熔断并暂停等待人工介入。

### 迭代 2：Shell 匹配逻辑的修正（brainstorming 第二轮）

> **智能体**：[展示 `cmd = tokens[0]` + `re.fullmatch` 的 Shell 匹配代码]
>
> **我**：当前示例中的 `cmd = tokens[0]` 结合 `re.fullmatch` 存在逻辑漏洞（如无法匹配 `rm -rf /` 这类带参数模式，且会被 `sudo` 前缀绕过）。请修改为 `re.search(command) or re.fullmatch(pattern, cmd_name)` 双重校验。
>
> **决策**：修正智能体的代码实现，采纳双重校验方案。

### 迭代 3：凭据方案的否决（brainstorming 第二轮）

> **智能体**：是否还需要利用 keyring 库做系统级钥匙串存储作为第二层安全？
>
> **我**：放弃 keyring（回避 WSL/无 GUI 环境下的 D-Bus 依赖风险），明确采用 .env 隔离 + getpass 隐式输入引导。
>
> **决策**：否决 keyring，仅用 .env + getpass。

### 迭代 4：治理 task 组织方式（writing-plans 第一轮）

> **智能体**：治理模块的 Task 组织方式？A）自底向上 B）自顶向下 C）TDD 驱动
>
> **我**：A。自底向上，每个子组件独立可测，T10 集成时已有扎实的组件基础。
>
> **决策**：采纳 A，T07（GuardRule 模型）→ T08（路径校验）→ T09（Shell 校验）→ T10（状态机集成）。

### 迭代 5：重复定义的发现（质量审查）

> **智能体**：[自行发现] `ApprovalResult` 在 `models.py` 和 `io_interface.py` 中重复定义。T14 测试从 `src.io_interface` 导入 `RiskInfo`（实际在 `src.models`）。
>
> **决策**：智能体自行修复，去重并修正导入路径。

---

## 六、冷启动验证（§4.5 自我验证）

### 6.1 验证方式

按照作业要求，使用一个与主开发智能体（OpenCode + DeepSeek V4 Pro）**不同**的 agent，在全新会话中仅凭 `SPEC.md` + `PLAN.md` 尝试实现 T01 和 T02。不向其提供任何 brainstorm 对话历史或补充解释。

**验证目标**：检验 SPEC 和 PLAN 在没有隐性上下文的情况下，能否被陌生 agent 独立理解并执行。

### 6.2 暴露的问题

陌生 agent 在 T01-T02 阶段共报告了以下阻断：

| # | 阻断描述 | 根因 | 严重性 |
|---|---------|------|--------|
| 1 | "T02 uses `Verdict` only. PLAN examples will need to follow SPEC naming." | SPEC 数据模型中 `GuardDecision.verdict` 声明为 `str`，但 SPEC 和 PLAN 的代码示例均使用 `Ver.BLOCK`（枚举）。陌生 agent 发现类型声明与代码示例不一致，无法确定该用哪个。 | 中 |
| 2 | "git check-ignore .env cannot run — folder is not a Git repository." | PLAN T01 的验证步骤依赖 `git check-ignore .env` 和 `git commit`，但未包含 `git init` 初始化步骤。对陌生 agent 而言，缺少 git 仓库是硬阻断。 | 高 |
| 3 | "pytest is not installed in the current Python environment." | 非文档缺陷。PLAN T01 Step 5 已包含 `pip install -r requirements.txt`，agent 在未执行安装步骤的情况下尝试运行了 `pytest --collect-only`。属于 agent 自身执行顺序问题。 | 低 |

### 6.3 修复措施

| 问题 | 修复 |
|------|------|
| `GuardDecision.verdict` 类型不一致 | SPEC 第 6 章：`verdict: str` → `verdict: Verdict`。SPEC 和 PLAN 现在统一使用枚举类型 |
| 缺少 `git init` | PLAN T01 新增 Step 0：`git init`，确保 `git check-ignore` 和后续 `git commit` 有仓库可操作 |
| pytest 未安装 | 无需修改文档。PLAN 中 `pip install` 步骤在 `pytest` 命令之前，顺序正确 |

### 6.4 反思：冷启动测试的价值

这次冷启动测试是 SPEC 和 PLAN 质量最有价值的反馈信号。三个问题中，前两个是**真正的文档缺陷**——它们在我的主开发 session 中不会暴露，因为我和主 agent 在 brainstorming 过程中积累了共享的隐性上下文（我知道 `Verdict` 就是枚举，我知道项目目录是 git 仓库）。但一个全新的 agent 没有这些上下文，它会在每一个未明文写下的假设处受阻。

**核心教训**：

1. **类型声明和代码示例必须一致**。SPEC 用 `str` 声明、PLAN 用 `Ver.BLOCK` 实现，这种不一致在主开发会话中不会引起注意（因为"大家都知道"是什么意思），但对陌生 agent 是歧义源。

2. **环境依赖必须显式声明**。`git init` 在主开发会话中是"显然已经做了"的事，但 PLAN 是给陌生 agent 的执行手册，必须从零开始描述每一步。

3. **冷启动测试是单人项目中最接近"同侪评审"的机制**。它暴露的不是"代码写错了"，而是"你没写下来的假设"。这正是作业要求的核心意图——"一个全新的 agent 会在你未明文写下的每个假设处受阻；而这些受阻之处，恰恰是 spec 质量最有价值的反馈信号"。

---

## 七、冷启动验证补充：Agent 行为与修订 Diff

### 7.1 冷启动 Agent 对话摘要

冷启动 Agent 收到指令："根据 SPEC+PLAN 从 PLAN 选 1–2 个 task 自主推进，遇到不确定之处即暂停询问"，随后依次尝试了 T01→T02→T03→T04→T05。

**Agent 暂停提问的时刻：**

| 轮次 | 暂停位置 | Agent 的提问 |
|------|----------|-------------|
| 第 1 轮 | T02 数据模型实现 | "PLAN 里 T02 的示例测试把 `Verdict` 写成了 `Ver`，和 SPEC 的命名不一致。我先暂停，等你确认是统一用 `Verdict` 还是额外加 `Ver` 别名。" |
| 第 1 轮 | T01 验证步骤 | `git check-ignore .env` 报错：`fatal: not a git repository`。Agent 将此事记录为 blocker 但未提问——它自己判断这是环境问题，暂停等待用户决策。 |
| 第 1 轮 | T01 验证步骤 | `pytest --collect-only` 报错：`pytest` 未安装。Agent 同样记录为 blocker。 |

**Agent 的实际产出 vs 预期：**

| Task | Agent 产出 | 评估 |
|------|-----------|------|
| T01 | `.gitignore`, `requirements.txt`, `pytest.ini`, `conftest.py` | 完全正确，与 SPEC/PLAN 一致 |
| T02 | `src/models.py`（含全部 12 个 dataclass），`test_models.py`（7 个测试） | 正确——Agent 按用户确认统一使用 `Verdict`，未加 `Ver` 别名 |
| T03 | `src/mock_llm.py`（`ScriptedMockLLM`），`test_mock_llm.py` | 功能正确，但存在一个 off-by-one bug：`call_count` 在读取动作前递增，导致第 3 次调用跳过了第 3 个动作。Agent 自行发现并修复了此 bug（2 次迭代）。 |
| T04 | `src/config.py`（`load_rules` + `BUILTIN_RULES`），`guard_rules.yaml`，`test_config.py` | 完全正确 |
| T05 | `src/credential.py`（set/status/clear），`test_credential.py`（4 个测试） | 完全正确 |

**产出与预期差距：** 极小。Agent 成功完成了 T01-T05，产出的代码在主仓库中可直接沿用（T02 模型层后来被主分支 subagent 重新实现，但结构一致）。唯一的功能性 bug（T03 off-by-one）被 Agent 自行发现并修复。差距不在代码质量，而在"隐性上下文"——Agent 遇到 3 处 SPEC/PLAN 未明文写下的假设后暂停，这些暂停恰好暴露了文档缺陷。

### 7.2 缺陷分析：Spec 写错 vs Agent 读错

| # | 缺陷 | 是 spec 写错还是 agent 读错？ | 分析 |
|---|------|---------------------------|------|
| 1 | `GuardDecision.verdict` 类型声明为 `str`，但 SPEC 和 PLAN 的代码示例均使用 `Ver.BLOCK`（枚举） | **Spec 写错** | SPEC 第 6 章类型声明 `verdict: str` 与第 11 章代码示例 `Ver.BLOCK` 矛盾。Agent 的正确做法是停下来询问而非猜测——它确实这么做了。如果 Agent 自作主张选了 `str`，后续所有 `guardrail.py` 的枚举比较逻辑都会失效。 |
| 2 | `git check-ignore .env` 失败：目录不是 Git 仓库 | **Spec 写错** | PLAN T01 的验证步骤假定工作区已是 Git 仓库。主开发会话中这个假设成立（仓库早已存在），但冷启动 Agent 从零开始，`git init` 是必须的步骤。Agent 将此事记录为 blocker 后等待用户决策，而非跳过验证。 |
| 3 | `pytest` 未安装 | **Agent 读错** | PLAN T01 Step 5 已明确写 `pip install -r requirements.txt`，但 Agent 在未执行安装步骤的情况下直接运行了 `pytest --collect-only`。这是 Agent 执行顺序的疏忽，非文档缺陷。 |

### 7.3 修订前后关键 Diff

**修订 1：SPEC 第 6 章 — `GuardDecision.verdict` 类型声明（commit `c70229c`）**

```diff
 @dataclass
 class GuardDecision:
     """治理判定结果"""
-    verdict: str                           # SAFE | WARN | BLOCK
+    verdict: Verdict                       # SAFE | WARN | BLOCK
     matched_rule: str = "default"
     reason: str = ""
```

**修订 2：PLAN T01 — 新增 Step 0 `git init`（commit `c70229c`）**

```diff
 - Consumes: (none — first task)
 - Produces: `tmp_workspace` fixture, `sample_action` fixture, `sample_session` fixture

+- [ ] **Step 0: 初始化 Git 仓库**
+
+```bash
+git init
+```
+
 - [ ] **Step 1: 创建 `.gitignore`**
```

**修订 3：无可修改 — 缺陷 3（pytest 未安装）**

PLAN 中 `pip install` 步骤在 `pytest` 命令之前，顺序正确，无需修改文档。根因是 Agent 未按顺序执行。

### 7.4 冷启动验证的额外发现：Agent 的 off-by-one 自修复

冷启动 Agent 在 T03 实现中暴露了一个值得记录的细微 bug：

```python
# Agent 初版（有 bug）
def chat(self, messages):
    self.call_count += 1            # 先递增
    if self.call_count > len(self.queue):
        return {"action": "finish"}
    return self.to_response(self.queue[self.call_count - 1])  # 后减一
```

```python
# Agent 修复版（正确）
def chat(self, messages):
    if self.call_count >= len(self.queue):
        return {"action": "finish"}
    action = self.queue[self.call_count]
    self.call_count += 1            # 后递增
    return self.to_response(action)
```

Agent 通过运行测试自行发现此 bug（"第三次调用应命中第 3 个动作，但实际命中了第 2 个"），并在 2 次迭代内修复。这说明即使是确定性代码（Mock LLM），SPEC 和 PLAN 也无法覆盖所有实现细节——Agent 的自我纠错能力（跑测试→发现失败→修 bug）是最终产出质量的关键保障。