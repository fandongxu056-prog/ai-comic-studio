"""Production ORM model — Stage 4 output persistence."""

from typing import Optional

from sqlalchemy import JSON, Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, OwnerMixin


class Production(Base, TimestampMixin, OwnerMixin):
    """Persisted Stage 4 output — generated assets, final videos, and cost report."""

    __tablename__ = "productions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storyboard_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("storyboards.id", ondelete="SET NULL"), nullable=True
    )
    asset_set_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("asset_sets.id", ondelete="SET NULL"), nullable=True
    )

    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
        comment="pending | in_progress | partial_complete | complete | failed"
    )

    # ── Full content as JSONB ──
    # Stores: generated_assets (by shot_id), final_videos[], task_log[], cost_report, quality_report
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # ── Denormalized progress ──
    shots_total: Mapped[int] = mapped_column(Integer, default=0)
    shots_completed: Mapped[int] = mapped_column(Integer, default=0)
    videos_exported: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Cost tracking ──
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    budget_compliance: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="under_budget | near_limit | exceeded_warn | exceeded_capped"
    )

    completed_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
