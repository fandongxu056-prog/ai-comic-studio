"""Script ORM model — Stage 1 output persistence.

Stores the full StructuredScript as JSONB with denormalized summary columns
for fast dashboard queries. The authoritative schema is defined in
app/schemas/stage1_script.py (Pydantic) and docs/schema-design.md (JSON Schema).
"""

from typing import Optional

from sqlalchemy import JSON, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, OwnerMixin, generate_uuid


class Script(Base, TimestampMixin, OwnerMixin):
    """Persisted Stage 1 output — a structured comic drama script."""

    __tablename__ = "scripts"

    # Primary key uses the structured script_id (e.g., SCR-A1B2C3D4)
    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Link to project
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Version control
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(20), default="draft",
        comment="draft | review | approved | locked"
    )

    # ── Full content as JSONB ──
    # Stores the complete StructuredScript: global_context, episodes, indexes, review_history
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # ── Denormalized summary columns (for dashboard queries without parsing JSONB) ──
    episode_count: Mapped[int] = mapped_column(Integer, default=0)
    scene_count: Mapped[int] = mapped_column(Integer, default=0)
    segment_count: Mapped[int] = mapped_column(Integer, default=0)
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    location_count: Mapped[int] = mapped_column(Integer, default=0)
    prop_count: Mapped[int] = mapped_column(Integer, default=0)

    # Latest review score (for quick status display)
    latest_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latest_verdict: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    def update_from_pydantic(self, script_model) -> None:
        """Sync denormalized columns from a StructuredScript Pydantic model."""
        summary = script_model.summary()
        self.episode_count = summary["episode_count"]
        self.scene_count = summary["scene_count"]
        self.segment_count = summary["segment_count"]
        self.character_count = summary["character_count"]
        self.location_count = summary["location_count"]
        self.prop_count = summary["prop_count"]
        self.content = script_model.model_dump()
        self.version = script_model.version
        self.status = script_model.status.value if hasattr(script_model.status, 'value') else script_model.status
