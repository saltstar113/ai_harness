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