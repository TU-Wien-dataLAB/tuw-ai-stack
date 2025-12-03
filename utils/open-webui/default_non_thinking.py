from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()
        pass

    async def inlet(
        self, body: dict, __event_emitter__, __user__: Optional[dict] = None
    ) -> dict:
        thinking_enabled = body.get("chat_template_kwargs", {}).get(
            "enable_thinking", None
        )
        if thinking_enabled is None:
            body["chat_template_kwargs"] = {"enable_thinking": False}
            thinking_enabled = False

        if not thinking_enabled:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Thinking disabled",
                        "done": True,
                        "hidden": False,
                    },
                }
            )
        return body
