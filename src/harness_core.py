from datetime import datetime, timezone
from src.models import Action, Task, TaskResult, Session, Turn, Verdict, RiskInfo, ApprovalResult
from src.session_store import load_session, save_session

class AgentLoop:
    def __init__(self, llm, guard, executor, feedback, session_store,
                 io=None, strict_mode: bool = False, max_turns: int = 50,
                 turn_callback=None):
        self.llm = llm
        self.guard = guard
        self.executor = executor
        self.feedback = feedback
        self.session_store = session_store
        self.io = io
        self.strict_mode = strict_mode
        self.max_turns = max_turns
        self.turn_callback = turn_callback

    def run(self, task: Task, session: Session) -> TaskResult:
        turns = []
        existing = load_session(session.session_id)
        if existing and existing.conventions:
            session.conventions = existing.conventions
        system_prompt = self._build_system_prompt(session)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.description},
        ]
        for turn_num in range(1, self.max_turns + 1):
            llm_response = self.llm.chat(messages)
            if llm_response.get("action") == "finish":
                break
            if llm_response.get("action") == "invalid_json":
                raw = llm_response.get("raw", "")
                messages.append({"role": "user", "content": f"Your response was not valid JSON. Raw: {raw}\nPlease respond with ONLY valid JSON: {{\"action\": \"...\", \"params\": {{...}}, \"reason\": \"...\"}}"})
                continue
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
            if self.turn_callback:
                self.turn_callback(turn)
            session.updated_at = datetime.now(timezone.utc).isoformat()
            save_session(session)
            if fb.context_for_llm:
                messages.append({"role": "user", "content": fb.context_for_llm})
            if not fb.should_retry and fb.category != "SUCCESS":
                return TaskResult(status="circuit_breaker", turns=turns, summary=f"熔断于第 {turn_num} 轮")
        return TaskResult(status="success", turns=turns)

    def _build_system_prompt(self, session: Session) -> str:
        conventions = "\n".join(f"- {c['key']}: {c['value']}" for c in session.conventions)
        return (f"You are a coding agent. Available tools: read_file, write_file, execute_shell, run_tests, run_lint.\n"
                f"Project conventions:\n{conventions or 'None'}\n"
                'RULES:\n'
                '- Use write_file to CREATE files BEFORE trying to execute or read them.\n'
                '- When you get an error feedback, read it carefully and adapt your next action.\n'
                '- Do NOT repeat the same failing action more than twice.\n'
                'You MUST respond with ONLY valid JSON, no extra text:\n'
                '{"action": "tool_name", "params": {"key": "value"}, "reason": "why you chose this action"}\n'
                'When task is complete: {"action": "finish"}\n'
                'Do NOT include markdown, backticks, or any text outside the JSON object.')

    def _parse_action(self, response: dict) -> Action | None:
        tool = response.get("action")
        if not tool or tool == "finish":
            return None
        return Action(tool=tool, params=response.get("params", {}), reason=response.get("reason", ""))