from src.models import ToolResult
from src.feedback import FeedbackEngine

def test_classify_test_failure():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=1, stderr="AssertionError: assert 1 == 2")
    fb = engine.analyze(result)
    assert fb.category == "TEST_FAILURE"
    assert fb.round == 1
    assert fb.should_retry is True

def test_classify_success():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=0, stdout="all passed")
    fb = engine.analyze(result)
    assert fb.category == "SUCCESS"
    assert fb.should_retry is False

def test_success_resets_counter():
    engine = FeedbackEngine()
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    engine.analyze(ToolResult(exit_code=0))
    fb = engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    assert fb.round == 1

def test_category_change_resets_counter():
    engine = FeedbackEngine()
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    fb = engine.analyze(ToolResult(exit_code=1, stderr="SyntaxError: invalid syntax"))
    assert fb.round == 1
    assert fb.category == "COMPILE_ERROR"

def test_circuit_breaker_round_3():
    engine = FeedbackEngine()
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    fb = engine.analyze(ToolResult(exit_code=1, stderr="AssertionError"))
    assert fb.round == 3
    assert fb.should_retry is False

def test_classify_timeout():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=-1, stderr="TIMEOUT")
    fb = engine.analyze(result)
    assert fb.category == "TIMEOUT"

def test_classify_runtime_error():
    engine = FeedbackEngine()
    result = ToolResult(exit_code=1, stderr="Traceback (most recent call last):\nTypeError: ...")
    fb = engine.analyze(result)
    assert fb.category == "RUNTIME_ERROR"