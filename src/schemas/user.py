from uuid import UUID
from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    username: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    api_key: str