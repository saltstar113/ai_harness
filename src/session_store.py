import json
from dataclasses import asdict
from pathlib import Path

from src.models import Session

STORE_DIR = Path.home() / ".ai_harness" / "sessions"


def _ensure_dir():
    STORE_DIR.mkdir(parents=True, exist_ok=True)


def save_session(session: Session) -> None:
    _ensure_dir()
    data = asdict(session)
    filepath = STORE_DIR / f"{session.session_id}.json"
    filepath.write_text(json.dumps(data, indent=2))


def load_session(session_id: str) -> Session | None:
    _ensure_dir()
    filepath = STORE_DIR / f"{session_id}.json"
    try:
        data = json.loads(filepath.read_text())
        return Session(**data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None


def search_sessions(keywords: list[str]) -> list[Session]:
    _ensure_dir()
    results = []
    patterns = [kw.lower() for kw in keywords]

    for filepath in sorted(STORE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(filepath.read_text())
            session = Session(**data)
        except (json.JSONDecodeError, TypeError):
            continue

        searchable = " ".join(session.tags + [session.task_description]).lower()
        if any(pat in searchable for pat in patterns):
            results.append(session)

        if len(results) >= 5:
            break

    return results