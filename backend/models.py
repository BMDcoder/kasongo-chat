from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    role: str  # 'user' or 'agent'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
# models are defined inline in main.py using SQLModel for brevity.
