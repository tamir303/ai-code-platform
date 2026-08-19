from pydantic import BaseModel, Field


class AutocompleteRequest(BaseModel):
    prefix: str = Field(..., description="Code content immediately before the cursor")
    suffix: str = Field(default="", description="Code content immediately after the cursor")
    language: str | None = Field(default=None, description="Optional language hint, e.g. 'python'")


class AutocompleteResponse(BaseModel):
    completion: str
