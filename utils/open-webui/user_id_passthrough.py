from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Priority of Filter")

    def __init__(self):
        self.valves = self.Valves()
        pass

    async def inlet(
        self, body: dict, __event_emitter__, __user__: Optional[dict] = None
    ) -> dict:
        if __user__:
            body["user_id"] = __user__["email"]
        return body

