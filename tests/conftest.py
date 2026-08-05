import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_action():
    from src.models import Action
    return Action(tool="read_file", params={"path": "test.py"}, reason="read test file")


@pytest.fixture
def sample_session():
    from src.models import Session
    return Session(
        session_id="test-session-001",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        task_description="test task",
        conventions=[{"key": "test_framework", "value": "pytest"}],
        tags=["test"],
    )