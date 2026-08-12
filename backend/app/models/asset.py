"""Asset ORM models — Stage 2 output persistence (Character, Location, Prop designs)."""

from typing import Optional

from sqlalchemy import JSON, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, OwnerMixin


class AssetSet(Base, TimestampMixin, OwnerMixin):
    """Persisted Stage 2 output — a complete asset design set.

    Contains character designs, location designs, prop designs, and style manifest.
    """

    __tablename__ = "asset_sets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    script_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True,
        comment="The script version this asset set was based on"
    )

    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(20), default="draft",
        comment="draft | review | approved | locked"
    )

    # ── Full content as JSONB ──
    # Stores: style_manifest, characters[], locations[], props[], consistency_cross_reference
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # ── Denormalized counts ──
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    location_count: Mapped[int] = mapped_column(Integer, default=0)
    prop_count: Mapped[int] = mapped_column(Integer, default=0)
    reference_images_generated: Mapped[int] = mapped_column(Integer, default=0)

    # Style manifest (extracted for quick reference)
    art_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    global_style_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
