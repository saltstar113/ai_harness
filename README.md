# Coding Agent Harness

纯 CLI 的 Coding Agent Harness。重点维度：治理（多维度规则引擎 + HITL 状态机）。

**核心等式**：Agent = LLM + Harness

所有核心机制（治理、反馈、工具分发、记忆）由确定性代码实现，移除 LLM 后仍可通过单元测试独立验证。

## 前置条件

| 项目 | 要求 |
|------|------|
| Python | 3.11+（依赖 `pathlib.is_relative_to` 和 `dataclasses` 标准库） |
| pip | 最新版本 |
| 操作系统 | Linux (x86_64), macOS (arm64 / x86_64), Windows (x86_64) |
| Shell | Linux/macOS: `/bin/sh`, Windows: PowerShell 5.1+ |
| 网络 | 仅首次安装依赖和 LLM API 调用时需要 |

## 安装

### Linux / macOS
```bash
bash install.sh
```

### Windows
```powershell
.\install.ps1
```

### 使用 Make
```bash
make install
```

## 配置 API Key

```bash
python run_cli.py credential set
```

## 运行

```bash
python run_cli.py --task "修复 test_auth.py 中的测试失败"
python run_cli.py --mock --task "演示模式"       # 离线模拟模式
python run_cli.py --strict --task "严格模式"      # WARN 升格为 HITL
python run_cli.py --help                         # 完整参数说明
```

## 测试

```bash
make test
# 或
pytest
```

## 机制演示

```bash
make demo
# 或
python demo.py
```

## 分发

本项目的分发形态为 **源码压缩包 + GitHub Release**。

### 构建源码压缩包

```bash
make dist
# 输出：dist/ai_harness.zip
```

### 手动构建

```bash
git archive --format=zip --output=ai_harness.zip HEAD
```

### 安装压缩包

```bash
unzip ai_harness.zip -d ai_harness
cd ai_harness
pip install -r requirements.txt
python run_cli.py credential set
```

### CI 构建产物

每次 push 到 master 分支后，CI 自动通过 `make dist` 构建压缩包并上传为 GitHub Actions Artifact（`ai_harness.zip`），可在 Actions 页面下载。

## 目录结构

```
ai_harness/
├── src/                    # 核心源码
│   ├── models.py           # 数据模型（12 dataclass + 4 enum）
│   ├── guardrail.py        # 治理引擎（SAFE/WARN/BLOCK 状态机）
│   ├── executor.py         # 工具执行器（5 个工具调度）
│   ├── feedback.py         # 反馈引擎（8 种分类，3 次熔断）
│   ├── harness_core.py     # Agent 主循环（7 步流程，DI 注入）
│   ├── mock_llm.py         # Mock LLM（ScriptedMockLLM / ScenarioMockLLM）
│   ├── session_store.py    # 会话存储（JSON 持久化 + 关键词检索）
│   ├── config.py           # 配置加载（YAML + 内置降级）
│   ├── credential.py       # 凭据管理（.env + getpass）
│   └── io_interface.py     # IO 接口（Protocol + SilentIO + CliIO + GuiIO）
├── tests/                  # 10 个测试文件，98 个测试用例
├── run_cli.py              # CLI 入口
├── demo.py                 # 三项机制演示（护栏/反馈/熔断）
├── guard_rules.yaml        # 治理规则配置文件
├── Makefile                # 一键命令（make test/install/demo/dist）
├── install.sh              # Linux/macOS 安装脚本
├── install.ps1             # Windows 安装脚本
├── requirements.txt        # 依赖清单
└── pytest.ini              # pytest 配置
```

## 安全

- API Key 存储在 `.env` 文件中（明文风险见下文）
- `.env` 在 `.gitignore` 中，永不提交
- `credential status` 仅显示"已配置/未配置"，不回显明文
- 所有核心机制在移除 LLM 后仍可通过 `pytest` 验证
- 路径隔离：`pathlib.Path.resolve().is_relative_to()` 物理路径校验，防止路径遍历
- 命令安全：`shlex.split()` 词法解析 + 正则双重校验，防止 `sudo` 前缀绕过
- 默认拒绝：规则解析失败时降级为全量 BLOCK 模式

### `.env` 明文风险

`.env` 文件为明文存储。任何对文件系统有读权限的进程均可读取。
建议设置文件权限：`chmod 600 .env`

## 已知限制

- 需要 Python 3.11+（不支持 Python 3.10 及以下）
- 不在沙箱/容器内运行 agent 时，工具执行器直接操作宿主机文件系统
- 仅支持 DeepSeek LLM API（接口抽象预留了多 LLM 扩展性）
- Shell 命令执行依赖于系统 shell（Linux/macOS: `/bin/sh`, Windows: `cmd.exe`）
- 不支持 REPL 交互模式（仅 `--task` 单次任务模式）