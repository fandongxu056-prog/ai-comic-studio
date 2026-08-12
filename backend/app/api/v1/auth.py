"""Authentication API — register, login, refresh, user profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new account and return access + refresh tokens."""
    # Check uniqueness
    existing_email = await auth_service.get_user_by_email(db, body.email)
    if existing_email:
        raise HTTPException(status_code=409, detail="该邮箱已被注册")

    existing_username = await auth_service.get_user_by_username(db, body.username)
    if existing_username:
        raise HTTPException(status_code=409, detail="该用户名已被使用")

    user = await auth_service.create_user(
        db=db,
        email=body.email,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
    )

    access_token, expires_in = auth_service.create_access_token(user.id, user.username)
    refresh_token = auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email/username + password, return tokens."""
    user = await auth_service.authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="邮箱/用户名或密码错误")

    access_token, expires_in = auth_service.create_access_token(user.id, user.username)
    refresh_token = auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    payload = auth_service.decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的 Refresh Token")

    user_id = payload.get("sub", "")
    username = payload.get("username", "")

    # Verify user still exists
    # (in production, query the DB here)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的 Token")

    access_token, expires_in = auth_service.create_access_token(user_id, username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=body.refresh_token,
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
