class ScriptedMockLLM:
    def __init__(self, actions: list):
        self.queue = actions
        self.call_count = 0

    def chat(self, messages: list[dict]) -> dict:
        if self.call_count >= len(self.queue):
            return {"action": "finish", "reason": "queue exhausted"}
        action = self.queue[self.call_count]
        self.call_count += 1
        return {"action": action.tool, "params": action.params}