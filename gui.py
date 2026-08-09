import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
from datetime import datetime, timezone
from pathlib import Path

from src.models import Action, Task, Session, Turn, Verdict, RiskInfo, ApprovalResult
from src.config import load_rules
from src.guardrail import GuardEngine
from src.executor import Executor
from src.feedback import FeedbackEngine
from src.harness_core import AgentLoop
from src.io_interface import IOInterface
from src.mock_llm import ScriptedMockLLM


class GuiIO(IOInterface):
    def __init__(self, gui):
        self.gui = gui
        self._event = threading.Event()
        self._result = None

    def output(self, message: str):
        self.gui._queue.put(("log", message))

    def request_approval(self, action: Action, risk: RiskInfo) -> ApprovalResult:
        self._event.clear()
        self._result = None
        self.gui._queue.put(("approval", action, risk))
        self._event.wait()
        return self._result

    def resolve_approval(self, approved: bool, reason: str = ""):
        self._result = ApprovalResult(approved=approved, reason=reason)
        self._event.set()


class HarnessGUI:
    COLORS = {
        "SAFE": ("#4CAF50", "white"),
        "WARN": ("#FF9800", "black"),
        "BLOCK": ("#F44336", "white"),
        "SUCCESS": "#4CAF50",
        "ERROR": "#F44336",
        "bg": "#1e1e1e",
        "fg": "#d4d4d4",
        "frame_bg": "#2d2d2d",
        "input_bg": "#3c3c3c",
        "button_bg": "#0e639c",
        "button_fg": "white",
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Coding Agent Harness")
        self.root.geometry("900x700")
        self.root.configure(bg=self.COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._queue = queue.Queue()
        self._running = False
        self._thread = None
        self._io = GuiIO(self)
        self._pending_approval = None

        self._build_control_panel()
        self._build_turn_area()
        self._build_status_bar()

        self._poll_queue()

    def _build_control_panel(self):
        frame = tk.Frame(self.root, bg=self.COLORS["bg"], padx=10, pady=10)
        frame.pack(fill=tk.X)

        tk.Label(frame, text="Task:", fg=self.COLORS["fg"], bg=self.COLORS["bg"],
                 font=("Consolas", 11)).pack(side=tk.LEFT, padx=(0, 5))

        self.task_entry = tk.Entry(frame, width=50, font=("Consolas", 11),
                                   bg=self.COLORS["input_bg"], fg=self.COLORS["fg"],
                                   insertbackground=self.COLORS["fg"], relief=tk.FLAT)
        self.task_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.task_entry.insert(0, "Create a hello.py file that prints 'Hello World'")

        self.run_btn = tk.Button(frame, text="Run", command=self._start_agent,
                                 bg=self.COLORS["button_bg"], fg=self.COLORS["button_fg"],
                                 font=("Consolas", 10, "bold"), relief=tk.FLAT,
                                 padx=15, pady=2)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 20))

        self.mode_var = tk.StringVar(value="mock")
        tk.Radiobutton(frame, text="Mock", variable=self.mode_var, value="mock",
                       bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                       selectcolor=self.COLORS["bg"], activebackground=self.COLORS["bg"],
                       activeforeground=self.COLORS["fg"], font=("Consolas", 10)).pack(side=tk.LEFT)
        tk.Radiobutton(frame, text="API", variable=self.mode_var, value="api",
                       bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                       selectcolor=self.COLORS["bg"], activebackground=self.COLORS["bg"],
                       activeforeground=self.COLORS["fg"], font=("Consolas", 10)).pack(side=tk.LEFT)

        tk.Label(frame, text="  Max Turns:", fg=self.COLORS["fg"], bg=self.COLORS["bg"],
                 font=("Consolas", 10)).pack(side=tk.LEFT)
        self.max_turns_var = tk.StringVar(value="50")
        tk.Spinbox(frame, from_=1, to=200, textvariable=self.max_turns_var, width=5,
                   bg=self.COLORS["input_bg"], fg=self.COLORS["fg"],
                   buttonbackground=self.COLORS["frame_bg"], font=("Consolas", 10),
                   relief=tk.FLAT).pack(side=tk.LEFT, padx=(5, 15))

        self.strict_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frame, text="Strict", variable=self.strict_var,
                       bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                       selectcolor=self.COLORS["bg"], activebackground=self.COLORS["bg"],
                       activeforeground=self.COLORS["fg"], font=("Consolas", 10)).pack(side=tk.LEFT)

    def _build_turn_area(self):
        container = tk.Frame(self.root, bg=self.COLORS["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(container, bg=self.COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.turn_frame = tk.Frame(self.canvas, bg=self.COLORS["bg"])

        self.turn_frame.bind("<Configure>",
                             lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.turn_frame, anchor=tk.NW,
                                                       width=self.canvas.winfo_reqwidth())

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._placeholder = tk.Label(self.turn_frame, text="Run a task to see turns here...",
                                     fg="#666666", bg=self.COLORS["bg"], font=("Consolas", 12))
        self._placeholder.pack(pady=40)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg=self.COLORS["frame_bg"], height=30)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(self.status_frame, text="Ready", fg=self.COLORS["fg"],
                                     bg=self.COLORS["frame_bg"], font=("Consolas", 10))
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.turns_label = tk.Label(self.status_frame, text="Turns: 0", fg=self.COLORS["fg"],
                                    bg=self.COLORS["frame_bg"], font=("Consolas", 10))
        self.turns_label.pack(side=tk.RIGHT, padx=10)

        self.time_label = tk.Label(self.status_frame, text="", fg=self.COLORS["fg"],
                                   bg=self.COLORS["frame_bg"], font=("Consolas", 10))
        self.time_label.pack(side=tk.RIGHT, padx=10)

    def _start_agent(self):
        if self._running:
            return
        task_desc = self.task_entry.get().strip()
        if not task_desc:
            return

        self._running = True
        self.run_btn.config(state=tk.DISABLED, text="Running...")
        self.status_label.config(text="Running...", fg="#FF9800")
        self.turns_label.config(text="Turns: 0")
        self.time_label.config(text="")

        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None
        for w in self.turn_frame.winfo_children():
            w.destroy()

        self._thread = threading.Thread(target=self._run_agent, args=(task_desc,), daemon=True)
        self._thread.start()

    def _run_agent(self, task_desc):
        try:
            workspace = Path(".").resolve()
            rules = load_rules("guard_rules.yaml")
            guard = GuardEngine(rules, workspace)
            executor = Executor(workspace)
            feedback = FeedbackEngine()

            if self.mode_var.get() == "mock":
                llm = ScriptedMockLLM([
                    Action(tool="read_file", params={"path": "README.md"}),
                    Action(tool="execute_shell", params={"command": "rm -rf /"}),
                    Action(tool="write_file", params={"path": "test.txt", "content": "hello"}),
                ])
            else:
                from src.credential import get_key
                key = get_key()
                if not key:
                    self._queue.put(("error", "No API key configured. Run: python run_cli.py credential set"))
                    return
                from run_cli import DeepSeekClient
                llm = DeepSeekClient(key)

            session = Session(session_id="gui", created_at="", updated_at="",
                              task_description=task_desc, conventions=[], tags=[])
            agent = AgentLoop(llm=llm, guard=guard, executor=executor, feedback=feedback,
                              session_store=None, io=self._io, strict_mode=self.strict_var.get(),
                              max_turns=int(self.max_turns_var.get()),
                              turn_callback=lambda t: self._queue.put(("turn", t)))
            task = Task(description=task_desc)
            result = agent.run(task, session)

            self._queue.put(("done", result))
        except Exception as e:
            self._queue.put(("error", str(e)))

    def _poll_queue(self):
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_message(self, msg):
        msg_type = msg[0]

        if msg_type == "log":
            pass

        elif msg_type == "approval":
            _, action, risk = msg
            self._pending_approval = (action, risk)
            self._show_approval(action, risk)

        elif msg_type == "done":
            _, result = msg
            self._running = False
            self.run_btn.config(state=tk.NORMAL, text="Run")
            color = self.COLORS["SUCCESS"] if result.status == "success" else self.COLORS["ERROR"]
            self.status_label.config(text=result.status, fg=color)
            self.turns_label.config(text=f"Turns: {len(result.turns)}")

        elif msg_type == "error":
            _, error = msg
            self._running = False
            self.run_btn.config(state=tk.NORMAL, text="Run")
            self.status_label.config(text="Error", fg=self.COLORS["ERROR"])
            self._add_turn_frame("Error", error, "", "", "", "")

        elif msg_type == "turn":
            _, turn = msg
            self._add_turn(turn)

    def _add_turn(self, turn: Turn):
        action_text = f"{turn.action.tool}({turn.action.params})"
        verdict_text = str(turn.guard_decision.verdict)
        reason_text = turn.guard_decision.reason or "—"
        result_text = turn.result.output[:200] if turn.result.output else "—"
        result_status = "success" if turn.result.success else "error"
        fb_text = turn.feedback.category if turn.feedback else "—"

        self._add_turn_frame(
            action_text, verdict_text, reason_text,
            result_text, result_status, fb_text,
            turn.turn_number
        )
        self.turns_label.config(text=f"Turns: {turn.turn_number}")

    def _add_turn_frame(self, action, verdict, verdict_reason, result, result_status, feedback, turn_num=0):
        frame = tk.Frame(self.turn_frame, bg=self.COLORS["frame_bg"], padx=10, pady=8,
                         highlightbackground="#444444", highlightthickness=1)
        frame.pack(fill=tk.X, padx=5, pady=3)

        header = tk.Frame(frame, bg=self.COLORS["frame_bg"])
        header.pack(fill=tk.X)
        tk.Label(header, text=f"Turn {turn_num}" if turn_num else "Log",
                 fg="#888888", bg=self.COLORS["frame_bg"],
                 font=("Consolas", 9, "bold")).pack(side=tk.LEFT)

        v_color = self.COLORS.get(verdict, ("#666666", "white"))
        verdict_badge = tk.Label(header, text=f" {verdict} ", bg=v_color[0], fg=v_color[1],
                                 font=("Consolas", 9, "bold"))
        verdict_badge.pack(side=tk.RIGHT)

        row1 = tk.Frame(frame, bg=self.COLORS["frame_bg"])
        row1.pack(fill=tk.X, pady=(5, 0))
        tk.Label(row1, text="Action:", fg="#888888", bg=self.COLORS["frame_bg"],
                 font=("Consolas", 10), width=8, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(row1, text=action, fg=self.COLORS["fg"], bg=self.COLORS["frame_bg"],
                 font=("Consolas", 10), wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT)

        if verdict_reason and verdict_reason != "—":
            row1b = tk.Frame(frame, bg=self.COLORS["frame_bg"])
            row1b.pack(fill=tk.X)
            tk.Label(row1b, text="Reason:", fg="#888888", bg=self.COLORS["frame_bg"],
                     font=("Consolas", 10), width=8, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row1b, text=verdict_reason, fg=self.COLORS["fg"], bg=self.COLORS["frame_bg"],
                     font=("Consolas", 10), wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT)

        row2 = tk.Frame(frame, bg=self.COLORS["frame_bg"])
        row2.pack(fill=tk.X, pady=(2, 0))
        tk.Label(row2, text="Result:", fg="#888888", bg=self.COLORS["frame_bg"],
                 font=("Consolas", 10), width=8, anchor=tk.W).pack(side=tk.LEFT)
        r_color = self.COLORS["SUCCESS"] if result_status == "success" else self.COLORS["ERROR"]
        tk.Label(row2, text=result, fg=r_color, bg=self.COLORS["frame_bg"],
                 font=("Consolas", 10), wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT)

        row3 = tk.Frame(frame, bg=self.COLORS["frame_bg"])
        row3.pack(fill=tk.X, pady=(2, 0))
        tk.Label(row3, text="Feedback:", fg="#888888", bg=self.COLORS["frame_bg"],
                 font=("Consolas", 10), width=8, anchor=tk.W).pack(side=tk.LEFT)
        fb_color = self.COLORS["SUCCESS"] if feedback == "SUCCESS" else self.COLORS["ERROR"]
        tk.Label(row3, text=feedback, fg=fb_color, bg=self.COLORS["frame_bg"],
                 font=("Consolas", 10)).pack(side=tk.LEFT)

    def _show_approval(self, action: Action, risk: RiskInfo):
        if self._pending_approval is None:
            return

        frame = tk.Frame(self.turn_frame, bg="#3d1a1a", padx=10, pady=8,
                         highlightbackground=self.COLORS["BLOCK"][0], highlightthickness=2)
        frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(frame, text="BLOCKED — Approval Required",
                 fg=self.COLORS["BLOCK"][0], bg="#3d1a1a",
                 font=("Consolas", 11, "bold")).pack(anchor=tk.W)

        tk.Label(frame, text=f"Action: {action.tool}({action.params})",
                 fg=self.COLORS["fg"], bg="#3d1a1a",
                 font=("Consolas", 10), wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

        tk.Label(frame, text=f"Risk: {risk.reason}",
                 fg="#FF9800", bg="#3d1a1a",
                 font=("Consolas", 10), wraplength=700, anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))

        btn_frame = tk.Frame(frame, bg="#3d1a1a")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        def approve():
            self._io.resolve_approval(True, "User approved")
            frame.destroy()
            self._pending_approval = None

        def reject():
            self._io.resolve_approval(False, "User rejected")
            frame.destroy()
            self._pending_approval = None

        tk.Button(btn_frame, text="Approve", command=approve,
                  bg="#4CAF50", fg="white", font=("Consolas", 10, "bold"),
                  relief=tk.FLAT, padx=15, pady=3).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="Reject", command=reject,
                  bg="#F44336", fg="white", font=("Consolas", 10, "bold"),
                  relief=tk.FLAT, padx=15, pady=3).pack(side=tk.LEFT)

        self.canvas.yview_moveto(1.0)

    def _on_close(self):
        self._running = False
        if self._pending_approval:
            self._io.resolve_approval(False, "Window closed")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    gui = HarnessGUI()
    gui.run()


if __name__ == "__main__":
    main()