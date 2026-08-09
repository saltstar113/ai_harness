# GUI 设计文档 — Coding Agent Harness

> **日期**：2026-08-09
> **类型**：功能增强
> **依赖**：Python 3.11+ · Tkinter（内置）
> **作者**：颜鑫

---

## 1. 目标

为 Coding Agent Harness 提供一个简陋但功能完整的桌面 GUI，用于测试和演示核心机制（护栏拦截、反馈修正、熔断），无需依赖命令行。

## 2. 用户故事

- 作为学生，我希望在图形界面中运行 Agent 任务，逐轮观察每个动作的护栏判决、执行结果和反馈
- 作为演示者，我希望直观展示 BLOCK 拦截、WARN 提示、HITL 审批等治理机制

## 3. 非功能约束

- **零新依赖**：仅使用 Python 标准库 `tkinter`
- **不修改核心代码**：复用现有 `AgentLoop`、`GuardEngine`、`Executor`、`FeedbackEngine`
- **单文件**：`gui.py`，约 200 行
- **线程安全**：AgentLoop 在后台线程运行，UI 通过 `root.after()` 更新

## 4. 界面布局

```
┌──────────────────────────────────────────────────┐
│  Coding Agent Harness GUI                        │
├──────────────────────────────────────────────────┤
│  任务描述: [________________________] [▶ 运行]   │
│  模式: ○ Mock LLM  ○ 真实 API                   │
│  Max Turns: [50]    严格模式: ☐                 │
├──────────────────────────────────────────────────┤
│  ┌─ 第 N 轮 ───────────────────────────────────┐ │
│  │ 动作: tool_name(params)                     │ │
│  │ 护栏: SAFE / WARN / BLOCK — reason          │ │
│  │ 审批: [通过] [拒绝]  (仅 BLOCK 时显示)     │ │
│  │ 结果: success / error — output              │ │
│  │ 反馈: SUCCESS / RETRY / CIRCUIT_BREAKER     │ │
│  └──────────────────────────────────────────────┘ │
│  ... 可滚动 ...                                   │
├──────────────────────────────────────────────────┤
│  状态: success/circuit_breaker  |  轮数: 3       │
└──────────────────────────────────────────────────┘
```

### 4.1 颜色方案

| 元素 | 颜色 | 含义 |
|------|------|------|
| SAFE 标签 | 绿色 `#4CAF50` | 护栏通过 |
| WARN 标签 | 橙色 `#FF9800` | 警告但继续 |
| BLOCK 标签 | 红色 `#F44336` | 拦截，需审批 |
| 成功结果 | 绿色文字 | 执行成功 |
| 失败结果 | 红色文字 | 执行失败 |

## 5. 架构

```
gui.py
├── HarnessGUI (tk.Tk)
│   ├── _build_control_panel()    → 顶部控制区
│   ├── _build_turn_display()     → 中间滚动回合区
│   ├── _build_status_bar()       → 底部状态栏
│   ├── _run_agent()              → 启动后台线程
│   ├── _add_turn_frame()         → 添加一轮 UI
│   └── _on_approval()            → 审批回调
│
│   复用现有模块（无修改）：
├── src.models        → Action, Session, Task, Turn, Verdict
├── src.guardrail     → GuardEngine
├── src.executor      → Executor
├── src.feedback      → FeedbackEngine
├── src.harness_core  → AgentLoop
├── src.mock_llm      → ScriptedMockLLM
└── src.config        → load_rules()
```

### 5.1 关键设计决策

**IO 接口适配**：`AgentLoop` 依赖 `io_interface` 进行审批交互。GUI 模式下，需要自定义 `GuiIO` 实现 `IOInterface` protocol，通过 `threading.Event` 阻塞等待用户点击审批按钮。

```
GuiIO 工作流：
1. AgentLoop 调用 io.request_approval(action, risk)
2. GuiIO 创建 Event 并放入队列
3. root.after() 在主线程渲染审批按钮
4. 用户点击 [通过] 或 [拒绝]
5. 回调设置 Event，GuiIO 返回 ApprovalResult
6. AgentLoop 继续执行
```

**MockLLM 动作序列**：GUI 模式下默认使用 MockLLM，提供预定义动作序列以展示各种治理场景。

## 6. 数据流

```
用户输入任务 → 点击"运行"
  → 后台线程: AgentLoop.run(task, session)
    → 每轮: LLM.chat() → Guard.check() → [HITL] → Executor.dispatch() → Feedback.analyze()
    → 每轮结束: 通过 queue 发送 Turn 数据到主线程
  → 主线程: root.after(100ms) 轮询 queue
    → 渲染 TurnFrame
    → 遇到 BLOCK: 显示审批按钮，等待用户操作
  → 最终: 更新状态栏
```

## 7. 测试

- GUI 不增加单元测试（Tkinter 难以自动化测试）
- 手动验证：`python gui.py` 启动后运行 Mock 任务，逐轮观察输出
- 手动验证场景：
  1. 护栏拦截（`rm -rf /`）→ 显示 BLOCK + 审批按钮
  2. 正常执行（`read_file`）→ 显示 SAFE + 成功结果
  3. 熔断触发（连续失败）→ 显示 circuit_breaker 状态

## 8. 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `gui.py` | 新增 | 约 200 行，GUI 入口 |
| `src/io_interface.py` | 不修改 | 复用 IOInterface protocol |
| `src/harness_core.py` | 不修改 | 复用 AgentLoop |
| 其他 | 不修改 | — |

## 9. 风险

| 风险 | 缓解 |
|------|------|
| Tkinter 线程安全 | 所有 UI 更新通过 `root.after()` 回到主线程 |
| HITL 阻塞后台线程 | 使用 `threading.Event` + 队列，不阻塞主线程 |
| 真实 API 调用耗时 | 实时显示当前轮次，不卡 UI |