"""机制演示：在 Mock LLM 下确定性地复现三项行为"""
import sys
from pathlib import Path
from src.models import Action, Task, Session, GuardRule, Verdict, ToolResult
from src.guardrail import GuardEngine
from src.mock_llm import ScriptedMockLLM
from src.executor import Executor
from src.feedback import FeedbackEngine
from src.harness_core import AgentLoop
from src.io_interface import SilentIO

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

# Demo 1: Guardrail blocks dangerous action
print("=== Demo 1: 治理护栏拦截危险动作 ===")
rules = [GuardRule(id="shell-dangerous", action_type="Shell", scope="System", risk_level="CRITICAL", verdict="BLOCK", pattern="rm -rf /|shutdown", description="禁止执行危险系统命令")]
guard = GuardEngine(rules, Path("/tmp/test"))
decision = guard.check(Action(tool="execute_shell", params={"command": "rm -rf /"}))
check("Demo 1: Guardrail blocked 'rm -rf /'", decision.verdict == Verdict.BLOCK)

# Demo 2: Feedback loop corrects action
print("\n=== Demo 2: 反馈闭环驱动修正 ===")
class FailingThenPassingExec:
    def __init__(self): self.count = 0
    def dispatch(self, action, timeout=30):
        self.count += 1
        if self.count == 1: return ToolResult(exit_code=1, stderr="AssertionError: test failed")
        return ToolResult(exit_code=0, stdout="all passed")

llm = ScriptedMockLLM([Action(tool="run_tests", params={}), Action(tool="write_file", params={"path": "fix.py", "content": "fixed"}), Action(tool="run_tests", params={})])
agent = AgentLoop(llm=llm, guard=GuardEngine([], Path("/tmp")), executor=FailingThenPassingExec(), feedback=FeedbackEngine(), session_store=None, io=SilentIO(), max_turns=10)
task = Task(description="fix tests")
session = Session(session_id="demo", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
result = agent.run(task, session)
check("Demo 2: Feedback loop corrected action", result.status == "success" and len(result.turns) == 3)

# Demo 3: Circuit breaker
print("\n=== Demo 3: 熔断 HITL ===")
class AlwaysFailExec:
    def dispatch(self, action, timeout=30): return ToolResult(exit_code=1, stderr="AssertionError: always fails")
llm3 = ScriptedMockLLM([Action(tool="run_tests", params={})] * 5)
agent3 = AgentLoop(llm=llm3, guard=GuardEngine([], Path("/tmp")), executor=AlwaysFailExec(), feedback=FeedbackEngine(), session_store=None, io=SilentIO(), max_turns=10)
result3 = agent3.run(task, session)
check("Demo 3: Circuit breaker triggered", result3.status == "circuit_breaker")

print(f"\n{'='*40}")
if FAILED == 0:
    print(f"All {PASSED} demos passed.")
else:
    print(f"{PASSED} passed, {FAILED} failed.")
    sys.exit(1)