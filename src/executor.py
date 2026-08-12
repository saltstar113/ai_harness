import subprocess
import time
import os
import re
from pathlib import Path
from src.models import Action, ToolResult

SAFE_ENV_PREFIXES = ("PATH", "PYTHON", "HOME", "USER", "USERNAME", "TEMP", "TMP",
                     "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "OS",
                     "LANG", "LC_", "VIRTUAL_ENV", "PWD", "SHELL", "TERM",
                     "HOMEDRIVE", "HOMEPATH", "LOGONSERVER", "COMPUTERNAME",
                     "PROCESSOR_", "NUMBER_OF_PROCESSORS", "PSMODULEPATH",
                     "COMMONPROGRAMFILES", "PROGRAMFILES", "PROGRAMDATA",
                     "PUBLIC", "ALLUSERSPROFILE", "APPDATA", "LOCALAPPDATA",
                     "WINDIR", "WSL", "DOCKER", "DISPLAY", "WAYLAND",
                     "XDG_", "DBUS_", "SSH_", "COLOR", "PROMPT",
                     "CONDA_", "VSCODE", "ELECTRON", "NODE", "NPM")


class Executor:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def _sanitized_env(self) -> dict:
        return {k: v for k, v in os.environ.items()
                if any(k.startswith(p) for p in SAFE_ENV_PREFIXES)}

    def _scrub_output(self, text: str) -> str:
        return re.sub(r'(sk-[a-zA-Z0-9]{20,})', '***REDACTED***', text)

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
        path = self.workspace / params["path"]
        content = path.read_text(encoding="utf-8")
        return ToolResult(stdout=content, exit_code=0, duration_ms=(time.time() - start) * 1000)

    def _write_file(self, params, timeout):
        start = time.time()
        path = self.workspace / (params.get("path") or params.get("file_path") or params.get("file") or params.get("filepath"))
        path.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if path.exists():
            backup = path.read_bytes()
        path.write_text(params["content"], encoding="utf-8")
        if "content" in params:
            try:
                import ast
                ast.parse(params["content"])
            except SyntaxError as e:
                if backup is not None:
                    path.write_bytes(backup)
                return ToolResult(exit_code=1, stderr=f"SYNTAX_ERROR: {e}",
                                  stdout="", duration_ms=(time.time() - start) * 1000)
        return ToolResult(stdout="OK", exit_code=0, duration_ms=(time.time() - start) * 1000)

    def _execute_shell(self, params, timeout):
        start = time.time()
        try:
            proc = subprocess.run(params["command"], shell=True, timeout=timeout,
                                  capture_output=True, text=True, cwd=str(self.workspace),
                                  env=self._sanitized_env())
            return ToolResult(stdout=self._scrub_output(proc.stdout),
                              stderr=self._scrub_output(proc.stderr),
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