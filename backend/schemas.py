from pydantic import BaseModel
from typing import Optional

class ChatIn(BaseModel):
    username: str
    message: str
    chat_id: Optional[int] = None
    agent_id: Optional[int] = None
