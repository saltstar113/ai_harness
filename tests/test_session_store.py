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