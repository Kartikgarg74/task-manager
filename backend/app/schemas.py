from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateProjectRequest(BaseModel):
    name: str


class CreateCardRequest(BaseModel):
    title: str
    priority: str = "medium"


class MoveCardRequest(BaseModel):
    target_role: str


class LogUpdateRequest(BaseModel):
    resolved: str
    duration_minutes: int
    summary: str
    impact: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    commit_hash: str | None = None
