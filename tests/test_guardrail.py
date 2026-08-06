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


def test_path_traversal_blocked(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "secret.txt").write_text("secret")
    engine = GuardEngine([], workspace)
    decision = engine.validate_path(str(tmp_path / "outside" / "secret.txt"))
    assert decision.verdict == Verdict.BLOCK
    assert "路径越界" in decision.reason


def test_path_in_workspace_allowed(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("code")
    engine = GuardEngine([], workspace)
    decision = engine.validate_path(str(workspace / "src" / "main.py"))
    assert decision.verdict == Verdict.SAFE


def test_dot_dot_slash_traversal_blocked(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "src").mkdir()
    engine = GuardEngine([], workspace)
    decision = engine.validate_path(str(workspace / "src" / "../../../etc/passwd"))
    assert decision.verdict == Verdict.BLOCK


def test_sudo_rm_rf_blocked():
    engine = make_engine()
    decision = engine.check_shell_command("sudo rm -rf /")
    assert decision.verdict == Verdict.BLOCK


def test_safe_ls_allowed():
    engine = make_engine()
    decision = engine.check_shell_command("ls -la")
    assert decision.verdict == Verdict.SAFE


def test_shlex_quote_handling():
    engine = make_engine()
    decision = engine.check_shell_command("rm -rf '/etc/passwd'")
    assert decision.verdict == Verdict.BLOCK


def test_env_prefix_rm_blocked():
    engine = make_engine()
    decision = engine.check_shell_command("env rm -rf /")
    assert decision.verdict == Verdict.BLOCK