from pathlib import Path

import pytest

from src.credential import status, clear_key, ENV_FILE, ENV_KEY


def test_status_returns_weipeizhi_when_no_key(monkeypatch, tmp_path):
    temp_env = tmp_path / ".env"
    monkeypatch.setattr("src.credential.ENV_FILE", temp_env)
    assert "未配置" in status()


def test_status_returns_yipeizhi_when_key_set(monkeypatch, tmp_path):
    temp_env = tmp_path / ".env"
    temp_env.write_text("DEEPSEEK_API_KEY=sk-test-123\n")
    monkeypatch.setattr("src.credential.ENV_FILE", temp_env)
    assert "已配置" in status()


def test_status_does_not_leak_key(monkeypatch, tmp_path):
    temp_env = tmp_path / ".env"
    temp_env.write_text("DEEPSEEK_API_KEY=sk-very-secret-key\n")
    monkeypatch.setattr("src.credential.ENV_FILE", temp_env)
    result = status()
    assert "sk-very-secret-key" not in result


def test_clear_key_removes_entry(monkeypatch, tmp_path):
    temp_env = tmp_path / ".env"
    temp_env.write_text("DEEPSEEK_API_KEY=sk-test-123\nOTHER_VAR=keep-me\n")
    monkeypatch.setattr("src.credential.ENV_FILE", temp_env)
    clear_key()
    content = temp_env.read_text()
    assert "DEEPSEEK_API_KEY" not in content
    assert "OTHER_VAR=keep-me" in content