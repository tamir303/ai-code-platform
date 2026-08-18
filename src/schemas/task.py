from pydantic import BaseModel, Field


class CodeFilePayload(BaseModel):
    filename: str = Field(..., example="auth.py")
    code: str = Field(..., example="def login(): pass")


class CodeReviewRequest(BaseModel):
    files: list[CodeFilePayload]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None