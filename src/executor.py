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

    def _read_file(self, params, timeout):
        start = time.time()
        path = Path(params["path"])
        content = path.read_text(encoding="utf-8")
        return ToolResult(stdout=content, exit_code=0, duration_ms=(time.time() - start) * 1000)

    def _write_file(self, params, timeout):
        start = time.time()
        path = Path(params.get("path") or params.get("file_path") or params.get("file"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(params["content"], encoding="utf-8")
        return ToolResult(stdout="OK", exit_code=0, duration_ms=(time.time() - start) * 1000)

    def _execute_shell(self, params, timeout):
        start = time.time()
        try:
            proc = subprocess.run(params["command"], shell=True, timeout=timeout,
                                  capture_output=True, text=True, cwd=str(self.workspace))
            return ToolResult(stdout=proc.stdout, stderr=proc.stderr,
                              exit_code=proc.returncode, duration_ms=(time.time() - start) * 1000)
        except subprocess.TimeoutExpired:
            return ToolResult(exit_code=-1, stderr="TIMEOUT", duration_ms=(time.time() - start) * 1000)

    def _run_tests(self, params, timeout):
        target = params.get("target", "")
        cmd = f"pytest {target} -q" if target else "pytest -q"
        return self._execute_shell({"command": cmd}, timeout)

    def _run_lint(self, params, timeout):
        target = params.get("target", ".")
        cmd = f"ruff check {target}"
        return self._execute_shell({"command": cmd}, timeout)