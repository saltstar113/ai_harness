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
    result = executor.dispatch(Action(tool="execute_shell", params={"command": "python -c \"import time; time.sleep(5)\""}), timeout=1)
    assert result.exit_code == -1
    assert "TIMEOUT" in result.stderr


def test_env_scrubbing_removes_api_key(tmp_workspace):
    import os
    os.environ["DEEPSEEK_API_KEY"] = "sk-deadbeef1234567890abcdef"
    try:
        executor = Executor(tmp_workspace)
        result = executor.dispatch(Action(tool="execute_shell", params={"command": "echo %DEEPSEEK_API_KEY%"}))
        assert "sk-deadbeef" not in result.stdout
        assert "sk-deadbeef" not in result.stderr
    finally:
        del os.environ["DEEPSEEK_API_KEY"]


def test_output_scrubbing_masks_key_pattern(tmp_workspace):
    executor = Executor(tmp_workspace)
    result = executor.dispatch(Action(tool="execute_shell", params={"command": "echo sk-abcdef1234567890abcdef1234567890"}))
    assert "***REDACTED***" in result.stdout
    assert "sk-abcdef" not in result.stdout


def test_atomic_write_syntax_error_rollback(tmp_workspace):
    executor = Executor(tmp_workspace)
    target = tmp_workspace / "main.py"
    target.write_text("def valid(): pass")
    result = executor.dispatch(Action(tool="write_file", params={"path": str(target), "content": "def invalid(: pass"}))
    assert result.exit_code != 0
    assert "SYNTAX_ERROR" in result.stderr
    assert target.read_text() == "def valid(): pass"


def test_atomic_write_valid_syntax_succeeds(tmp_workspace):
    executor = Executor(tmp_workspace)
    target = tmp_workspace / "main.py"
    result = executor.dispatch(Action(tool="write_file", params={"path": str(target), "content": "def valid(): pass"}))
    assert result.exit_code == 0
    assert target.read_text() == "def valid(): pass"