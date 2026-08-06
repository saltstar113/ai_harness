# Coding Agent Harness

纯 CLI 的 Coding Agent Harness。重点维度：治理（多维度规则引擎 + HITL 状态机）。

## 安装

### Linux / macOS
```bash
bash install.sh
```

### Windows
```powershell
.\install.ps1
```

## 配置 API Key

```bash
python run_cli.py credential set
```

## 运行

```bash
python run_cli.py --task "修复 test_auth.py 中的测试失败"
python run_cli.py --mock --task "演示模式"
python run_cli.py --strict --task "严格模式"
```

## 测试

```bash
pytest
```

## 机制演示

```bash
python demo.py
```

## 目录结构

```
ai_harness/
├── src/                    # 核心源码
│   ├── models.py           # 数据模型
│   ├── guardrail.py        # 治理引擎
│   ├── executor.py         # 工具执行器
│   ├── feedback.py         # 反馈引擎
│   ├── harness_core.py     # Agent 主循环
│   ├── mock_llm.py         # Mock LLM
│   ├── session_store.py    # 会话存储
│   ├── config.py           # 配置加载
│   ├── credential.py       # 凭据管理
│   └── io_interface.py     # IO 接口
├── tests/                  # 测试
├── run_cli.py              # CLI 入口
├── demo.py                 # 机制演示
└── guard_rules.yaml        # 治理规则
```

## 安全

- API Key 存储在 `.env` 文件中（明文风险见下文）
- `.env` 在 `.gitignore` 中，永不提交
- `credential status` 仅显示"已配置/未配置"，不回显明文
- 所有核心机制在移除 LLM 后仍可通过 `pytest` 验证

### `.env` 明文风险

`.env` 文件为明文存储。任何对文件系统有读权限的进程均可读取。
建议设置文件权限：`chmod 600 .env`

## 已知限制

- 需要 Python 3.11+
- 不在沙箱/容器内运行 agent 时，工具执行器直接操作宿主机文件系统
- 仅支持 DeepSeek LLM API