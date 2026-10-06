from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    role_id: int
    status: bool = True


class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=64)
    role_id: int | None = None
    status: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str | None
    role_id: int
    role_name: str | None = None
    status: bool

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None

    model_config = {"from_attributes": True}


class OperationLogOut(BaseModel):
    id: int
    user_id: int | None
    username: str | None = None
    operation: str
    module: str | None
    request_method: str | None
    request_path: str | None
    ip: str | None
    result: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportPreviewRow(BaseModel):
    row: int
    data: dict
    errors: list[str] = []
