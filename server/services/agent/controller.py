import json
from typing import List, Dict, Any
from ..init_services import inference, tool_manager
from .dialog_state import DialogueState
from ...logger import logger


class AgentController:

    def __init__(self, ws):
        self.ws = ws
        self.state = DialogueState()

        self.running = False

    async def handle_text(self, text: str):
        if not text.strip():
            return

        self.state.add("user", text)
        await self._run_agent_loop()


    async def handle_text(self, text: str):
        if not text.strip():
            return

        self.state.add("user", text)
        await self._run_agent_loop()


    def reset(self):
        self.state.reset()

    async def cleanup(self):
        pass


    async def _run_agent_loop(self):
        """
        Классический agent loop:
        generate -> tool_calls -> execute -> generate -> ...
        """
        if self.running:
            return  
        self.running = True

        try:
            while True:
                self.state.cut_history()
                messages = self.state.get_messages()

                stream = inference.generate(
                    prompt=messages,
                )

                tool_calls: List[Dict[str, Any]] = []
                assistant_text = ""

                async for event in stream:
                    etype = event["type"]

                    if etype == "token":
                        assistant_text += event["content"]
                        await self.ws.send_json({
                            "type": "token",
                            "token": event["content"]
                        })

                    elif etype == "tool_calls":
                        tool_calls = event["data"]
                        break

                    elif etype == "end":
                        if assistant_text.strip():
                            self.state.add("assistant", assistant_text)
                        await self.ws.send_json({"type": "complete"})
                        return

                if not tool_calls:
                    if assistant_text.strip():
                        self.state.add("assistant", assistant_text)
                    await self.ws.send_json({"type": "complete"})
                    return

                for call in tool_calls:
                    call = json.loads(call)
                    name = call.get("name")
                    args = call.get("arguments", {})

                    try:
                        logger.info(f"Tool Call: {name}: {args}")
                        result = tool_manager.execute(name, args)
                        logger.info(f"Results: {result}")
                    except Exception as e:
                        result = f"Tool error: {e}"

                    self.state.add(
                        role="tool",
                        content=json.dumps(result, ensure_ascii=False),
                        tool_name=name
                    )
                    logger.info(self.state.get_messages())

        finally:
            self.running = False
