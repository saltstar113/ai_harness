from src.models import Action, ToolResult, GuardDecision, Verdict, FeedbackResult, FeedbackCategory, Turn, Task, TaskResult, Session


def test_action_creation():
    action = Action(tool="read_file", params={"path": "foo.py"}, reason="read")
    assert action.tool == "read_file"
    assert action.params == {"path": "foo.py"}


def test_tool_result_defaults():
    result = ToolResult()
    assert result.exit_code == 0
    assert result.stdout == ""


def test_guard_decision_enum():
    decision = GuardDecision(verdict=Verdict.BLOCK, matched_rule="shell-dangerous", reason="dangerous")
    assert decision.verdict == Verdict.BLOCK


def test_feedback_result():
    fb = FeedbackResult(category="TEST_FAILURE", round=1, should_retry=True, context_for_llm="error details")
    assert fb.category == "TEST_FAILURE"
    assert fb.round == 1
    assert fb.should_retry is True


def test_turn_optional_fields():
    action = Action(tool="read_file", params={"path": "test.py"})
    guard = GuardDecision(verdict=Verdict.SAFE)
    turn = Turn(turn_number=1, timestamp="2026-01-01T00:00:00Z", action=action, guard_decision=guard)
    assert turn.approval is None
    assert turn.result is None
    assert turn.feedback is None


def test_task_result_defaults():
    result = TaskResult(status="success")
    assert result.turns == []
    assert result.summary == ""


def test_session_creation():
    session = Session(
        session_id="abc-123",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        task_description="test",
        conventions=[{"key": "framework", "value": "pytest"}],
        tags=["testing"],
    )
    assert session.session_id == "abc-123"
    assert len(session.conventions) == 1
    assert session.decisions == []