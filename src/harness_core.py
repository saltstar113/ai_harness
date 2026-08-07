from datetime import datetime, timezone
from src.models import Action, Task, TaskResult, Session, Turn, Verdict, RiskInfo, ApprovalResult

class AgentLoop:
    def __init__(self, llm, guard, executor, feedback, session_store,
                 io=None, strict_mode: bool = False, max_turns: int = 50):
        self.llm = llm
        self.guard = guard
        self.executor = executor
        self.feedback = feedback
        self.session_store = session_store
        self.io = io
        self.strict_mode = strict_mode
        self.max_turns = max_turns

    def run(self, task: Task, session: Session) -> TaskResult:
        turns = []
        system_prompt = self._build_system_prompt(session)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.description},
        ]
        for turn_num in range(1, self.max_turns + 1):
            llm_response = self.llm.chat(messages)
            if llm_response.get("action") == "finish":
                break
            action = self._parse_action(llm_response)
            if action is None:
                continue
            guard_decision = self.guard.check(action)
            approval = None
            if guard_decision.verdict == Verdict.BLOCK:
                if self.io is not None:
                    risk = RiskInfo(action_summary=f"{action.tool}({action.params})",
                                    verdict=str(guard_decision.verdict),
                                    matched_rule=guard_decision.matched_rule,
                                    reason=guard_decision.reason)
                    approval = self.io.request_approval(action, risk)
                    if not approval.approved:
                        messages.append({"role": "user", "content": f"动作被拒绝：{approval.reason}。请提供替代方案。"})
                        continue
            elif guard_decision.verdict == Verdict.WARN:
                if self.io is not None:
                    self.io.output(f"[WARN] {action.tool}: {guard_decision.reason}")
                if self.strict_mode and self.io is not None:
                    risk = RiskInfo(action_summary=f"{action.tool}({action.params})",
                                    verdict=str(guard_decision.verdict),
                                    matched_rule=guard_decision.matched_rule,
                                    reason=guard_decision.reason)
                    approval = self.io.request_approval(action, risk)
                    if not approval.approved:
                        continue
            result = self.executor.dispatch(action)
            fb = self.feedback.analyze(result)
            turn = Turn(turn_number=turn_num, timestamp=datetime.now(timezone.utc).isoformat(),
                        action=action, guard_decision=guard_decision, approval=approval,
                        result=result, feedback=fb)
            turns.append(turn)
            if fb.context_for_llm:
                messages.append({"role": "user", "content": fb.context_for_llm})
            if not fb.should_retry and fb.category != "SUCCESS":
                return TaskResult(status="circuit_breaker", turns=turns, summary=f"熔断于第 {turn_num} 轮")
        return TaskResult(status="success", turns=turns)

    def _build_system_prompt(self, session: Session) -> str:
        conventions = "\n".join(f"- {c['key']}: {c['value']}" for c in session.conventions)
        return (f"你是一个 coding agent。可用工具：read_file, write_file, execute_shell, run_tests, run_lint。\n"
                f"项目约定：\n{conventions or '无'}\n"
                '返回 JSON 格式：{"action": "tool_name", "params": {...}, "reason": "..."}\n'
                '任务完成时返回：{"action": "finish"}')

    def _parse_action(self, response: dict) -> Action | None:
        tool = response.get("action")
        if not tool or tool == "finish":
            return None
        return Action(tool=tool, params=response.get("params", {}), reason=response.get("reason", ""))