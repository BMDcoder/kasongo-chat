from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginIn(BaseModel):
    username: str
    password: str

class AgentIn(BaseModel):
    name: str
    system_prompt: str
    description: Optional[str] = None

class ChatIn(BaseModel):
    username: Optional[str] = "guest"
    agent_id: int
    message: str
