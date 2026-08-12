import argparse
from pathlib import Path
from src.models import Task, Session, Action
from src.config import load_rules
from src.guardrail import GuardEngine
from src.executor import Executor
from src.feedback import FeedbackEngine
from src.harness_core import AgentLoop
from src.io_interface import CliIO
from src.mock_llm import ScriptedMockLLM
from src.credential import status as cred_status, set_key as cred_set, clear_key as cred_clear


class DeepSeekClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com"

    def chat(self, messages: list[dict]) -> dict:
        import httpx, json
        resp = httpx.post(f"{self.base_url}/chat/completions",
                          headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                          json={"model": "deepseek-chat", "messages": messages, "temperature": 0.0}, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"action": "invalid_json", "raw": content[:300]}


def main():
    parser = argparse.ArgumentParser(description="Coding Agent Harness")
    parser.add_argument("--task", type=str, help="任务描述")
    parser.add_argument("--session", type=str, help="会话 ID")
    parser.add_argument("--config", type=str, default="guard_rules.yaml", help="治理规则文件路径")
    parser.add_argument("--mock", action="store_true", help="使用 Mock LLM 模式")
    parser.add_argument("--strict", action="store_true", help="严格模式")
    parser.add_argument("--max-turns", type=int, default=50, help="最大轮次")
    parser.add_argument("--workspace", type=str, default=".", help="工作目录")
    parser.add_argument("--verbose", action="store_true", help="显示每轮详情")
    parser.add_argument("command", nargs="?", choices=["credential"], help="子命令")
    parser.add_argument("subcommand", nargs="?", choices=["set", "status", "clear"], help="credential 子命令")
    args = parser.parse_args()

    if args.command == "credential":
        if args.subcommand == "set":
            cred_set()
        elif args.subcommand == "status":
            print(cred_status())
        elif args.subcommand == "clear":
            cred_clear()
        return

    if not args.task:
        parser.print_help()
        return

    workspace = Path(args.workspace).resolve()
    rules = load_rules(args.config)
    guard = GuardEngine(rules, workspace)
    executor = Executor(workspace)
    feedback = FeedbackEngine()
    io = CliIO()

    if args.mock:
        llm = ScriptedMockLLM([Action(tool="read_file", params={"path": "README.md"})])
    else:
        from src.credential import get_key
        key = get_key()
        if not key:
            print("请先配置 API Key: python run_cli.py credential set")
            return
        llm = DeepSeekClient(key)

    session = Session(session_id=args.session or "default", created_at="", updated_at="",
                      task_description=args.task, conventions=[], tags=[args.task])

    if args.verbose:
        def print_turn(turn):
            print(f"\n--- Turn {turn.turn_number} ---")
            print(f"Action: {turn.action.tool}({turn.action.params})")
            if turn.action.reason:
                print(f"Reason: {turn.action.reason}")
            print(f"Guard: {turn.guard_decision.verdict}")
            if turn.result:
                out = (turn.result.stdout or turn.result.stderr or "")[:200]
                print(f"Result: {out}")
            if turn.feedback:
                print(f"Feedback: {turn.feedback.category}")
    else:
        def print_turn(turn): pass

    agent = AgentLoop(llm=llm, guard=guard, executor=executor, feedback=feedback,
                      session_store=None, io=io, strict_mode=args.strict, max_turns=args.max_turns,
                      turn_callback=print_turn)
    task = Task(description=args.task)
    result = agent.run(task, session)
    print(f"\nStatus: {result.status}")
    print(f"Turns: {len(result.turns)}")


if __name__ == "__main__":
    main()