"""Project ORM model — stores project metadata and stage progress."""

from typing import Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, OwnerMixin, generate_uuid


class Project(Base, TimestampMixin, OwnerMixin):
    """Project model — the top-level entity."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Source material
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_content: Mapped[Optional[str]] = mapped_column(nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Genre & style (stored as JSON)
    genre: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Target spec
    format: Mapped[str] = mapped_column(String(50), default="horizontal_standard")
    aspect_ratio: Mapped[str] = mapped_column(String(10), default="16:9")
    target_resolution: Mapped[str] = mapped_column(String(20), default="1920x1080")
    total_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    episode_count: Mapped[int] = mapped_column(Integer, default=1)

    # Style preference
    art_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    style_preference: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Stage tracking (denormalized for fast dashboard queries)
    current_stage: Mapped[str] = mapped_column(
        String(20), default="script",
        comment="script | assets | storyboard | production | complete"
    )

    # Stage artifact IDs
    script_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    script_version: Mapped[int] = mapped_column(Integer, default=0)
    script_status: Mapped[str] = mapped_column(String(20), default="not_started")

    asset_set_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assets_version: Mapped[int] = mapped_column(Integer, default=0)
    assets_status: Mapped[str] = mapped_column(String(20), default="not_started")

    storyboard_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    storyboard_version: Mapped[int] = mapped_column(Integer, default=0)
    storyboard_status: Mapped[str] = mapped_column(String(20), default="not_started")

    production_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    production_version: Mapped[int] = mapped_column(Integer, default=0)
    production_status: Mapped[str] = mapped_column(String(20), default="not_started")

    # Global seed for visual consistency
    global_style_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def stage_summary(self) -> dict:
        """Return a summary of all stage statuses."""
        return {
            "script": {"status": self.script_status, "id": self.script_id, "version": self.script_version},
            "assets": {"status": self.assets_status, "id": self.asset_set_id, "version": self.assets_version},
            "storyboard": {"status": self.storyboard_status, "id": self.storyboard_id, "version": self.storyboard_version},
            "production": {"status": self.production_status, "id": self.production_id, "version": self.production_version},
        }
