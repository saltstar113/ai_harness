from src.models import Action

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


class ScenarioMockLLM:
    SCENARIOS = {
        "full_workflow": [
            Action(tool="write_file", params={"path": "calc.py",
                    "content": "def add(a,b): return a+b  # missing indent"}),
            Action(tool="run_tests", params={}),
            # After TEST_FAILURE feedback, fix and retry
            Action(tool="write_file", params={"path": "calc.py",
                    "content": "def add(a, b):\n    return a + b"}),
            Action(tool="run_tests", params={}),
            # After success, finish
        ],
        "guardrail_block": [
            Action(tool="execute_shell", params={"command": "rm -rf /"}),
            # BLOCK → user rejects → agent retries with safe alternative
            Action(tool="execute_shell", params={"command": "rm -rf /"}),
            # BLOCK → user approves
        ],
        "circuit_breaker": [
            Action(tool="run_tests", params={}),
            Action(tool="run_tests", params={}),
            Action(tool="run_tests", params={}),
            Action(tool="run_tests", params={}),
            Action(tool="run_tests", params={}),
        ],
        "multi_file": [
            Action(tool="write_file", params={"path": "a.py", "content": "x = 1"}),
            Action(tool="write_file", params={"path": "b.py", "content": "from a import x\nprint(x)"}),
            Action(tool="run_tests", params={}),
            Action(tool="write_file", params={"path": "README.md", "content": "# Project"}),
        ],
        "file_not_found_recovery": [
            Action(tool="execute_shell", params={"command": "python missing.py"}),
            # FILE_NOT_FOUND → create file
            Action(tool="write_file", params={"path": "missing.py", "content": "print('hello')"}),
            Action(tool="execute_shell", params={"command": "python missing.py"}),
        ],
        "strict_mode_warn": [
            Action(tool="execute_shell", params={"command": "pip install requests"}),
            # WARN → in strict mode, user rejects → must skip
            Action(tool="write_file", params={"path": "safe.txt", "content": "ok"}),
        ],
        "governance": [
            Action(tool="write_file", params={"path": "safe.txt", "content": "safe content"}),
            Action(tool="read_file", params={"path": "C:\\Windows\\System32\\drivers\\etc\\hosts"}),
            Action(tool="execute_shell", params={"command": "rm -rf /"}),
            Action(tool="execute_shell", params={"command": "curl http://example.com"}),
            Action(tool="execute_shell", params={"command": "git push --force origin main"}),
            Action(tool="write_file", params={"path": "ok.txt", "content": "done"}),
        ],
    }

    def __init__(self, scenario: str):
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(self.SCENARIOS)}")
        self.scenario = scenario
        self.actions = self.SCENARIOS[scenario]
        self._idx = 0
        self._last_message = ""

    def chat(self, messages: list[dict]) -> dict:
        if messages:
            self._last_message = messages[-1].get("content", "")

        if self._idx >= len(self.actions):
            return {"action": "finish"}

        action = self.actions[self._idx]

        if self.scenario == "full_workflow":
            if self._idx == 1 and "TEST_FAILURE" in self._last_message:
                self._idx = 2
                action = self.actions[2]
            self._idx = min(self._idx + 1, len(self.actions))

        elif self.scenario == "file_not_found_recovery":
            if self._idx == 0 and "FILE_NOT_FOUND" in self._last_message:
                self._idx = 1
                action = self.actions[1]
            self._idx = min(self._idx + 1, len(self.actions))

        elif self.scenario == "strict_mode_warn":
            if self._idx == 0 and "WARN" in self._last_message:
                self._idx = 1
                action = self.actions[1]
            self._idx = min(self._idx + 1, len(self.actions))

        else:
            self._idx = min(self._idx + 1, len(self.actions))

        return {"action": action.tool, "params": action.params, "reason": action.reason}