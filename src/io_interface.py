from typing import Protocol
from src.models import Action, RiskInfo, ApprovalResult


class IOInterface(Protocol):
    def output(self, message: str) -> None: ...
    def input(self, prompt: str) -> str: ...
    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult: ...


class SilentIO:
    def __init__(self, approval_result: ApprovalResult | None = None):
        self.approval_result = approval_result or ApprovalResult(approved=True)
        self.outputs: list[str] = []
        self.approval_calls: list[tuple] = []

    def output(self, message: str) -> None:
        self.outputs.append(message)

    def input(self, prompt: str) -> str:
        return ""

    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult:
        self.approval_calls.append((action, risk))
        return self.approval_result


class CliIO:
    def output(self, message: str) -> None:
        print(message)

    def input(self, prompt: str) -> str:
        return input(prompt)

    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult:
        print(f"\n{'='*50}")
        print(f"危险动作需要审批")
        print(f"动作: {action.tool}({action.params})")
        print(f"风险等级: {risk.verdict}")
        print(f"命中规则: {risk.matched_rule}")
        print(f"原因: {risk.reason}")
        print(f"{'='*50}")
        choice = input("批准执行? [Y]批准 / [N]拒绝: ").strip().upper()
        if choice == "Y":
            return ApprovalResult(approved=True)
        reason = input("拒绝理由（将回灌给 LLM，回车跳过）: ").strip()
        return ApprovalResult(approved=False, reason=reason)