# Coding Agent Harness 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 从零构建一个纯 CLI 的 Coding Agent Harness，重点维度为治理（多维度规则引擎 + HITL 状态机），所有核心机制可通过 mock LLM 进行确定性单元测试。

**Architecture:** 核心/IO 分离架构。Core 层（AgentLoop + GuardEngine + Executor + FeedbackEngine + SessionStore）通过依赖注入组装，所有 IO 通过 `IOInterface` Protocol 完成。CLI 适配器（ClIO）和测试适配器（SilentIO）实现同一接口，WebUI 后期可无缝接入。

**Tech Stack:** Python 3.11+, pytest, httpx, python-dotenv, pyyaml

## Global Constraints

- Python 3.11+（依赖 `pathlib.is_relative_to` 和 `dataclasses` 标准库）
- 不引入 LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex 等 agent 编排框架
- 核心机制仅使用 Python 标准库（`pathlib`, `shlex`, `json`, `re`, `subprocess`, `getpass`, `dataclasses`）
- 所有测试必须在 mock LLM 模式下运行，不依赖网络与真实 LLM API
- `.env` 在 `.gitignore` 中，凭据绝不硬编码、不提交 Git、不写入日志
- 每个 task 必须 TDD：先写失败测试（红）→ 最小实现（绿）
- 每个 task 完成后 commit，commit message 标注 task 编号

---

## 依赖关系图

```
                    ┌─ T03 (Mock LLM) ─────────────┐
                    │                               │
T01 ──→ T02 ──┬─── T04 (Config) ──→ T07→T08→T09→T10 ──→ T11 ──┐
              │                                               │
              ├─── T05 (Credential) ──────────────────────────┤
              │                                               │
              └─── T06 (Session) ─────────────────────────────┤
                                                               ↓
                                              T12 ──→ T13 ──→ T14
                                                               │
                                                               ↓
                                              T15 ──→ T16 ──→ T17 ──→ T18
```

**并行组**：T03, T04, T05, T06 可完全并行（无相互依赖）

## Worktree 分配

| Worktree | Task | 策略 |
|----------|------|------|
| `phase1-infra` | T01, T02 | 串行 |
| `phase2-base` | T03, T04, T05, T06 | 4 个并行 |
| `phase3-governance` | T07, T08, T09, T10 | 严格串行 |
| `phase4-executor` | T11 | 单 task |
| `phase5-core` | T12, T13, T14 | 严格串行 |
| `phase6-io` | T15, T16, T17, T18 | 串行 |

---

### Task 1: 项目脚手架 + 测试基础设施

**目标**：建立项目骨架，确保 pytest 可运行、`.gitignore` 拦截敏感文件、共享 fixture 可用。

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `tests/conftest.py`

**Interfaces:**
- Consumes: (none — first task)
- Produces: `tmp_workspace` fixture (临时目录 Path), `sample_action` fixture, `sample_session` fixture

- [x] **Step 0: 初始化 Git 仓库**

```bash
git init
```

- [x] **Step 1: 创建 `.gitignore`**

```
.env
__pycache__/
.pytest_cache/
*.pyc
.venv/
venv/
*.egg-info/
dist/
```

- [x] **Step 2: 创建 `requirements.txt`**

```
httpx>=0.27
pytest>=8.0
python-dotenv>=1.0
pyyaml>=6.0
```

- [x] **Step 3: 创建 `pytest.ini`**

```ini
[pytest]
testpaths = tests
addopts = -v --tb=short
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [x] **Step 4: 创建 `tests/conftest.py`**

```python
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def tmp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_action():
    from src.models import Action
    return Action(tool="read_file", params={"path": "test.py"}, reason="read test file")

@pytest.fixture
def sample_session():
    from src.models import Session
    return Session(
        session_id="test-session-001",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        task_description="test task",
        conventions=[{"key": "test_framework", "value": "pytest"}],
        tags=["test"]
    )
```

- [x] **Step 5: 验证**

```bash
pip install -r requirements.txt
pytest --collect-only
```
Expected: 输出 "no tests collected"（尚无测试文件，但 pytest 正常运行）

```bash
git check-ignore .env
```
Expected: 输出 `.env`

- [x] **Step 6: Commit**

```bash
git add .gitignore requirements.txt pytest.ini tests/conftest.py
git commit -m "chore: project scaffold with pytest and shared fixtures"
```

---

### Task 2: 数据模型定义

**目标**：定义 SPEC 第 6 章全部 dataclass 和 Enum，作为所有模块的共享类型契约。

**Files:**
- Create: `src/__init__.py`
- Create: `src/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: (none beyond stdlib)
- Produces: `Tool(Enum)`, `Verdict(Enum)`, `FeedbackCategory(Enum)`, `TaskStatus(Enum)`, `Action`, `ToolResult`, `GuardRule`, `GuardDecision`, `RiskInfo`, `ApprovalResult`, `FeedbackResult`, `Turn`, `Task`, `TaskResult`, `Session`

- [x] **Step 1: 写失败测试**

```python
# tests/test_models.py
from src.models import Action, ToolResult, GuardDecision, Verdict, FeedbackResult, FeedbackCategory, Turn, Task, TaskResult, Session

def test_action_creation():
    action = Action(tool="read_file", params={"path": "foo.py"}, reason="read")
    assert action.tool == "read_file"
    assert action.params == {"path": "foo.py"}

def test_tool_result_defaults():
    result = ToolResult()
    assert result.exit_code == 0
    assert result.stdout == ""

def test_guard_decision_enum():
    decision = GuardDecision(verdict=Ver.BLOCK, matched_rule="shell-dangerous", reason="dangerous")
    assert decision.verdict == Ver.BLOCK

def test_feedback_result():
    fb = FeedbackResult(category="TEST_FAILURE", round=1, should_retry=True, context_for_llm="error details")
    assert fb.category == "TEST_FAILURE"
    assert fb.round == 1
    assert fb.should_retry is True

def test_turn_optional_fields():
    action = Action(tool="read_file", params={"path": "test.py"})
    guard = GuardDecision(verdict=Ver.SAFE)
    turn = Turn(turn_number=1, timestamp="2026-01-01T00:00:00Z", action=action, guard_decision=guard)
    assert turn.approval is None
    assert turn.result is None
    assert turn.feedback is None

def test_task_result_defaults():
    result = TaskResult(status="success")
    assert result.turns == []
    assert result.summary == ""

def test_session_creation():
    session = Session(
        session_id="abc-123",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        task_description="test",
        conventions=[{"key": "framework", "value": "pytest"}],
        tags=["testing"]
    )
    assert session.session_id == "abc-123"
    assert len(session.conventions) == 1
    assert session.decisions == []
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'src.models'`

- [x] **Step 3: 实现 `src/models.py`**

```python
from dataclasses import dataclass, field
from enum import Enum
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
    tool: str
    params: dict
    reason: str = ""

@dataclass
class ToolResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0

@dataclass
class GuardRule:
    id: str
    action_type: str
    scope: str
    risk_level: str
    verdict: str
    pattern: Optional[str] = None
    description: str = ""

@dataclass
class GuardDecision:
    verdict: str
    matched_rule: str = "default"
    reason: str = ""

@dataclass
class RiskInfo:
    action_summary: str
    verdict: str
    matched_rule: str
    reason: str

@dataclass
class ApprovalResult:
    approved: bool
    reason: str = ""

@dataclass
class FeedbackResult:
    category: str
    round: int
    should_retry: bool
    context_for_llm: str = ""

@dataclass
class Turn:
    turn_number: int
    timestamp: str
    action: Action
    guard_decision: GuardDecision
    approval: Optional[ApprovalResult] = None
    result: Optional[ToolResult] = None
    feedback: Optional[FeedbackResult] = None

@dataclass
class Task:
    description: str
    context: dict = field(default_factory=dict)

@dataclass
class TaskResult:
    status: str
    turns: list = field(default_factory=list)
    summary: str = ""

@dataclass
class Session:
    session_id: str
    created_at: str
    updated_at: str
    task_description: str
    decisions: list = field(default_factory=list)
    conventions: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    summary: str = ""
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_models.py -v
```
Expected: 7 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/__init__.py src/models.py tests/test_models.py
git commit -m "feat(T02): define data models (Action, GuardDecision, Session, etc.)"
```

---

### Task 3: Mock LLM 抽象

**目标**：实现 `ScriptedMockLLM`，支持注入 `List[Action]` 动作队列，队列耗尽返回 FINISH 信号。

**Files:**
- Create: `src/mock_llm.py`
- Create: `tests/test_mock_llm.py`

**Interfaces:**
- Consumes: `src.models.Action`
- Produces: `ScriptedMockLLM(actions: list[Action])` 类，`chat(messages: list[dict]) -> dict` 方法

- [x] **Step 1: 写失败测试**

```python
# tests/test_mock_llm.py
from src.models import Action
from src.mock_llm import ScriptedMockLLM

