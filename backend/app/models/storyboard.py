"""Storyboard ORM model — Stage 3 output persistence."""

from typing import Optional

from sqlalchemy import JSON, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, OwnerMixin


class Storyboard(Base, TimestampMixin, OwnerMixin):
    """Persisted Stage 3 output — a complete shot plan with keyframe prompts."""

    __tablename__ = "storyboards"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    script_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True
    )
    asset_set_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("asset_sets.id", ondelete="SET NULL"), nullable=True
    )

    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(20), default="draft",
        comment="draft | review | approved | locked"
    )

    # ── Full content as JSONB ──
    # Stores: episodes[] (with scenes[] → shots[]), tempo_analysis, review_history
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # ── Denormalized counts ──
    episode_count: Mapped[int] = mapped_column(Integer, default=0)
    total_shots: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    latest_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
