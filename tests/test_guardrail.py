from pathlib import Path
from src.models import Action, GuardRule, Verdict
from src.guardrail import GuardEngine


def make_engine(rules=None, workspace=None):
    if rules is None:
        rules = [
            GuardRule(
                id="shell-dangerous",
                action_type="Shell",
                scope="System",
                risk_level="CRITICAL",
                verdict="BLOCK",
                pattern="rm -rf /|shutdown|reboot",
                description="禁止执行危险系统命令",
            ),
            GuardRule(
                id="fs-read-safe",
                action_type="FileSystem",
                scope="Workspace",
                risk_level="LOW",
                verdict="SAFE",
                description="允许读取 workspace 内文件",
            ),
            GuardRule(
                id="shell-pip-warn",
                action_type="Shell",
                scope="Workspace",
                risk_level="MEDIUM",
                verdict="WARN",
                pattern="pip install",
                description="pip install 记录警告",
            ),
        ]
    if workspace is None:
        workspace = Path("/tmp/test_workspace")
    return GuardEngine(rules, workspace)


def test_block_dangerous_shell():
    engine = make_engine()
    action = Action(tool="execute_shell", params={"command": "rm -rf /"})
    decision = engine.check(action)
    assert decision.verdict == Verdict.BLOCK
    assert decision.matched_rule == "shell-dangerous"


def test_allow_safe_read():
    engine = make_engine()
    action = Action(tool="read_file", params={"path": "src/main.py"})
    decision = engine.check(action)
    assert decision.verdict == Verdict.SAFE


def test_warn_pip_install():
    engine = make_engine()
    action = Action(tool="execute_shell", params={"command": "pip install pytest"})
    decision = engine.check(action)
    assert decision.verdict == Verdict.WARN


def test_unknown_tool_returns_safe():
    engine = make_engine()
    action = Action(tool="unknown_tool", params={})
    decision = engine.check(action)
    assert decision.verdict == Verdict.SAFE