def test_returns_actions_in_order():
    actions = [
        Action(tool="read_file", params={"path": "a.py"}),
        Action(tool="write_file", params={"path": "b.py", "content": "x"}),
        Action(tool="run_tests", params={"target": "tests/"}),
    ]
    llm = ScriptedMockLLM(actions)

    resp1 = llm.chat([{"role": "user", "content": "task"}])
    assert resp1["action"] == "read_file"
    assert resp1["params"] == {"path": "a.py"}

    resp2 = llm.chat([{"role": "user", "content": "continue"}])
    assert resp2["action"] == "write_file"

    resp3 = llm.chat([{"role": "user", "content": "continue"}])
    assert resp3["action"] == "run_tests"

def test_queue_exhausted_returns_finish():
    llm = ScriptedMockLLM([Action(tool="read_file", params={"path": "x.py"})])
    llm.chat([])  # consume
    resp = llm.chat([])
    assert resp["action"] == "finish"
    assert "queue exhausted" in resp.get("reason", "")

def test_call_count_tracks_invocations():
    llm = ScriptedMockLLM([Action(tool="read_file", params={"path": "x.py"})])
    assert llm.call_count == 0
    llm.chat([])
    assert llm.call_count == 1
    llm.chat([])
    assert llm.call_count == 2
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_mock_llm.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mock_llm'`

- [x] **Step 3: 实现 `src/mock_llm.py`**

```python
class ScriptedMockLLM:
    def __init__(self, actions: list):
        self.queue = actions
        self.call_count = 0

    def chat(self, messages: list[dict]) -> dict:
        if self.call_count >= len(self.queue):
            return {"action": "finish", "reason": "queue exhausted"}
        action = self.queue[self.call_count]
        self.call_count += 1
        return {"action": action.tool, "params": action.params}
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_mock_llm.py -v
```
Expected: 3 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/mock_llm.py tests/test_mock_llm.py
git commit -m "feat(T03): implement ScriptedMockLLM with action queue"
```

---

### Task 4: 配置加载器

**目标**：实现 YAML 规则文件解析，加载为 `List[GuardRule]`，文件不存在时降级为内置默认规则。

**Files:**
- Create: `src/config.py`
- Create: `guard_rules.yaml`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: `src.models.GuardRule`
- Produces: `load_rules(path: str) -> list[GuardRule]`

- [x] **Step 1: 写失败测试**

```python
# tests/test_config.py
import tempfile
from src.config import load_rules

def test_load_default_rules_when_file_missing():
    rules = load_rules("nonexistent_config.yaml")
    assert len(rules) >= 5
    rule_ids = [r.id for r in rules]
    assert "fs-delete-system" in rule_ids
    assert "shell-dangerous" in rule_ids

