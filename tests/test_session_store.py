import json
from datetime import datetime, timezone

from src.session_store import save_session, load_session, search_sessions, STORE_DIR
from src.models import Session


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)

    session = Session(
        session_id="sess-001",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Refactor the auth module",
        decisions=["use JWT", "expire after 1h"],
        conventions=["PEP8", "type hints"],
        errors=[],
        tags=["refactoring", "auth"],
        summary="Refactored auth module successfully",
    )

    save_session(session)
    loaded = load_session("sess-001")

    assert loaded is not None
    assert loaded.session_id == "sess-001"
    assert loaded.task_description == "Refactor the auth module"
    assert loaded.decisions == ["use JWT", "expire after 1h"]
    assert loaded.conventions == ["PEP8", "type hints"]
    assert loaded.tags == ["refactoring", "auth"]
    assert loaded.summary == "Refactored auth module successfully"
    assert loaded.created_at == "2025-01-15T10:00:00Z"
    assert loaded.updated_at == "2025-01-15T10:30:00Z"


def test_search_by_keyword(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)

    session1 = Session(
        session_id="sess-001",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Refactor the auth module",
        decisions=[],
        conventions=[],
        errors=[],
        tags=["refactoring", "auth"],
        summary="",
    )

    session2 = Session(
        session_id="sess-002",
        created_at="2025-01-15T11:00:00Z",
        updated_at="2025-01-15T11:30:00Z",
        task_description="Add logging to payment module",
        decisions=[],
        conventions=[],
        errors=[],
        tags=["feature", "logging"],
        summary="",
    )

    save_session(session1)
    save_session(session2)

    results = search_sessions(["refactoring"])
    assert len(results) == 1
    assert results[0].session_id == "sess-001"


def test_search_returns_empty_for_no_match(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)

    session = Session(
        session_id="sess-001",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Refactor auth module",
        decisions=[],
        conventions=[],
        errors=[],
        tags=["refactoring"],
        summary="",
    )

    save_session(session)

    results = search_sessions(["nonexistent"])
    assert results == []


def test_load_nonexistent_session_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    result = load_session("nonexistent-id")
    assert result is None


def test_save_session_with_errors(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    session = Session(
        session_id="sess-err",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Buggy task",
        decisions=[],
        conventions=[],
        errors=[{"type": "COMPILE_ERROR", "message": "SyntaxError at line 12"}],
        tags=["bug"],
        summary="",
    )
    save_session(session)
    loaded = load_session("sess-err")
    assert loaded is not None
    assert len(loaded.errors) == 1
    assert loaded.errors[0]["type"] == "COMPILE_ERROR"


def test_save_session_with_conventions_dict(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    session = Session(
        session_id="sess-conv",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Task with conventions",
        decisions=[],
        conventions=[{"key": "indent", "value": "4 spaces"}, {"key": "naming", "value": "snake_case"}],
        errors=[],
        tags=[],
        summary="",
    )
    save_session(session)
    loaded = load_session("sess-conv")
    assert loaded is not None
    assert len(loaded.conventions) == 2
    assert loaded.conventions[0]["key"] == "indent"


def test_search_by_task_description(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    session = Session(
        session_id="sess-desc",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Implement user authentication with JWT",
        decisions=[],
        conventions=[],
        errors=[],
        tags=[],
        summary="",
    )
    save_session(session)
    results = search_sessions(["authentication"])
    assert len(results) == 1
    assert results[0].session_id == "sess-desc"


def test_search_skips_corrupt_json(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    good_session = Session(
        session_id="good",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-15T10:30:00Z",
        task_description="Good session",
        decisions=[],
        conventions=[],
        errors=[],
        tags=["good"],
        summary="",
    )
    save_session(good_session)
    (tmp_path / "corrupt.json").write_text("not valid json {{{")
    results = search_sessions(["good"])
    assert len(results) == 1
    assert results[0].session_id == "good"


def test_search_limited_to_5_results(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    for i in range(7):
        session = Session(
            session_id=f"sess-{i:03d}",
            created_at=f"2025-01-15T1{i}:00:00Z",
            updated_at=f"2025-01-15T1{i}:30:00Z",
            task_description=f"Task number {i}",
            decisions=[],
            conventions=[],
            errors=[],
            tags=["batch"],
            summary="",
        )
        save_session(session)
    results = search_sessions(["batch"])
    assert len(results) == 5


def test_all_fields_preserved_after_save_load(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session_store.STORE_DIR", tmp_path)
    session = Session(
        session_id="full-test",
        created_at="2025-06-01T12:00:00Z",
        updated_at="2025-06-01T13:00:00Z",
        task_description="Full field test",
        decisions=["decision A", "decision B"],
        conventions=[{"key": "k", "value": "v"}],
        errors=[{"type": "TEST_FAILURE", "message": "assert False"}],
        tags=["test", "full"],
        summary="Completed successfully",
    )
    save_session(session)
    loaded = load_session("full-test")
    assert loaded is not None
    assert loaded.session_id == "full-test"
    assert loaded.created_at == "2025-06-01T12:00:00Z"
    assert loaded.updated_at == "2025-06-01T13:00:00Z"
    assert loaded.task_description == "Full field test"
    assert loaded.decisions == ["decision A", "decision B"]
    assert loaded.conventions == [{"key": "k", "value": "v"}]
    assert loaded.errors == [{"type": "TEST_FAILURE", "message": "assert False"}]
    assert loaded.tags == ["test", "full"]
    assert loaded.summary == "Completed successfully"