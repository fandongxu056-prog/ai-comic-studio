"""Base SQLAlchemy model and common mixins."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Abstract base class for all ORM models."""
    pass


def generate_uuid() -> str:
    """Generate a UUIDv7 string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OwnerMixin:
    """Mixin that adds an owner_id column for multi-tenant isolation."""

    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