def test_load_custom_rules():
    yaml_content = """rules:
  - id: "custom-rule"
    action_type: "FileSystem"
    scope: "Workspace"
    risk_level: "LOW"
    verdict: "SAFE"
    description: "test rule"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    rules = load_rules(tmp_path)
    assert len(rules) == 1
    assert rules[0].id == "custom-rule"
    assert rules[0].verdict == "SAFE"

def test_load_rules_returns_guard_rule_objects():
    rules = load_rules("nonexistent_config.yaml")
    for rule in rules:
        assert hasattr(rule, "id")
        assert hasattr(rule, "action_type")
        assert hasattr(rule, "verdict")
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_config.py -v
```
Expected: FAIL

- [x] **Step 3: 实现 `src/config.py`**

```python
import yaml
from pathlib import Path
from src.models import GuardRule

BUILTIN_RULES = [
    GuardRule(
        id="fs-delete-system", action_type="FileSystem", scope="System",
        risk_level="CRITICAL", verdict="BLOCK", pattern="delete|rm|unlink",
        description="禁止删除系统级文件"
    ),
    GuardRule(
        id="shell-dangerous", action_type="Shell", scope="System",
        risk_level="CRITICAL", verdict="BLOCK",
        pattern="rm -rf /|shutdown|reboot|mkfs",
        description="禁止执行危险系统命令"
    ),
    GuardRule(
        id="shell-sudo-rm", action_type="Shell", scope="System",
        risk_level="CRITICAL", verdict="BLOCK",
        pattern=r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f?|-rf|--recursive)",
        description="禁止递归删除命令（含 sudo 前缀也能匹配）"
    ),
    GuardRule(
        id="network-outbound", action_type="Network", scope="System",
        risk_level="HIGH", verdict="BLOCK",
        pattern=r"curl.*\|.*(bash|sh|python|perl)|wget.*-O.*\|.*sh",
        description="禁止从网络下载并执行脚本"
    ),
    GuardRule(
        id="git-force-push", action_type="Shell", scope="Project",
        risk_level="HIGH", verdict="BLOCK",
        pattern=r"git\s+push\s+.*(--force|-f)",
        description="禁止强制推送"
    ),
]

def load_rules(path: str) -> list[GuardRule]:
    config_path = Path(path)
    if not config_path.exists():
        return BUILTIN_RULES

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules = []
    for item in data.get("rules", []):
        rules.append(GuardRule(
            id=item["id"],
            action_type=item["action_type"],
            scope=item["scope"],
            risk_level=item["risk_level"],
            verdict=item["verdict"],
            pattern=item.get("pattern"),
            description=item["description"],
        ))
    return rules if rules else BUILTIN_RULES
```

- [x] **Step 4: 创建 `guard_rules.yaml`**（默认规则文件，内容同 BUILTIN_RULES 的 YAML 版本）

- [x] **Step 5: 运行验证通过**

```bash
pytest tests/test_config.py -v
```
Expected: 3 tests PASS

- [x] **Step 6: Commit**

```bash
git add src/config.py guard_rules.yaml tests/test_config.py
git commit -m "feat(T04): implement config loader with builtin fallback rules"
```

---

### Task 5: 凭据管理

**目标**：实现 `.env` 读写 + `getpass` 隐式输入，`status` 仅显示"已配置/未配置"。

**Files:**
- Create: `src/credential.py`
- Create: `tests/test_credential.py`

**Interfaces:**
- Consumes: (none beyond stdlib + python-dotenv)
- Produces: `get_key() -> str | None`, `set_key()`, `clear_key()`, `status() -> str`

- [x] **Step 1: 写失败测试**

```python
# tests/test_credential.py
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.credential import get_key, set_key, clear_key, status

def test_status_returns_weipeizhi_when_no_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    monkeypatch.setattr("src.credential.ENV_FILE", env_file)
    monkeypatch.setattr("src.credential.ENV_KEY", "DEEPSEEK_API_KEY")
    assert "未配置" in status()

def test_status_returns_yipeizhi_when_key_set(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-test-123")
    monkeypatch.setattr("src.credential.ENV_FILE", env_file)
    monkeypatch.setattr("src.credential.ENV_KEY", "DEEPSEEK_API_KEY")
    assert "已配置" in status()

def test_status_does_not_leak_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-very-secret-key")
    monkeypatch.setattr("src.credential.ENV_FILE", env_file)
    monkeypatch.setattr("src.credential.ENV_KEY", "DEEPSEEK_API_KEY")
    result = status()
    assert "sk-very-secret-key" not in result

def test_clear_key_removes_entry(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-test-123\nOTHER_VAR=value")
    monkeypatch.setattr("src.credential.ENV_FILE", env_file)
    monkeypatch.setattr("src.credential.ENV_KEY", "DEEPSEEK_API_KEY")
    clear_key()
    content = env_file.read_text()
    assert "DEEPSEEK_API_KEY" not in content
    assert "OTHER_VAR=value" in content
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_credential.py -v
```
Expected: FAIL

- [x] **Step 3: 实现 `src/credential.py`**

```python
import os
import getpass
from pathlib import Path
from dotenv import load_dotenv, set_key as dotenv_set_key, unset_key

ENV_FILE = Path(".env")
ENV_KEY = "DEEPSEEK_API_KEY"

def get_key() -> str | None:
    load_dotenv(ENV_FILE)
    return os.environ.get(ENV_KEY)

def set_key():
    key = getpass.getpass("Enter API Key: ")
    if not ENV_FILE.exists():
        ENV_FILE.touch()
    dotenv_set_key(str(ENV_FILE), ENV_KEY, key)
    print("API Key configured.")

def clear_key():
    if ENV_FILE.exists():
        unset_key(str(ENV_FILE), ENV_KEY)
        print("API Key cleared.")
    else:
        print("No .env file found, nothing to clear.")

def status() -> str:
    load_dotenv(ENV_FILE)
    if os.environ.get(ENV_KEY):
        return "已配置"
    return "未配置"
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_credential.py -v
```
Expected: 4 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/credential.py tests/test_credential.py
git commit -m "feat(T05): implement credential management with getpass"
```

---

### Task 6: 会话存储

**目标**：实现 JSON 文件读写 + 关键词检索，存储到 `~/.ai_harness/sessions/`。

**Files:**
- Create: `src/session_store.py`
- Create: `tests/test_session_store.py`

**Interfaces:**
- Consumes: `src.models.Session`
- Produces: `save_session(session: Session)`, `load_session(session_id: str) -> Session`, `search_sessions(keywords: list[str]) -> list[Session]`

- [x] **Step 1: 写失败测试**

```python
# tests/test_session_store.py
from src.models import Session
from src.session_store import save_session, load_session, search_sessions

def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    store_dir = tmp_path / "sessions"
    monkeypatch.setattr("src.session_store.STORE_DIR", store_dir)

    session = Session(
        session_id="test-001",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        task_description="refactor user module",
        conventions=[{"key": "test_framework", "value": "pytest"}],
        decisions=[{"turn": 3, "decision": "use dataclass", "reason": "better types"}],
        tags=["refactoring", "user-module"],
    )
    save_session(session)
    loaded = load_session("test-001")

    assert loaded.session_id == "test-001"
    assert loaded.task_description == "refactor user module"
    assert len(loaded.conventions) == 1
    assert loaded.conventions[0]["key"] == "test_framework"
    assert len(loaded.decisions) == 1
    assert "refactoring" in loaded.tags

def test_search_by_keyword(tmp_path, monkeypatch):
    store_dir = tmp_path / "sessions"
    monkeypatch.setattr("src.session_store.STORE_DIR", store_dir)

    s1 = Session(session_id="s1", created_at="", updated_at="",
                 task_description="refactor", tags=["refactoring"], conventions=[], decisions=[])
    s2 = Session(session_id="s2", created_at="", updated_at="",
                 task_description="fix bug", tags=["bugfix"], conventions=[], decisions=[])
    save_session(s1)
    save_session(s2)

    results = search_sessions(["refactoring"])
    assert len(results) == 1
    assert results[0].session_id == "s1"

def test_search_returns_empty_for_no_match(tmp_path, monkeypatch):
    store_dir = tmp_path / "sessions"
    monkeypatch.setattr("src.session_store.STORE_DIR", store_dir)

    s1 = Session(session_id="s1", created_at="", updated_at="",
                 task_description="test", tags=["testing"], conventions=[], decisions=[])
    save_session(s1)

    results = search_sessions(["nonexistent"])
    assert len(results) == 0
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_session_store.py -v
```
Expected: FAIL

- [x] **Step 3: 实现 `src/session_store.py`**

```python
import json
from pathlib import Path
from dataclasses import asdict
from src.models import Session

STORE_DIR = Path.home() / ".ai_harness" / "sessions"

def _ensure_dir():
    STORE_DIR.mkdir(parents=True, exist_ok=True)

def save_session(session: Session):
    _ensure_dir()
    filepath = STORE_DIR / f"{session.session_id}.json"
    data = asdict(session)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_session(session_id: str) -> Session | None:
    filepath = STORE_DIR / f"{session_id}.json"
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Session(**data)
    except (json.JSONDecodeError, TypeError):
        return None

def search_sessions(keywords: list[str]) -> list[Session]:
    _ensure_dir()
    results = []
    for filepath in sorted(STORE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if len(results) >= 5:
            break
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            tags = data.get("tags", [])
            desc = data.get("task_description", "")
            if any(kw.lower() in " ".join(tags + [desc]).lower() for kw in keywords):
                results.append(Session(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    return results
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_session_store.py -v
```
Expected: 3 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/session_store.py tests/test_session_store.py
git commit -m "feat(T06): implement session store with JSON persistence and keyword search"
```

---

### Task 7: GuardRule 模型 + 规则匹配引擎

**目标**：实现 `GuardEngine` 核心骨架：从配置加载规则 → 按 action_type/scope 维度匹配 → 输出 `GuardDecision`。

**Files:**
- Create: `src/guardrail.py`
- Create: `tests/test_guardrail.py`

**Interfaces:**
- Consumes: `src.models.GuardRule`, `src.models.GuardDecision`, `src.models.Action`, `src.models.Verdict`, `src.config.load_rules`
- Produces: `GuardEngine(rules, workspace)` 类，`check(action: Action) -> GuardDecision` 方法

- [x] **Step 1: 写失败测试**

```python
# tests/test_guardrail.py
from pathlib import Path
from src.models import Action, GuardRule, GuardDecision, Verdict
from src.guardrail import GuardEngine

def make_engine(rules=None, workspace=None):
    if rules is None:
        rules = [
            GuardRule(
                id="shell-dangerous", action_type="Shell", scope="System",
                risk_level="CRITICAL", verdict="BLOCK",
                pattern="rm -rf /|shutdown|reboot",
                description="禁止执行危险系统命令"
            ),
            GuardRule(
                id="fs-read-safe", action_type="FileSystem", scope="Workspace",
                risk_level="LOW", verdict="SAFE",
                description="允许读取 workspace 内文件"
            ),
            GuardRule(
                id="shell-pip-warn", action_type="Shell", scope="Workspace",
                risk_level="MEDIUM", verdict="WARN",
                pattern="pip install",
                description="pip install 记录警告"
            ),
        ]
    if workspace is None:
        workspace = Path("/tmp/test_workspace")
    return GuardEngine(rules, workspace)

def test_block_dangerous_shell():
    engine = make_engine()
    action = Action(tool="execute_shell", params={"command": "rm -rf /"})
    decision = engine.check(action)
    assert decision.verdict == Ver.BLOCK
    assert decision.matched_rule == "shell-dangerous"

def test_allow_safe_read():
    engine = make_engine()
    action = Action(tool="read_file", params={"path": "src/main.py"})
    decision = engine.check(action)
    assert decision.verdict == Ver.SAFE

def test_warn_pip_install():
    engine = make_engine()
    action = Action(tool="execute_shell", params={"command": "pip install pytest"})
    decision = engine.check(action)
    assert decision.verdict == Ver.WARN

def test_unknown_tool_returns_safe():
    engine = make_engine()
    action = Action(tool="unknown_tool", params={})
    decision = engine.check(action)
    assert decision.verdict == Ver.SAFE
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_guardrail.py -v
```
Expected: FAIL

- [x] **Step 3: 实现 `src/guardrail.py`**

```python
import re
from pathlib import Path
from src.models import Action, GuardRule, GuardDecision, Verdict

VERDICT_PRIORITY = {Ver.BLOCK: 3, Ver.WARN: 2, Ver.SAFE: 1}

class GuardEngine:
    def __init__(self, rules: list[GuardRule], workspace: Path):
        self.rules = rules
        self.workspace = workspace.resolve()

    def check(self, action: Action) -> GuardDecision:
        action_type = self._classify_action_type(action.tool)
        candidates = [r for r in self.rules if r.action_type == action_type]
        if not candidates:
            return GuardDecision(verdict=Ver.SAFE, reason="无匹配规则")

        best = None
        for rule in candidates:
            if rule.pattern:
                cmd = action.params.get("command", "") or action.params.get("path", "")
                if re.search(rule.pattern, cmd):
                    if best is None or VERDICT_PRIORITY[Ver(rule.verdict)] > VERDICT_PRIORITY[Ver(best.verdict)]:
                        best = rule
            else:
                if best is None or VERDICT_PRIORITY[Ver(rule.verdict)] > VERDICT_PRIORITY[Ver(best.verdict)]:
                    best = rule

        if best is None:
            return GuardDecision(verdict=Ver.SAFE, reason="无匹配规则")

        return GuardDecision(
            verdict=Ver(best.verdict),
            matched_rule=best.id,
            reason=best.description
        )

    def _classify_action_type(self, tool: str) -> str:
        mapping = {
            "read_file": "FileSystem",
            "write_file": "FileSystem",
            "execute_shell": "Shell",
            "run_tests": "Shell",
            "run_lint": "Shell",
        }
        return mapping.get(tool, "Unknown")
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_guardrail.py -v
```
Expected: 4 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/guardrail.py tests/test_guardrail.py
git commit -m "feat(T07): implement GuardEngine skeleton with rule matching"
```

---

### Task 8: 路径隔离校验

**目标**：在 GuardEngine 中集成 `validate_path()`，使用 `pathlib.Path.resolve().is_relative_to()` 防止路径遍历。

**Files:**
- Modify: `src/guardrail.py`（新增 `validate_path` 方法）
- Modify: `tests/test_guardrail.py`（新增路径测试）

**Interfaces:**
- Consumes: `src.guardrail.GuardEngine`
- Produces: `GuardEngine.validate_path(target: str) -> GuardDecision`

- [x] **Step 1: 写失败测试**

```python
# 追加到 tests/test_guardrail.py
def test_path_traversal_blocked(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "secret.txt").write_text("secret")

    engine = GuardEngine([], workspace)
    decision = engine.validate_path(str(tmp_path / "outside" / "secret.txt"))
    assert decision.verdict == Ver.BLOCK
    assert "路径越界" in decision.reason

def test_path_in_workspace_allowed(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("code")

    engine = GuardEngine([], workspace)
    decision = engine.validate_path(str(workspace / "src" / "main.py"))
    assert decision.verdict == Ver.SAFE

def test_dot_dot_slash_traversal_blocked(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()

    engine = GuardEngine([], workspace)
    decision = engine.validate_path(str(workspace / "src" / "../../../etc/passwd"))
    assert decision.verdict == Ver.BLOCK
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_guardrail.py::test_path_traversal_blocked -v
```
Expected: FAIL — `AttributeError: 'GuardEngine' object has no attribute 'validate_path'`

- [x] **Step 3: 实现 `validate_path` 方法**

```python
# 追加到 src/guardrail.py 的 GuardEngine 类中
def validate_path(self, target: str) -> GuardDecision:
    resolved = Path(target).resolve()
    if not resolved.is_relative_to(self.workspace):
        return GuardDecision(
            verdict=Ver.BLOCK,
            matched_rule="path-boundary",
            reason=f"路径越界：{target} 不在 workspace {self.workspace} 内"
        )
    return GuardDecision(verdict=Ver.SAFE, matched_rule="default", reason="")
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_guardrail.py -v
```
Expected: 7 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/guardrail.py tests/test_guardrail.py
git commit -m "feat(T08): add path traversal protection with resolve().is_relative_to()"
```

---

### Task 9: Shell 命令双重校验

**目标**：在 GuardEngine 中集成 `check_shell_command()`，使用 `shlex.split()` + `re.search` + `re.fullmatch` 防止 `sudo` 等前缀绕过。

**Files:**
- Modify: `src/guardrail.py`（新增 `check_shell_command` 方法）
- Modify: `tests/test_guardrail.py`（新增 Shell 测试）

**Interfaces:**
- Consumes: `src.guardrail.GuardEngine`
- Produces: `GuardEngine.check_shell_command(command: str) -> GuardDecision`

- [x] **Step 1: 写失败测试**

```python
# 追加到 tests/test_guardrail.py
def test_sudo_rm_rf_blocked():
    engine = make_engine()
    decision = engine.check_shell_command("sudo rm -rf /")
    assert decision.verdict == Ver.BLOCK

def test_safe_ls_allowed():
    engine = make_engine()
    decision = engine.check_shell_command("ls -la")
    assert decision.verdict == Ver.SAFE

def test_shlex_quote_handling():
    engine = make_engine()
    decision = engine.check_shell_command("rm -rf '/etc/passwd'")
    assert decision.verdict == Ver.BLOCK

def test_env_prefix_rm_blocked():
    engine = make_engine()
    decision = engine.check_shell_command("env rm -rf /")
    assert decision.verdict == Ver.BLOCK
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_guardrail.py::test_sudo_rm_rf_blocked -v
```
Expected: FAIL

- [x] **Step 3: 实现 `check_shell_command` 方法**

```python
# 追加到 src/guardrail.py 的 GuardEngine 类中
import shlex

def check_shell_command(self, command: str) -> GuardDecision:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return GuardDecision(verdict=Ver.BLOCK, reason="命令解析失败")

    cmd_name = tokens[0] if tokens else ""

    shell_rules = [r for r in self.rules if r.action_type == "Shell" and r.pattern]
    for rule in shell_rules:
        if re.search(rule.pattern, command) or re.fullmatch(rule.pattern, cmd_name):
            return GuardDecision(
                verdict=Ver(rule.verdict),
                matched_rule=rule.id,
                reason=rule.description
            )

    return GuardDecision(verdict=Ver.SAFE, matched_rule="default", reason="")
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_guardrail.py -v
```
Expected: 11 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/guardrail.py tests/test_guardrail.py
git commit -m "feat(T09): add shell command double-check with shlex + regex"
```

---

### Task 10: 治理状态机集成 + 完整 test_guardrail.py

**目标**：将 T07-T09 的组件集成为完整 `GuardEngine`，实现 IDENTIFY→CLASSIFY→SAFE/WARN/BLOCK 状态机。补充参数化测试。

**Files:**
- Modify: `src/guardrail.py`（集成完整 `check()` 方法，整合路径校验和 Shell 校验）
- Modify: `tests/test_guardrail.py`（补充参数化测试）

**Interfaces:**
- Consumes: `src.guardrail.GuardEngine` (T07-T09)
- Produces: 完整 `GuardEngine.check(action) -> GuardDecision`（含路径校验和 Shell 校验）

- [x] **Step 1: 写失败测试**

```python
# 追加到 tests/test_guardrail.py
import pytest

def test_full_check_integrates_path_validation(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()

    rules = [
        GuardRule(
            id="fs-write-block-system", action_type="FileSystem", scope="System",
            risk_level="CRITICAL", verdict="BLOCK",
            description="禁止写入系统文件"
        ),
    ]
    engine = GuardEngine(rules, workspace)
    action = Action(tool="write_file", params={"path": str(tmp_path / "outside" / "file.txt"), "content": "x"})
    decision = engine.check(action)
    assert decision.verdict == Ver.BLOCK

def test_full_check_integrates_shell_validation():
    engine = make_engine()
    action = Action(tool="execute_shell", params={"command": "sudo rm -rf /"})
    decision = engine.check(action)
    assert decision.verdict == Ver.BLOCK

@pytest.mark.parametrize("tool,params,expected_verdict", [
    ("read_file", {"path": "src/main.py"}, Ver.SAFE),
    ("execute_shell", {"command": "rm -rf /"}, Ver.BLOCK),
    ("execute_shell", {"command": "shutdown now"}, Ver.BLOCK),
    ("execute_shell", {"command": "sudo rm -rf /etc"}, Ver.BLOCK),
    ("execute_shell", {"command": "env rm -rf /"}, Ver.BLOCK),
    ("execute_shell", {"command": "ls -la"}, Ver.SAFE),
    ("execute_shell", {"command": "python -m pytest"}, Ver.SAFE),
    ("execute_shell", {"command": "pip install pytest"}, Ver.WARN),
    ("read_file", {"path": "README.md"}, Ver.SAFE),
    ("write_file", {"path": "src/new.py", "content": "x"}, Ver.SAFE),
])
def test_parametrize_rules(tool, params, expected_verdict):
    engine = make_engine()
    action = Action(tool=tool, params=params)
    decision = engine.check(action)
    assert decision.verdict == expected_verdict, f"Expected {expected_verdict} for {tool}({params})"
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_guardrail.py::test_full_check_integrates_path_validation -v
```
Expected: FAIL — T07 的 `check()` 未集成 `validate_path`

- [x] **Step 3: 重构 `GuardEngine.check()` 集成全部校验**

```python
# 修改 src/guardrail.py 的 check() 方法
def check(self, action: Action) -> GuardDecision:
    action_type = self._classify_action_type(action.tool)

    # 文件操作：先做路径校验
    if action_type == "FileSystem":
        target = action.params.get("path", "")
        if target:
            path_decision = self.validate_path(target)
            if path_decision.verdict == Ver.BLOCK:
                return path_decision

    # Shell 操作：先做命令校验
    if action_type == "Shell":
        command = action.params.get("command", "")
        if command:
            shell_decision = self.check_shell_command(command)
            if shell_decision.verdict != Ver.SAFE:
                return shell_decision

    # 规则匹配
    candidates = [r for r in self.rules if r.action_type == action_type]
    if not candidates:
        return GuardDecision(verdict=Ver.SAFE, reason="无匹配规则")

    best = None
    for rule in candidates:
        if best is None or VERDICT_PRIORITY[Ver(rule.verdict)] > VERDICT_PRIORITY[Ver(best.verdict)]:
            best = rule

    if best is None:
        return GuardDecision(verdict=Ver.SAFE, reason="无匹配规则")

    return GuardDecision(
        verdict=Ver(best.verdict),
        matched_rule=best.id,
        reason=best.description
    )
```

- [x] **Step 4: 运行全部测试通过**

```bash
pytest tests/test_guardrail.py -v
```
Expected: 15 tests PASS（覆盖 AC2-AC5）

- [x] **Step 5: Commit**

```bash
git add src/guardrail.py tests/test_guardrail.py
git commit -m "feat(T10): integrate full guard state machine with parametrized tests"
```

---

### Task 11: 工具执行器

**目标**：实现 `Executor`，维护 `{tool_name: callable}` 注册表，`dispatch(action)` 路由到对应工具函数。`write_file` 含 `parent.mkdir(parents=True)` 建图保障。

**Files:**
- Create: `src/executor.py`
- Create: `tests/test_executor.py`

**Interfaces:**
- Consumes: `src.models.Action`, `src.models.ToolResult`
- Produces: `Executor(workspace: Path)` 类，`dispatch(action: Action) -> ToolResult` 方法

- [x] **Step 1: 写失败测试**

```python
# tests/test_executor.py
from src.models import Action
from src.executor import Executor

def test_read_file(tmp_workspace):
    (tmp_workspace / "test.txt").write_text("hello world")
    executor = Executor(tmp_workspace)
    result = executor.dispatch(Action(tool="read_file", params={"path": str(tmp_workspace / "test.txt")}))
    assert result.exit_code == 0
    assert result.stdout == "hello world"

def test_write_file_creates_parent_dirs(tmp_workspace):
    executor = Executor(tmp_workspace)
    target = tmp_workspace / "sub" / "deep" / "file.txt"
    result = executor.dispatch(Action(tool="write_file", params={"path": str(target), "content": "data"}))
    assert result.exit_code == 0
    assert target.exists()
    assert target.read_text() == "data"

def test_unknown_tool(tmp_workspace):
    executor = Executor(tmp_workspace)
    result = executor.dispatch(Action(tool="nonexistent_tool", params={}))
    assert result.exit_code == -2
    assert "UNKNOWN_TOOL" in result.stderr

def test_shell_command(tmp_workspace):
    executor = Executor(tmp_workspace)
    result = executor.dispatch(Action(tool="execute_shell", params={"command": "echo hello"}))
    assert result.exit_code == 0
    assert "hello" in result.stdout

def test_shell_timeout(tmp_workspace):
    executor = Executor(tmp_workspace)
    result = executor.dispatch(Action(tool="execute_shell", params={"command": "sleep 5"}), timeout=1)
    assert result.exit_code == -1
    assert "TIMEOUT" in result.stderr
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_executor.py -v
```
Expected: FAIL

- [x] **Step 3: 实现 `src/executor.py`**

```python
import subprocess
import time
from pathlib import Path
from src.models import Action, ToolResult

class Executor:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def dispatch(self, action: Action, timeout: int = 30) -> ToolResult:
        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "execute_shell": self._execute_shell,
            "run_tests": self._run_tests,
            "run_lint": self._run_lint,
        }
        handler = handlers.get(action.tool)
        if handler is None:
            return ToolResult(exit_code=-2, stderr="UNKNOWN_TOOL", duration_ms=0)

        start = time.time()
        try:
            return handler(action.params, timeout)
        except Exception as e:
            return ToolResult(exit_code=-1, stderr=str(e), duration_ms=(time.time() - start) * 1000)

    def _read_file(self, params: dict, timeout: int) -> ToolResult:
        start = time.time()
        path = Path(params["path"])
        content = path.read_text(encoding="utf-8")
        return ToolResult(stdout=content, exit_code=0, duration_ms=(time.time() - start) * 1000)

    def _write_file(self, params: dict, timeout: int) -> ToolResult:
        start = time.time()
        path = Path(params["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(params["content"], encoding="utf-8")
        return ToolResult(stdout="OK", exit_code=0, duration_ms=(time.time() - start) * 1000)

    def _execute_shell(self, params: dict, timeout: int) -> ToolResult:
        start = time.time()
        try:
            proc = subprocess.run(
                params["command"],
                shell=True,
                timeout=timeout,
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
            )
            return ToolResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=(time.time() - start) * 1000,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(exit_code=-1, stderr="TIMEOUT", duration_ms=(time.time() - start) * 1000)

    def _run_tests(self, params: dict, timeout: int) -> ToolResult:
        target = params.get("target", "")
        cmd = f"pytest {target} -q" if target else "pytest -q"
        return self._execute_shell({"command": cmd}, timeout)

    def _run_lint(self, params: dict, timeout: int) -> ToolResult:
        target = params.get("target", ".")
        cmd = f"ruff check {target}"
        return self._execute_shell({"command": cmd}, timeout)
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_executor.py -v
```
Expected: 5 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/executor.py tests/test_executor.py
git commit -m "feat(T11): implement executor with tool dispatch and mkdir guarantee"
```

---

### Task 12: 反馈引擎

**目标**：实现 `FeedbackEngine`，解析 `ToolResult` → 结构化分类 → 按连续同类失败计数 → 多轮熔断。

**Files:**
- Create: `src/feedback.py`
- Create: `tests/test_feedback.py`

**Interfaces:**
- Consumes: `src.models.ToolResult`, `src.models.FeedbackResult`
- Produces: `FeedbackEngine` 类，`analyze(result: ToolResult) -> FeedbackResult` 方法

- [x] **Step 1: 写失败测试**

```python
# tests/test_feedback.py
from src.models import ToolResult
from src.feedback import FeedbackEngine

def test_classify_test_failure():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")
    fb = engine.analyze(result)
    assert fb.category == "TEST_FAILURE"
    assert fb.round == 1
    assert fb.should_retry is True

def test_classify_success():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=0, stdout="all passed")
    fb = engine.analyze(result)
    assert fb.category == "SUCCESS"
    assert fb.should_retry is False

def test_success_resets_counter():
    engine = FeedbackEngine()
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))  # fail 1
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))  # fail 2
    engine.analyze(ToolResult(exit_code=0))                            # success
    fb = engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))  # fail again
    assert fb.round == 1

def test_category_change_resets_counter():
    engine = FeedbackEngine()
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))  # TEST_FAILURE
    fb = engine.analyze(ToolResult(exit_code=1, stderr="SyntaxError: invalid syntax"))  # COMPILE_ERROR
    assert fb.round == 1
    assert fb.category == "COMPILE_ERROR"

def test_circuit_breaker_round_3():
    engine = FeedbackEngine()
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    fb = engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    assert fb.round == 3
    assert fb.should_retry is False

def test_classify_timeout():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=-1, stderr="TIMEOUT")
    fb = engine.analyze(result)
    assert fb.category == "TIMEOUT"

def test_classify_runtime_error():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=1, stderr="Traceback (most recent call last):\nTypeError: ...")
    fb = engine.analyze(result)
    assert fb.category == "RUNTIME_ERROR"
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_feedback.py -v
```
Expected: FAIL

- [x] **Step 3: 实现 `src/feedback.py`**

```python
from src.models import ToolResult, FeedbackResult

class FeedbackEngine:
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._last_category: str | None = None

    def analyze(self, result: ToolResult) -> FeedbackResult:
        if result.exit_code == 0:
            self._counters.clear()
            self._last_category = None
            return FeedbackResult(category="SUCCESS", round=0, should_retry=False)

        category = self._classify(result)
        is_same_category = (category == self._last_category)

        if is_same_category:
            self._counters[category] = self._counters.get(category, 0) + 1
        else:
            self._counters = {category: 1}
            self._last_category = category

        round_num = self._counters[category]
        should_retry = round_num < 3

        if round_num == 1:
            context = f"[{category}]\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        elif round_num == 2:
            lines = result.stderr.strip().split("\n")
            key_lines = [l for l in lines if l.strip()][:5]
            context = f"[{category}] 关键错误:\n" + "\n".join(key_lines)
        else:
            context = f"[{category}] 连续第 {round_num} 次同类失败，已触发熔断"

        return FeedbackResult(
            category=category,
            round=round_num,
            should_retry=should_retry,
            context_for_llm=context,
        )

    def _classify(self, result: ToolResult) -> str:
        stderr = result.stderr
        if result.exit_code == -1 and "TIMEOUT" in stderr:
            return "TIMEOUT"
        if "SyntaxError" in stderr or "IndentationError" in stderr:
            return "COMPILE_ERROR"
        if "AssertionError" in stderr or "FAILED" in stderr:
            return "TEST_FAILURE"
        if "Traceback" in stderr:
            return "RUNTIME_ERROR"
        if result.exit_code != 0:
            return "UNKNOWN_ERROR"
        return "SUCCESS"
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_feedback.py -v
```
Expected: 7 tests PASS（覆盖 AC6-AC9）

- [x] **Step 5: Commit**

```bash
git add src/feedback.py tests/test_feedback.py
git commit -m "feat(T12): implement feedback engine with circuit breaker"
```

---

### Task 13: AgentLoop 主循环

**目标**：实现 `AgentLoop`，依赖注入所有组件，执行 7 步主循环。Core 层不直接 IO，所有交互通过 `IOInterface`。

**Files:**
- Create: `src/harness_core.py`
- Create: `tests/test_core.py`

**Interfaces:**
- Consumes: `src.models.*`, `src.mock_llm.ScriptedMockLLM`, `src.guardrail.GuardEngine`, `src.executor.Executor`, `src.feedback.FeedbackEngine`, `src.session_store.*`, `src.io_interface.IOInterface`
- Produces: `AgentLoop` 类，`run(task: Task, session: Session) -> TaskResult` 方法

- [x] **Step 1: 写失败测试**

```python
# tests/test_core.py
from src.models import Action, Task, Session, TaskResult, ApprovalResult
from src.mock_llm import ScriptedMockLLM
from src.harness_core import AgentLoop
from src.io_interface import SilentIO

class FakeGuard:
    def check(self, action):
        from src.models import GuardDecision, Verdict
        return GuardDecision(verdict=Ver.SAFE)

class FakeExecutor:
    def dispatch(self, action, timeout=30):
        from src.models import ToolResult
        return ToolResult(exit_code=0, stdout="ok")

class FakeFeedback:
    def analyze(self, result):
        from src.models import FeedbackResult
        return FeedbackResult(category="SUCCESS", round=0, should_retry=False)

class FakeSessionStore:
    def save_session(self, session): pass
    def search_sessions(self, keywords): return []

def test_agent_loop_completes_with_mock_llm():
    actions = [
        Action(tool="read_file", params={"path": "test.txt"}),
    ]
    llm = ScriptedMockLLM(actions)
    agent = AgentLoop(
        llm=llm,
        guard=FakeGuard(),
        executor=FakeExecutor(),
        feedback=FakeFeedback(),
        session_store=FakeSessionStore(),
        io=SilentIO(),
        max_turns=10,
    )
    task = Task(description="read a file")
    session = Session(
        session_id="s1", created_at="", updated_at="",
        task_description="test", conventions=[], tags=[]
    )
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 1
    assert result.turns[0].action.tool == "read_file"

def test_agent_loop_stops_on_finish():
    llm = ScriptedMockLLM([])  # empty queue → returns finish
    agent = AgentLoop(
        llm=llm, guard=FakeGuard(), executor=FakeExecutor(),
        feedback=FakeFeedback(), session_store=FakeSessionStore(),
        io=SilentIO(), max_turns=10,
    )
    task = Task(description="do nothing")
    session = Session(
        session_id="s1", created_at="", updated_at="",
        task_description="test", conventions=[], tags=[]
    )
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 0
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_core.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [x] **Step 3: 先创建 `src/io_interface.py`**（T13 依赖的 IO 接口）

```python
from typing import Protocol
from src.models import Action, RiskInfo, ApprovalResult

class IOInterface(Protocol):
    def output(self, message: str) -> None: ...
    def input(self, prompt: str) -> str: ...
    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult: ...

class SilentIO:
    def __init__(self, approval_result: ApprovalResult | None = None):
        self.approval_result = approval_result or ApprovalResult(approved=True)
        self.outputs: list[str] = []
        self.approval_calls: list[tuple] = []

    def output(self, message: str) -> None:
        self.outputs.append(message)

    def input(self, prompt: str) -> str:
        return ""

    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult:
        self.approval_calls.append((action, risk))
        return self.approval_result
```

- [x] **Step 4: 实现 `src/harness_core.py`**

```python
import uuid
from datetime import datetime, timezone
from src.models import Action, Task, TaskResult, Session, Turn, GuardDecision, Verdict, RiskInfo
from src.io_interface import IOInterface

class AgentLoop:
    def __init__(self, llm, guard, executor, feedback, session_store, io: IOInterface,
                 strict_mode: bool = False, max_turns: int = 50):
        self.llm = llm
        self.guard = guard
        self.executor = executor
        self.feedback = feedback
        self.session_store = session_store
        self.io = io
        self.strict_mode = strict_mode
        self.max_turns = max_turns

    def run(self, task: Task, session: Session) -> TaskResult:
        turns = []
        system_prompt = self._build_system_prompt(session)

        for turn_num in range(1, self.max_turns + 1):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.description},
            ]

            llm_response = self.llm.chat(messages)
            if llm_response.get("action") == "finish":
                break

            action = self._parse_action(llm_response)
            if action is None:
                continue

            guard_decision = self.guard.check(action)
            approval = None

            if guard_decision.verdict == Ver.BLOCK:
                risk = RiskInfo(
                    action_summary=f"{action.tool}({action.params})",
                    verdict=str(guard_decision.verdict),
                    matched_rule=guard_decision.matched_rule,
                    reason=guard_decision.reason,
                )
                approval = self.io.request_approval(action, risk)
                if not approval.approved:
                    messages.append({"role": "user", "content": f"动作被拒绝：{approval.reason}。请提供替代方案。"})
                    continue

            elif guard_decision.verdict == Ver.WARN:
                self.io.output(f"[WARN] {action.tool}: {guard_decision.reason}")
                if self.strict_mode:
                    risk = RiskInfo(
                        action_summary=f"{action.tool}({action.params})",
                        verdict=str(guard_decision.verdict),
                        matched_rule=guard_decision.matched_rule,
                        reason=guard_decision.reason,
                    )
                    approval = self.io.request_approval(action, risk)
                    if not approval.approved:
                        continue

            result = self.executor.dispatch(action)
            fb = self.feedback.analyze(result)

            turn = Turn(
                turn_number=turn_num,
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=action,
                guard_decision=guard_decision,
                approval=approval,
                result=result,
                feedback=fb,
            )
            turns.append(turn)

            if not fb.should_retry and fb.category != "SUCCESS":
                return TaskResult(status="circuit_breaker", turns=turns, summary=f"熔断于第 {turn_num} 轮")

        status = "success" if turns else "success"
        return TaskResult(status=status, turns=turns)

    def _build_system_prompt(self, session: Session) -> str:
        conventions = "\n".join(
            f"- {c['key']}: {c['value']}" for c in session.conventions
        )
        return f"""你是一个 coding agent。可用工具：read_file, write_file, execute_shell, run_tests, run_lint。
