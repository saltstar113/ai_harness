import re
from pathlib import Path
from src.models import Action, GuardRule, GuardDecision, Verdict

VERDICT_PRIORITY = {Verdict.BLOCK: 3, Verdict.WARN: 2, Verdict.SAFE: 1}


class GuardEngine:
    def __init__(self, rules: list[GuardRule], workspace: Path):
        self.rules = rules
        self.workspace = workspace.resolve()

    def check(self, action: Action) -> GuardDecision:
        action_type = self._classify_action_type(action.tool)
        candidates = [r for r in self.rules if r.action_type == action_type]
        if not candidates:
            return GuardDecision(verdict=Verdict.SAFE, reason="无匹配规则")

        best = None
        for rule in candidates:
            if rule.pattern:
                cmd = action.params.get("command", "") or action.params.get("path", "")
                if re.search(rule.pattern, cmd):
                    if best is None or VERDICT_PRIORITY[Verdict(rule.verdict)] > VERDICT_PRIORITY[Verdict(best.verdict)]:
                        best = rule
            else:
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
        resolved = Path(target).resolve()
        if not resolved.is_relative_to(self.workspace):
            return GuardDecision(
                verdict=Verdict.BLOCK,
                matched_rule="path-boundary",
                reason=f"路径越界：{target} 不在 workspace {self.workspace} 内"
            )
        return GuardDecision(verdict=Verdict.SAFE, matched_rule="default", reason="")