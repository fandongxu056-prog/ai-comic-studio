"""Pydantic schemas for Project — mapping to ProjectInput in docs/schema-design.md."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──

class SourceType(str, Enum):
    ORIGINAL_IDEA = "original_idea"
    NOVEL_EXCERPT = "novel_excerpt"
    SYNOPSIS = "synopsis"
    OUTLINE = "outline"
    FULL_NOVEL = "full_novel"


class FormatType(str, Enum):
    HORIZONTAL_STANDARD = "horizontal_standard"
    VERTICAL_SHORT = "vertical_short"
    SQUARE = "square"


class AspectRatio(str, Enum):
    R16_9 = "16:9"
    R9_16 = "9:16"
    R1_1 = "1:1"
    R4_3 = "4:3"
    R3_4 = "3:4"


class ArtStyle(str, Enum):
    ANIME = "anime"
    REALISTIC = "realistic"
    SEMI_REALISTIC = "semi_realistic"
    CARTOON = "cartoon"
    INK_WASH = "ink_wash"
    CHINESE_INK = "chinese_ink"
    COMIC_BOOK = "comic_book"
    ILLUSTRATION = "illustration"
    RENDER_3D = "3d_render"
    OTHER = "other"


class StageStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    LOCKED = "locked"
    REVISION = "revision"
    COMPLETE = "complete"
    FAILED = "failed"


# ── Request Schemas ──

class GenreSpec(BaseModel):
    primary: str
    sub_tags: list[str] = Field(default_factory=list, max_length=10)


class TargetSpec(BaseModel):
    format: FormatType = FormatType.HORIZONTAL_STANDARD
    aspect_ratio: AspectRatio = AspectRatio.R16_9
    target_resolution: str = "1920x1080"
    total_duration_seconds: int = Field(ge=30, le=7200)
    episode_count: int = Field(default=1, ge=1, le=200)
    duration_per_episode_seconds: int = Field(ge=30, le=600)


class StylePreference(BaseModel):
    art_style: ArtStyle = ArtStyle.ANIME
    color_palette: Optional[str] = None
    reference_images: list[dict] = Field(default_factory=list, max_length=20)
    style_notes: Optional[str] = Field(default=None, max_length=2000)


class ProjectCreateRequest(BaseModel):
    """Request to create a new project (Stage 0 input)."""
    title: str = Field(max_length=200)
    source_type: SourceType
    source_content: str = Field(max_length=200000)
    source_url: Optional[str] = None
    genre: Optional[GenreSpec] = None
    target_spec: TargetSpec = Field(default_factory=TargetSpec)
    style_preference: StylePreference = Field(default_factory=StylePreference)


class ProjectUpdateRequest(BaseModel):
    """Request to update project settings."""
    title: Optional[str] = Field(default=None, max_length=200)
    target_spec: Optional[TargetSpec] = None
    style_preference: Optional[StylePreference] = None


# ── Response Schemas ──

class ProjectStageSummary(BaseModel):
    status: StageStatus = StageStatus.NOT_STARTED
    id: Optional[str] = None
    version: int = 0


class ProjectStagesSummary(BaseModel):
    script: ProjectStageSummary = Field(default_factory=ProjectStageSummary)
    assets: ProjectStageSummary = Field(default_factory=ProjectStageSummary)
    storyboard: ProjectStageSummary = Field(default_factory=ProjectStageSummary)
    production: ProjectStageSummary = Field(default_factory=ProjectStageSummary)


class ProjectResponse(BaseModel):
    """Project details response."""
    id: str
    title: str
    source_type: SourceType
    genre: Optional[GenreSpec] = None
    format: FormatType = FormatType.HORIZONTAL_STANDARD
    aspect_ratio: AspectRatio = AspectRatio.R16_9
    target_resolution: str = "1920x1080"
    current_stage: str = "script"
    stages: ProjectStagesSummary = Field(default_factory=ProjectStagesSummary)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """List of user's projects."""
    projects: list[ProjectResponse]
    total: int