项目约定：
{conventions or '无'}
返回 JSON 格式：{{"action": "tool_name", "params": {{...}}, "reason": "..."}}
任务完成时返回：{{"action": "finish"}}"""

    def _parse_action(self, response: dict) -> Action | None:
        tool = response.get("action")
        if not tool or tool == "finish":
            return None
        return Action(
            tool=tool,
            params=response.get("params", {}),
            reason=response.get("reason", ""),
        )
```

- [x] **Step 5: 运行验证通过**

```bash
pytest tests/test_core.py -v
```
Expected: 2 tests PASS

- [x] **Step 6: Commit**

```bash
git add src/io_interface.py src/harness_core.py tests/test_core.py
git commit -m "feat(T13): implement AgentLoop with DI and 7-step main loop"
```

---

### Task 14: 核心集成测试

**目标**：补充 `test_core.py` 的完整集成测试，覆盖多轮修正、熔断、WARN strict 模式、HITL 拒绝回灌。

**Files:**
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: `src.harness_core.AgentLoop` (T13)
- Produces: 完整 test_core.py（覆盖 AC1, AC7, AC14-AC16）

- [x] **Step 1: 写失败测试**

```python
# 追加到 tests/test_core.py
from src.models import GuardDecision, Verdict, ToolResult, FeedbackResult, RiskInfo
from src.io_interface import SilentIO, ApprovalResult

class BlockingGuard:
    def check(self, action):
        if action.tool == "execute_shell":
            return GuardDecision(verdict=Ver.BLOCK, matched_rule="shell-dangerous", reason="危险命令")
        return GuardDecision(verdict=Ver.SAFE)

class FailingThenPassingExecutor:
    def __init__(self):
        self.call_count = 0
    def dispatch(self, action, timeout=30):
        self.call_count += 1
        if self.call_count == 1:
            return ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")
        return ToolResult(exit_code=0, stdout="ok")

class AlwaysFailingExecutor:
    def dispatch(self, action, timeout=30):
        return ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")

def test_guardrail_block_with_approval_rejected():
    llm = ScriptedMockLLM([Action(tool="execute_shell", params={"command": "rm -rf /"})])
    io = SilentIO(approval_result=ApprovalResult(approved=False, reason="太危险了，换个方式"))
    agent = AgentLoop(
        llm=llm, guard=BlockingGuard(), executor=FakeExecutor(),
        feedback=FakeFeedback(), session_store=FakeSessionStore(),
        io=io, max_turns=10,
    )
    task = Task(description="delete something")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert len(io.approval_calls) == 1
    assert io.approval_calls[0][1].reason == "危险命令"

def test_circuit_breaker_halts_loop():
    from src.feedback import FeedbackEngine
    llm = ScriptedMockLLM([
        Action(tool="run_tests", params={}),
        Action(tool="run_tests", params={}),
        Action(tool="run_tests", params={}),
        Action(tool="run_tests", params={}),
    ])
    agent = AgentLoop(
        llm=llm, guard=FakeGuard(), executor=AlwaysFailingExecutor(),
        feedback=FeedbackEngine(), session_store=FakeSessionStore(),
        io=SilentIO(), max_turns=10,
    )
    task = Task(description="run tests")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "circuit_breaker"

def test_feedback_loop_retries_on_failure():
    from src.feedback import FeedbackEngine
    llm = ScriptedMockLLM([
        Action(tool="run_tests", params={}),
        Action(tool="write_file", params={"path": "fix.py", "content": "fixed"}),
        Action(tool="run_tests", params={}),
    ])
    agent = AgentLoop(
        llm=llm, guard=FakeGuard(), executor=FailingThenPassingExecutor(),
        feedback=FeedbackEngine(), session_store=FakeSessionStore(),
        io=SilentIO(), max_turns=10,
    )
    task = Task(description="fix tests")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 3
    assert result.turns[0].feedback.category == "TEST_FAILURE"
    assert result.turns[2].feedback.category == "SUCCESS"
```

- [x] **Step 2: 运行验证失败**

```bash
pytest tests/test_core.py::test_circuit_breaker_halts_loop -v
```
Expected: FAIL — 熔断逻辑可能未正确触发

- [x] **Step 3: 修复 AgentLoop 确保熔断逻辑正确**

检查 `AgentLoop.run()` 中熔断判断的位置和逻辑。确保 `should_retry == False` 且 category != SUCCESS 时立即返回。

- [x] **Step 4: 运行全部测试通过**

```bash
pytest tests/test_core.py -v
```
Expected: 5 tests PASS（覆盖 AC1, AC7, AC14, AC15, AC16）

- [x] **Step 5: Commit**

```bash
git add tests/test_core.py
git commit -m "test(T14): add integration tests for circuit breaker and feedback loop"
```

---

### Task 15: IOInterface + CLI 适配器

**目标**：实现 `CliIO`（stdin/stdout 交互）+ `run_cli.py` 入口，支持完整的命令行参数。

**Files:**
- Modify: `src/io_interface.py`（新增 `CliIO` 类）
- Create: `run_cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `src.io_interface.IOInterface`, `src.harness_core.AgentLoop`, `src.models.*`
- Produces: `CliIO` 类, `run_cli.py` 入口

- [x] **Step 1: 实现 `CliIO`**（追加到 `src/io_interface.py`）

```python
class CliIO:
    def output(self, message: str) -> None:
        print(message)

    def input(self, prompt: str) -> str:
        return input(prompt)

    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult:
        print(f"\n{'='*50}")
        print(f"危险动作需要审批")
        print(f"动作: {action.tool}({action.params})")
        print(f"风险等级: {risk.verdict}")
        print(f"命中规则: {risk.matched_rule}")
        print(f"原因: {risk.reason}")
        print(f"{'='*50}")
        choice = input("批准执行? [Y]批准 / [N]拒绝: ").strip().upper()
        if choice == "Y":
            return ApprovalResult(approved=True)
        reason = input("拒绝理由（将回灌给 LLM，回车跳过）: ").strip()
        return ApprovalResult(approved=False, reason=reason)
```

- [x] **Step 2: 实现 `run_cli.py`**

```python
import argparse
from pathlib import Path
from src.models import Task, Session
from src.config import load_rules
from src.guardrail import GuardEngine
from src.executor import Executor
from src.feedback import FeedbackEngine
from src.harness_core import AgentLoop
from src.io_interface import CliIO, SilentIO
from src.mock_llm import ScriptedMockLLM
from src.session_store import save_session, search_sessions
from src.credential import status as cred_status, set_key as cred_set, clear_key as cred_clear


class DeepSeekClient:
    """真实 LLM 客户端（薄封装 httpx 调用 DeepSeek Chat Completions API）"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com"

    def chat(self, messages: list[dict]) -> dict:
        import httpx, json
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": messages, "temperature": 0.1},
            timeout=60,
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"action": "finish", "reason": "LLM response not JSON"}


