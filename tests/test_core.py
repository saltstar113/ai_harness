from src.models import Action, Task, Session, GuardDecision, Verdict, ToolResult, FeedbackResult
from src.mock_llm import ScriptedMockLLM
from src.harness_core import AgentLoop

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