import re
import shlex
from pathlib import Path
from src.models import Action, GuardRule, GuardDecision, Verdict

VERDICT_PRIORITY = {Verdict.BLOCK: 3, Verdict.WARN: 2, Verdict.SAFE: 1}


class GuardEngine:
    def __init__(self, rules: list[GuardRule], workspace: Path):
        self.rules = rules
        self.workspace = workspace.resolve()

    def check(self, action: Action) -> GuardDecision:
        action_type = self._classify_action_type(action.tool)

        if action_type == "FileSystem":
            target = action.params.get("path", "")
            if target:
                path_decision = self.validate_path(target)
                if path_decision.verdict == Verdict.BLOCK:
                    return path_decision

        if action_type == "Shell":
            command = action.params.get("command", "")
            if command:
                shell_decision = self.check_shell_command(command)
                if shell_decision.verdict != Verdict.SAFE:
                    return shell_decision

        candidates = [r for r in self.rules if r.action_type == action_type and not r.pattern]
        if not candidates:
            return GuardDecision(verdict=Verdict.SAFE, reason="无匹配规则")

        best = None
        for rule in candidates:
            if best is None or VERDICT_PRIORITY[Verdict(rule.verdict)] > VERDICT_PRIORITY[Verdict(best.verdict)]:
                best = rule

        if best is None:
            return GuardDecision(verdict=Verdict.SAFE, reason="无匹配规则")

        return GuardDecision(
            verdict=Verdict(best.verdict),
            matched_rule=best.id,
            reason=best.description
        )

    def _classify_action_type(self, tool: str) -> str:
        mapping = {
            "read_file": "FileSystem",
            "write_file": "FileSystem",
            "execute_shell": "Shell",
            "run_tests": "Shell",
            "run_lint": "Shell",
        }
        return mapping.get(tool, "Unknown")

    def validate_path(self, target: str) -> GuardDecision:
        target_path = Path(target)
        if not target_path.is_absolute():
            resolved = (self.workspace / target_path).resolve()
        else:
            resolved = target_path.resolve()
        if not resolved.is_relative_to(self.workspace):
            return GuardDecision(
                verdict=Verdict.BLOCK,
                matched_rule="path-boundary",
                reason=f"路径越界：{target} 不在 workspace {self.workspace} 内"
            )
        return GuardDecision(verdict=Verdict.SAFE, matched_rule="default", reason="")

    def check_shell_command(self, command: str) -> GuardDecision:
        normalized = re.sub(r'\$IFS|\$\{IFS\}', ' ', command)
        try:
            tokens = shlex.split(normalized)
        except ValueError:
            return GuardDecision(verdict=Verdict.BLOCK, reason="命令解析失败")

        cmd_name = tokens[0] if tokens else ""

        shell_rules = [r for r in self.rules if r.action_type == "Shell" and r.pattern]
        for rule in shell_rules:
            if re.search(rule.pattern, normalized) or re.fullmatch(rule.pattern, cmd_name):
                return GuardDecision(
                    verdict=Verdict(rule.verdict),
                    matched_rule=rule.id,
                    reason=rule.description
                )

        joined = shlex.join(tokens)
        for rule in shell_rules:
            if re.search(rule.pattern, joined):
                return GuardDecision(
                    verdict=Verdict(rule.verdict),
                    matched_rule=rule.id,
                    reason=rule.description
                )

        return GuardDecision(verdict=Verdict.SAFE, matched_rule="default", reason="")