def main():
    parser = argparse.ArgumentParser(description="Coding Agent Harness")
    parser.add_argument("--task", type=str, help="任务描述")
    parser.add_argument("--session", type=str, help="会话 ID（恢复历史会话）")
    parser.add_argument("--config", type=str, default="guard_rules.yaml", help="治理规则文件路径")
    parser.add_argument("--mock", action="store_true", help="使用 Mock LLM 模式")
    parser.add_argument("--strict", action="store_true", help="严格模式（WARN 升格为 HITL）")
    parser.add_argument("--max-turns", type=int, default=50, help="最大轮次")
    parser.add_argument("--workspace", type=str, default=".", help="工作目录")
    parser.add_argument("command", nargs="?", choices=["credential"], help="子命令")
    parser.add_argument("subcommand", nargs="?", choices=["set", "status", "clear"], help="credential 子命令")

    args = parser.parse_args()

    if args.command == "credential":
        if args.subcommand == "set":
            cred_set()
        elif args.subcommand == "status":
            print(cred_status())
        elif args.subcommand == "clear":
            cred_clear()
        return

    if not args.task:
        parser.print_help()
        return

    workspace = Path(args.workspace).resolve()
    rules = load_rules(args.config)
    guard = GuardEngine(rules, workspace)
    executor = Executor(workspace)
    feedback = FeedbackEngine()
    io = CliIO()

    if args.mock:
        actions = [
            __import__("src.models").Action(tool="read_file", params={"path": "README.md"}),
        ]
        llm = ScriptedMockLLM(actions)
    else:
        from src.credential import get_key
        import httpx
        key = get_key()
        if not key:
            print("请先配置 API Key: python run_cli.py credential set")
            return
        llm = DeepSeekClient(key)

    session = Session(
        session_id=args.session or "default",
        created_at="", updated_at="",
        task_description=args.task,
        conventions=[], tags=[]
    )

    agent = AgentLoop(
        llm=llm, guard=guard, executor=executor, feedback=feedback,
        session_store=None, io=io,
        strict_mode=args.strict, max_turns=args.max_turns,
    )

    task = Task(description=args.task)
    result = agent.run(task, session)
    print(f"\nStatus: {result.status}")
    print(f"Turns: {len(result.turns)}")

