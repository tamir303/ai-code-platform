from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class MessageItem(BaseModel):
    role: str
    content: str
    created_at: datetime


class SessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(SessionResponse):
    messages: list[MessageItem] = []
    total_messages: int = 0
    limit: int = 50
    offset: int = 0