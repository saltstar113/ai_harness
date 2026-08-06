import tempfile
import os
from pathlib import Path

import pytest

from src.config import load_rules, GuardRule


def test_load_default_rules_when_file_missing():
    rules = load_rules("nonexistent_config.yaml")
    assert len(rules) >= 5
    rule_ids = [r.id for r in rules]
    assert "fs-delete-system" in rule_ids
    assert "shell-dangerous" in rule_ids
    assert "shell-sudo-rm" in rule_ids
    assert "network-outbound" in rule_ids
    assert "git-force-push" in rule_ids


def test_load_custom_rules():
    yaml_content = """
rules:
  - id: custom-rule-1
    action_type: Shell
    scope: All
    risk_level: HIGH
    verdict: BLOCK
    pattern: "rm -rf /"
    description: "Custom rule"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        rules = load_rules(tmp_path)
        assert len(rules) == 1
        assert rules[0].id == "custom-rule-1"
        assert rules[0].verdict == "BLOCK"
    finally:
        os.unlink(tmp_path)

    # Test empty rules list falls back to BUILTIN_RULES
    yaml_empty = "rules: []"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_empty)
        tmp_path = f.name

    try:
        rules = load_rules(tmp_path)
        assert len(rules) >= 5
    finally:
        os.unlink(tmp_path)


def test_load_rules_returns_guard_rule_objects():
    yaml_content = """
rules:
  - id: rule-a
    action_type: Shell
    scope: System
    risk_level: CRITICAL
    verdict: BLOCK
    pattern: "pattern-a"
    description: "Rule A"
  - id: rule-b
    action_type: Filesystem
    scope: Workspace
    risk_level: MEDIUM
    verdict: WARN
    pattern: "pattern-b"
    description: "Rule B"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        rules = load_rules(tmp_path)
        assert len(rules) == 2
        for rule in rules:
            assert isinstance(rule, GuardRule)
            assert hasattr(rule, "id")
            assert hasattr(rule, "action_type")
            assert hasattr(rule, "verdict")
            assert hasattr(rule, "scope")
            assert hasattr(rule, "risk_level")
            assert hasattr(rule, "pattern")
            assert hasattr(rule, "description")
    finally:
        os.unlink(tmp_path)