if __name__ == "__main__":
    main()
```

- [x] **Step 3: 写测试**

```python
# tests/test_cli.py
import subprocess
import sys

def test_cli_help_output():
    result = subprocess.run([sys.executable, "run_cli.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--task" in result.stdout

def test_cli_credential_status():
    result = subprocess.run([sys.executable, "run_cli.py", "credential", "status"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "已配置" in result.stdout or "未配置" in result.stdout
```

- [x] **Step 4: 运行验证通过**

```bash
pytest tests/test_cli.py -v
```
Expected: 2 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/io_interface.py run_cli.py tests/test_cli.py
git commit -m "feat(T15): implement CliIO and run_cli.py entry point"
```

---

### Task 16: 机制演示脚本

**目标**：实现 `demo.py`，在 mock LLM 下确定性地复现三项行为。

**Files:**
- Create: `demo.py`

**Interfaces:**
- Consumes: `src.models.*`, `src.guardrail.*`, `src.feedback.*`, `src.harness_core.*`, `src.mock_llm.*`, `src.io_interface.*`
- Produces: `demo.py` 可执行脚本

- [x] **Step 1: 写 `demo.py`**

```python
"""机制演示：在 Mock LLM 下确定性地复现三项行为"""
import sys
from pathlib import Path
from src.models import Action, Task, Session, GuardRule, GuardDecision, Verdict, ToolResult, TaskResult
from src.guardrail import GuardEngine
from src.mock_llm import ScriptedMockLLM
from src.executor import Executor
from src.feedback import FeedbackEngine
from src.harness_core import AgentLoop
from src.io_interface import SilentIO, ApprovalResult

PASSED = 0
FAILED = 0

def check(name, condition):
    global PASSED, FAILED
    if condition:
        print(f"[PASS] {name}")
        PASSED += 1
    else:
        print(f"[FAIL] {name}")
        FAILED += 1

# Demo 1: 治理护栏拦截危险动作
print("=== Demo 1: 治理护栏拦截危险动作 ===")
rules = [
    GuardRule(id="shell-dangerous", action_type="Shell", scope="System",
              risk_level="CRITICAL", verdict="BLOCK", pattern="rm -rf /|shutdown",
              description="禁止执行危险系统命令"),
]
guard = GuardEngine(rules, Path("/tmp/test"))
decision = guard.check(Action(tool="execute_shell", params={"command": "rm -rf /"}))
check("Demo 1: Guardrail blocked 'rm -rf /'", decision.verdict == Ver.BLOCK)

# Demo 2: 反馈闭环驱动修正
print("\n=== Demo 2: 反馈闭环驱动修正 ===")
class FailingThenPassingExec:
    def __init__(self):
        self.count = 0
    def dispatch(self, action, timeout=30):
        self.count += 1
        if self.count == 1:
            return ToolResult(exit_code=1, stderr="AssertionError: test failed")
        return ToolResult(exit_code=0, stdout="all passed")

llm = ScriptedMockLLM([
    Action(tool="run_tests", params={}),
    Action(tool="write_file", params={"path": "fix.py", "content": "fixed"}),
    Action(tool="run_tests", params={}),
])
agent = AgentLoop(
    llm=llm, guard=GuardEngine([], Path("/tmp")),
    executor=FailingThenPassingExec(), feedback=FeedbackEngine(),
    session_store=None, io=SilentIO(), max_turns=10,
)
task = Task(description="fix tests")
session = Session(session_id="demo", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
result = agent.run(task, session)
check("Demo 2: Feedback loop corrected action", result.status == "success" and len(result.turns) == 3)

# Demo 3: 熔断 HITL
print("\n=== Demo 3: 熔断 HITL ===")
class AlwaysFailExec:
    def dispatch(self, action, timeout=30):
        return ToolResult(exit_code=1, stderr="AssertionError: always fails")

llm3 = ScriptedMockLLM([Action(tool="run_tests", params={})] * 5)
agent3 = AgentLoop(
    llm=llm3, guard=GuardEngine([], Path("/tmp")),
    executor=AlwaysFailExec(), feedback=FeedbackEngine(),
    session_store=None, io=SilentIO(), max_turns=10,
)
result3 = agent3.run(task, session)
check("Demo 3: Circuit breaker triggered", result3.status == "circuit_breaker")

print(f"\n{'='*40}")
if FAILED == 0:
    print(f"All {PASSED} demos passed.")
else:
    print(f"{PASSED} passed, {FAILED} failed.")
    sys.exit(1)
```

- [x] **Step 2: 运行验证**

```bash
python demo.py
```
Expected: 输出 3 个 `[PASS]`，最终 `All 3 demos passed.`

- [x] **Step 3: Commit**

```bash
git add demo.py
git commit -m "feat(T16): implement mechanism demo script (AC17)"
```

---

### Task 17: CI 配置

**目标**：创建 `.github/workflows/ci.yml`，包含 `unit-test` job。

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: (none — CI 配置)
- Produces: GitHub Actions workflow

- [x] **Step 1: 创建 `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest -v
```

- [x] **Step 2: 验证**

推送到 GitHub 后，确认 `unit-test` job 自动触发并 PASS。

- [x] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(T17): add GitHub Actions unit-test workflow"
```

---

### Task 18: README + 安装脚本

**目标**：编写 `README.md`（含项目简介、安装、运行、分发命令、目录结构、安全边界说明）+ `install.sh` / `install.ps1`。

**Files:**
- Create: `README.md`
- Create: `install.sh`
- Create: `install.ps1`

**Interfaces:**
- Consumes: (none)
- Produces: 文档和安装脚本

- [x] **Step 1: 创建 `install.sh`**

```bash
#!/bin/bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo ""
echo "Installation complete."
echo "Run 'python run_cli.py credential set' to configure your API key."
echo "Run 'python run_cli.py --help' for usage."
```

- [x] **Step 2: 创建 `install.ps1`**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Write-Host ""
Write-Host "Installation complete."
Write-Host "Run 'python run_cli.py credential set' to configure your API key."
Write-Host "Run 'python run_cli.py --help' for usage."
```

- [x] **Step 3: 创建 `README.md`**

```markdown
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
```

- [x] **Step 4: 验证**

```bash
chmod +x install.sh
bash install.sh
```
Expected: 成功创建 venv 并安装依赖

```bash
python run_cli.py --help
```
Expected: 正常输出帮助信息

- [x] **Step 5: Commit**

```bash
git add README.md install.sh install.ps1
git commit -m "docs(T18): add README, install scripts, and security notes"
```

---

## AC 覆盖映射

| AC | 描述 | 覆盖 Task | 关键路径 |
|----|------|-----------|----------|
| AC1 | 主循环能跑 | T13, T14 | ✓ |
| AC2 | 治理拦截危险 | T07, T10 | ✓ |
| AC3 | 治理放行安全 | T07, T10 | ✓ |
| AC4 | 路径隔离 | T08, T10 | ✓ |
| AC5 | Shell 双重校验 | T09, T10 | ✓ |
| AC6 | 反馈分类 | T12 | ✓ |
| AC7 | 第 3 次熔断 | T12, T14 | ✓ |
| AC8 | 成功重置 | T12 | ✓ |
| AC9 | 类型变化重置 | T12 | ✓ |
| AC10 | 记忆读写 | T06 | 补充 |
| AC11 | 记忆检索 | T06 | 补充 |
| AC12 | 凭据状态 | T05 | 补充 |
| AC13 | 配置加载 | T04 | 补充 |
| AC14 | WARN 自动执行 | T13, T14 | ✓ |
| AC15 | strict 升格 | T13, T14 | ✓ |
| AC16 | HITL 拒绝回灌 | T13, T14 | ✓ |
| AC17 | 机制演示 | T16 | ✓ |
| AC18 | pytest 全绿 | T17 | ✓ |
| AC19 | CI 通过 | T17 | ✓ |
| AC20 | 无凭据提交 | T01, T18 | ✓ |

---

## 实现完成记录

> 所有任务由 Superpowers subagent-driven-development 工作流完成。每项注明 commit hash 及对应的 worktree 分支。

| Task | 描述 | Commit | 分支 | 完成日期 |
|------|------|--------|------|----------|
| T01 | 项目脚手架 + 测试基础设施 | `66fc7c5` | phase1-infra | 2026-08-09 |
| T02 | 数据模型 | `66fc7c5` | phase1-infra | 2026-08-09 |
| T03 | Mock LLM 抽象 | `c70229c` | phase2-base | 2026-08-09 |
| T04 | 配置加载 | `ddd5663` | phase2-base | 2026-08-09 |
| T05 | 凭据管理 | `fb818e6` | phase2-base | 2026-08-09 |
| T06 | 会话存储 | `fb818e6` | phase2-base | 2026-08-09 |
| T07 | GuardEngine 骨架 | `564c6bd` | phase3-governance | 2026-08-09 |
| T08 | 路径隔离 | `62a96f6` | phase3-governance | 2026-08-09 |
| T09 | Shell 双重校验 | `5bf73b6` | phase3-governance | 2026-08-09 |
| T10 | 护栏状态机集成 | `5f9d8b6` | phase3-governance | 2026-08-09 |
| T11 | 工具执行器 | `70a23d4` | phase4-executor | 2026-08-09 |
| T12 | 反馈引擎 | `fd263ea` | phase5-core | 2026-08-09 |
| T13 | AgentLoop 主循环 | `b30308d` | phase5-core | 2026-08-09 |
| T14 | 集成测试 | `b918c21` | phase5-core | 2026-08-09 |
| T15 | CLI 入口 | `38ae1d8` | phase6-io | 2026-08-09 |
| T16 | 机制演示 demo.py | `903447d` | phase6-io | 2026-08-09 |
| T17 | CI 配置 | `903447d` | phase6-io | 2026-08-09 |
| T18 | README + 安装脚本 | `903447d` | phase6-io | 2026-08-09 |

**代码审查后修复（人工修改）：**

| 修复 | Commit | 说明 |
|------|--------|------|
| 反馈上下文注入 LLM | `01550a8` | `context_for_llm` 计算了但未注入 messages |
| YAML 正则转义 | `01550a8` | `guard_rules.yaml` 反斜杠转义错误 |
| Action 导入错误 | `a3d6e59` | BLOCK 拒绝理由未回灌 |
| LINT_ERROR 分类 | `a3d6e59` | 线号格式未匹配 |

**GUI 测试辅助（非作业要求）：**

| 功能 | Commit |
|------|--------|
| GUI 设计文档 | `6df9b1c` |
| GUI 实现 | `e193b51` |
| 会话持久化 | `bc40762` |
| API Key 输入 | `a3f483e` |
| 英语提示词 | `9716974` |
| CLI verbose 模式 | `57b49d8` |
| 参数名兼容 | `91a984c` ~ `9e78601` |
| 重复成功检测 | `1aba491` ~ `7ce2f94` |
| ScenarioMockLLM | `2062295` |
| 治理场景 | `d33e7b8` ~ `d625567` |
| 高级治理任务 (4 个) | `8ef1093` ~ `40d6ec3` |
| 高级鲁棒性任务 (5 个) | `91fea0b` |

**最终测试：87 passed, 2 skipped（零网络依赖）**