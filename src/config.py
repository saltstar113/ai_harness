from pathlib import Path

import yaml

from src.models import GuardRule

BUILTIN_RULES = [
    GuardRule(
        id="fs-delete-system",
        action_type="Filesystem",
        scope="System",
        risk_level="CRITICAL",
        verdict="BLOCK",
        pattern="C:\\\\Windows\\\\|/etc/|/boot/|/usr/",
        description="禁止删除系统目录文件",
    ),
    GuardRule(
        id="shell-dangerous",
        action_type="Shell",
        scope="System",
        risk_level="CRITICAL",
        verdict="BLOCK",
        pattern="rm -rf /|shutdown|reboot|mkfs",
        description="禁止执行危险系统命令",
    ),
    GuardRule(
        id="shell-sudo-rm",
        action_type="Shell",
        scope="System",
        risk_level="CRITICAL",
        verdict="BLOCK",
        pattern="sudo rm|sudo del",
        description="禁止sudo删除操作",
    ),
    GuardRule(
        id="network-outbound",
        action_type="Shell",
        scope="Network",
        risk_level="HIGH",
        verdict="WARN",
        pattern="curl|wget|nc |netcat",
        description="警告外网连接操作",
    ),
    GuardRule(
        id="git-force-push",
        action_type="Shell",
        scope="Git",
        risk_level="HIGH",
        verdict="BLOCK",
        pattern="git push.*--force|git push.*-f",
        description="禁止强制推送代码",
    ),
]


def load_rules(path: str) -> list[GuardRule]:
    filepath = Path(path)

    if not filepath.exists():
        return BUILTIN_RULES

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not data.get("rules"):
        return BUILTIN_RULES

    rules = []
    for rule_data in data["rules"]:
        rules.append(
            GuardRule(
                id=rule_data["id"],
                action_type=rule_data["action_type"],
                scope=rule_data["scope"],
                risk_level=rule_data["risk_level"],
                verdict=rule_data["verdict"],
                pattern=rule_data.get("pattern"),
                description=rule_data.get("description", ""),
            )
        )

    return rules if rules else BUILTIN_RULES