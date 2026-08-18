from uuid import UUID
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User prompt or code query")
    session_id: UUID | None = Field(default=None, description="Optional existing session ID")


class ChatChunkResponse(BaseModel):
    session_id: UUID
    content: str
    is_done: bool = False