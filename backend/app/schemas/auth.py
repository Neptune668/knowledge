"""认证相关请求/响应模型。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    department_id: int | None = None
    department_name: str | None = None
    roles: list[str] = []


class LoginResponse(BaseModel):
    access_token: str
    user_info: UserInfo
    permissions: list[str]
