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