from src.models import ToolResult, FeedbackResult

class FeedbackEngine:
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._last_category: str | None = None

    def analyze(self, result: ToolResult) -> FeedbackResult:
        if result.exit_code == 0:
            self._counters.clear()
            self._last_category = None
            return FeedbackResult(category="SUCCESS", round=0, should_retry=False)

        category = self._classify(result)
        is_same_category = (category == self._last_category)

        if is_same_category:
            self._counters[category] = self._counters.get(category, 0) + 1
        else:
            self._counters = {category: 1}
            self._last_category = category

        round_num = self._counters[category]
        should_retry = round_num < 3

        if round_num == 1:
            context = f"[{category}]\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        elif round_num == 2:
            lines = result.stderr.strip().split("\n")
            key_lines = [l for l in lines if l.strip()][:5]
            context = f"[{category}] 关键错误:\n" + "\n".join(key_lines)
        else:
            context = f"[{category}] 连续第 {round_num} 次同类失败，已触发熔断"

        return FeedbackResult(category=category, round=round_num, should_retry=should_retry, context_for_llm=context)

    def _classify(self, result: ToolResult) -> str:
        stderr = result.stderr
        if result.exit_code == -1 and "TIMEOUT" in stderr:
            return "TIMEOUT"
        if "SyntaxError" in stderr or "IndentationError" in stderr:
            return "COMPILE_ERROR"
        if "AssertionError" in stderr or "FAILED" in stderr:
            return "TEST_FAILURE"
        if "Traceback" in stderr:
            return "RUNTIME_ERROR"
        if any(code in stderr for code in ("E", "F", "W", "C", "N", "D", "PL", "RUF", "UP", "SIM")):
            import re
            if re.search(r"[A-Z]+\d{3,4}", stderr):
                return "LINT_ERROR"
        if result.exit_code != 0:
            return "UNKNOWN_ERROR"
        return "SUCCESS"