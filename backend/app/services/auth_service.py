"""Authentication service — JWT tokens, password hashing, user management."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

# Password hashing
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# Token config
ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.secret_key
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


# ── Password Utilities ──


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using Argon2/Bcrypt."""
    return pwd_context.hash(password)


# ── Token Utilities ──


def create_access_token(user_id: str, username: str) -> tuple[str, int]:
    """Create a JWT access token.

    Returns:
        (token_string, expires_in_seconds)
    """
    expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    expires_delta = timedelta(minutes=expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire_minutes * 60


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ── User CRUD ──


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    password: str,
    display_name: str | None = None,
) -> User:
    """Create a new user with hashed password."""
    user = User(
        email=email.lower().strip(),
        username=username.strip(),
        hashed_password=hash_password(password),
        display_name=display_name or username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Find a user by email (case-insensitive)."""
    q = select(User).where(User.email == email.lower().strip())
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Find a user by username."""
    q = select(User).where(User.username == username.strip())
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Find a user by ID."""
    q = select(User).where(User.id == user_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, email_or_username: str, password: str) -> User | None:
    """Authenticate a user by email/username + password.

    Returns the User on success, None on failure.
    """
    identifier = email_or_username.strip()
    user = await get_user_by_email(db, identifier)
    if user is None:
        user = await get_user_by_username(db, identifier)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
