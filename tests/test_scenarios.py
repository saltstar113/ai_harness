from src.models import Action, Task, Session, GuardDecision, Verdict, ToolResult, FeedbackResult, ApprovalResult
from src.mock_llm import ScenarioMockLLM, ScriptedMockLLM
from src.harness_core import AgentLoop
from src.io_interface import SilentIO


class FakeGuard:
    def check(self, action):
        return GuardDecision(verdict=Verdict.SAFE)


class GuardrailGuard:
    def check(self, action):
        if action.tool == "execute_shell" and "rm -rf" in str(action.params):
            return GuardDecision(verdict=Verdict.BLOCK, matched_rule="shell-dangerous", reason="危险命令")
        return GuardDecision(verdict=Verdict.SAFE)


class WarnGuard:
    def check(self, action):
        if "pip install" in str(action.params):
            return GuardDecision(verdict=Verdict.WARN, matched_rule="pip-install", reason="network call")
        return GuardDecision(verdict=Verdict.SAFE)


class FakeExecutor:
    def dispatch(self, action, timeout=30):
        return ToolResult(exit_code=0, stdout="ok")


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


class FakeFeedback:
    def analyze(self, result, action_desc=""):
        return FeedbackResult(category="SUCCESS", round=0, should_retry=False)


class FakeSessionStore:
    def save_session(self, session): pass
    def search_sessions(self, keywords): return []


def test_scenario_full_workflow():
    llm = ScenarioMockLLM("full_workflow")
    from src.feedback import FeedbackEngine

    class FailingTestThenPass:
        def __init__(self):
            self.call_count = 0
        def dispatch(self, action, timeout=30):
            self.call_count += 1
            if action.tool == "write_file":
                return ToolResult(exit_code=0, stdout="ok")
            if self.call_count <= 3:
                return ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")
            return ToolResult(exit_code=0, stdout="ok")

    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=FailingTestThenPass(),
                      feedback=FeedbackEngine(), session_store=FakeSessionStore(), io=SilentIO(), max_turns=10)
    task = Task(description="build calculator")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    turns = result.turns
    assert len(turns) == 4
    assert turns[0].action.tool == "write_file"
    assert turns[0].feedback.category == "SUCCESS"
    assert turns[1].action.tool == "run_tests"
    assert turns[1].feedback.category == "TEST_FAILURE"
    assert turns[2].action.tool == "write_file"
    assert turns[2].feedback.category == "SUCCESS"
    assert turns[3].action.tool == "run_tests"
    assert turns[3].feedback.category == "SUCCESS"


def test_scenario_guardrail_block():
    io = SilentIO(approval_result=ApprovalResult(approved=False, reason="too dangerous"))
    llm = ScenarioMockLLM("guardrail_block")
    agent = AgentLoop(llm=llm, guard=GuardrailGuard(), executor=FakeExecutor(),
                      feedback=FakeFeedback(), session_store=FakeSessionStore(), io=io, max_turns=10)
    task = Task(description="delete files")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert len(io.approval_calls) == 2
    for action, risk in io.approval_calls:
        assert action.tool == "execute_shell"


def test_scenario_circuit_breaker():
    from src.feedback import FeedbackEngine
    llm = ScenarioMockLLM("circuit_breaker")
    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=AlwaysFailingExecutor(),
                      feedback=FeedbackEngine(), session_store=FakeSessionStore(), io=SilentIO(), max_turns=10)
    task = Task(description="run tests")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "circuit_breaker"


def test_scenario_multi_file():
    from src.feedback import FeedbackEngine
    llm = ScenarioMockLLM("multi_file")
    agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=FakeExecutor(),
                      feedback=FeedbackEngine(), session_store=FakeSessionStore(), io=SilentIO(), max_turns=10)
    task = Task(description="create multi-file project")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 4
    assert result.turns[0].action.tool == "write_file"
    assert result.turns[1].action.tool == "write_file"
    assert result.turns[2].action.tool == "run_tests"
    assert result.turns[3].action.tool == "write_file"


def test_scenario_file_not_found():
    from src.feedback import FeedbackEngine
    from src.executor import Executor
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        llm = ScenarioMockLLM("file_not_found_recovery")
        executor = Executor(Path(tmp))
        agent = AgentLoop(llm=llm, guard=FakeGuard(), executor=executor,
                          feedback=FeedbackEngine(), session_store=FakeSessionStore(), io=SilentIO(), max_turns=10)
        task = Task(description="run missing script")
        session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
        result = agent.run(task, session)
        assert result.status == "success"
        turns = result.turns
        assert len(turns) == 3
        assert turns[0].feedback.category == "FILE_NOT_FOUND"
        assert turns[1].action.tool == "write_file"
        assert turns[1].feedback.category == "SUCCESS"
        assert turns[2].action.tool == "execute_shell"
        assert turns[2].feedback.category == "SUCCESS"
        assert (Path(tmp) / "missing.py").exists()


def test_scenario_strict_mode_warn():
    io = SilentIO(approval_result=ApprovalResult(approved=False, reason="no network"))
    llm = ScenarioMockLLM("strict_mode_warn")
    agent = AgentLoop(llm=llm, guard=WarnGuard(), executor=FakeExecutor(),
                      feedback=FakeFeedback(), session_store=FakeSessionStore(), io=io, strict_mode=True, max_turns=10)
    task = Task(description="install package")
    session = Session(session_id="s1", created_at="", updated_at="", task_description="test", conventions=[], tags=[])
    result = agent.run(task, session)
    assert result.status == "success"
    assert len(result.turns) == 1
    assert result.turns[0].action.tool == "write_file"


def test_scripted_mock_llm_still_works():
    actions = [Action(tool="read_file", params={"path": "test.txt"})]
    llm = ScriptedMockLLM(actions)
    result = llm.chat([])
    assert result["action"] == "read_file"