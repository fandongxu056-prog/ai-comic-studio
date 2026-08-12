"""Authentication schemas — register, login, token responses."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr = Field(description="注册邮箱")
    username: str = Field(min_length=3, max_length=100, description="用户名")
    password: str = Field(min_length=6, max_length=128, description="密码")
    display_name: str | None = Field(default=None, max_length=100, description="显示名称")


class LoginRequest(BaseModel):
    """User login payload."""

    email: str = Field(description="邮箱或用户名")
    password: str = Field(description="密码")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(description="JWT Access Token")
    refresh_token: str = Field(description="JWT Refresh Token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(description="Token 有效期（秒）")


class RefreshRequest(BaseModel):
    """Token refresh payload."""

    refresh_token: str = Field(description="Refresh Token")


class UserResponse(BaseModel):
    """Public user profile."""

    id: str
    email: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: str | None = None
