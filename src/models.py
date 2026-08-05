from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Tool(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_SHELL = "execute_shell"
    RUN_TESTS = "run_tests"
    RUN_LINT = "run_lint"


class Verdict(Enum):
    SAFE = "SAFE"
    WARN = "WARN"
    BLOCK = "BLOCK"


class FeedbackCategory(Enum):
    SUCCESS = "SUCCESS"
    COMPILE_ERROR = "COMPILE_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    LINT_ERROR = "LINT_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class TaskStatus(Enum):
    SUCCESS = "success"
    ABORTED = "aborted"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class Action:
    tool: str
    params: dict
    reason: str = ""


@dataclass
class ToolResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0


@dataclass
class GuardRule:
    id: str
    action_type: str
    scope: str
    risk_level: str
    verdict: str
    pattern: Optional[str] = None
    description: str = ""


@dataclass
class GuardDecision:
    verdict: Verdict
    matched_rule: str = "default"
    reason: str = ""


@dataclass
class RiskInfo:
    action_summary: str
    verdict: str
    matched_rule: str
    reason: str


@dataclass
class ApprovalResult:
    approved: bool
    reason: str = ""


@dataclass
class FeedbackResult:
    category: str
    round: int
    should_retry: bool
    context_for_llm: str = ""


@dataclass
class Turn:
    turn_number: int
    timestamp: str
    action: Action
    guard_decision: GuardDecision
    approval: Optional[ApprovalResult] = None
    result: Optional[ToolResult] = None
    feedback: Optional[FeedbackResult] = None


@dataclass
class Task:
    description: str
    context: dict = field(default_factory=dict)


@dataclass
class TaskResult:
    status: str
    turns: list = field(default_factory=list)
    summary: str = ""


@dataclass
class Session:
    session_id: str
    created_at: str
    updated_at: str
    task_description: str
    decisions: list = field(default_factory=list)
    conventions: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    summary: str = ""