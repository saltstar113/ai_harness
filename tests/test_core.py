from src.models import Action, Task, Session, GuardDecision, Verdict, ToolResult, FeedbackResult, RiskInfo
from src.mock_llm import ScriptedMockLLM
from src.harness_core import AgentLoop
from src.io_interface import SilentIO, ApprovalResult

class FakeGuard:
    def check(self, action):
        return GuardDecision(verdict=Verdict.SAFE)

class FakeExecutor:
    def dispatch(self, action, timeout=30):
        return ToolResult(exit_code=0, stdout="ok")

class FakeFeedback:
    def analyze(self, result):
        return FeedbackResult(category="SUCCESS", round=0, should_retry=False)

class FakeSessionStore:
    def save_session(self, session): pass
    def search_sessions(self, keywords): return []

def test_agent_loop_completes_with_mock_llm():
    actions = [Action(tool="read_file", params={"path": "test.txt"})]
    llm = ScriptedMockLLM(actions)
    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=FakeExecutor(),
                      feedback=FakeFeedback(), session_store=FakeSessionStore(), max_turns=10)
    task = Task(description="read a file")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 1
    assert result.turns[0].action.tool == "read_file"

def test_agent_loop_stops_on_finish():
    llm = ScriptedMockLLM([])
    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=FakeExecutor(),
                      feedback=FakeFeedback(), session_store=FakeSessionStore(), max_turns=10)
    task = Task(description="do nothing")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 0


class BlockingGuard:
    def check(self, action):
        if action.tool == "execute_shell":
            return GuardDecision(verdict=Verdict.BLOCK, matched_rule="shell-dangerous", reason="危险命令")
        return GuardDecision(verdict=Verdict.SAFE)


class AlwaysFailingExecutor:
    def dispatch(self, action, timeout=30):
        return ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")


class FailingThenPassingExecutor:
    def __init__(self):
        self.call_count = 0

    def dispatch(self, action, timeout=30):
        self.call_count += 1
        if self.call_count == 1:
            return ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")
        return ToolResult(exit_code=0, stdout="ok")


def test_guardrail_block_with_approval_rejected():
    llm = ScriptedMockLLM([Action(tool="execute_shell", params={"command": "rm -rf /"})])
    io = SilentIO(approval_result=ApprovalResult(approved=False, reason="太危险了"))
    agent = AgentLoop(llm=llm, guard=BlockingGuard(), executor=FakeExecutor(),
                      feedback=FakeFeedback(), session_store=FakeSessionStore(), io=io, max_turns=10)
    task = Task(description="delete something")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert len(io.approval_calls) == 1
    assert io.approval_calls[0][1].reason == "危险命令"


def test_circuit_breaker_halts_loop():
    from src.feedback import FeedbackEngine
    llm = ScriptedMockLLM([Action(tool="run_tests", params={})] * 5)
    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=AlwaysFailingExecutor(),
                      feedback=FeedbackEngine(), session_store=FakeSessionStore(), io=SilentIO(), max_turns=10)
    task = Task(description="run tests")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "circuit_breaker"


def test_feedback_loop_retries_on_failure():
    from src.feedback import FeedbackEngine
    llm = ScriptedMockLLM([Action(tool="run_tests", params={}), Action(tool="write_file", params={"path": "fix.py", "content": "fixed"}), Action(tool="run_tests", params={})])
    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=FailingThenPassingExecutor(),
                      feedback=FeedbackEngine(), session_store=FakeSessionStore(), io=SilentIO(), max_turns=10)
    task = Task(description="fix tests")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 3
    assert result.turns[0].feedback.category == "TEST_FAILURE"
    assert result.turns[2].feedback.category == "SUCCESS"