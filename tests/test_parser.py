from run_cli import DeepSeekClient


def test_parse_clean_json():
    result = DeepSeekClient._parse_json('{"action": "read_file", "params": {"path": "test.txt"}}')
    assert result is not None
    assert result["action"] == "read_file"


def test_parse_json_in_markdown_block():
    result = DeepSeekClient._parse_json('```json\n{"action": "write_file", "params": {"path": "x.py"}}\n```')
    assert result is not None
    assert result["action"] == "write_file"


def test_parse_json_with_trailing_comma():
    result = DeepSeekClient._parse_json('{"action": "read_file", "params": {"path": "test.txt"},}')
    assert result is not None
    assert result["action"] == "read_file"


def test_parse_json_with_extra_text():
    result = DeepSeekClient._parse_json('Here is the action:\n{"action": "finish"}')
    assert result is not None
    assert result["action"] == "finish"


def test_parse_json_empty():
    result = DeepSeekClient._parse_json("not json at all")
    assert result is None


def test_parse_json_backtick_block():
    result = DeepSeekClient._parse_json('```\n{"action": "execute_shell", "params": {"command": "ls"}}\n```')
    assert result is not None
    assert result["action"] == "execute_shell"