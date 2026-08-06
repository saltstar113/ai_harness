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
    result = executor.dispatch(Action(tool="execute_shell", params={"command": "ping -n 6 127.0.0.1"}), timeout=1)
    assert result.exit_code == -1
    assert "TIMEOUT" in result.stderr