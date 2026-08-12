"""Initial schema — all core tables for the AI Comic Studio platform.

Creates: projects, scripts, asset_sets, storyboards, productions

Revision ID: 001
Revises: None
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # ── Users ──
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # ── Projects ──
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_content", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("genre", sa.JSON(), nullable=True),
        sa.Column("format", sa.String(50), server_default="horizontal_standard"),
        sa.Column("aspect_ratio", sa.String(10), server_default="16:9"),
        sa.Column("target_resolution", sa.String(20), server_default="1920x1080"),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("episode_count", sa.Integer(), server_default="1"),
        sa.Column("art_style", sa.String(50), nullable=True),
        sa.Column("style_preference", sa.JSON(), nullable=True),
        sa.Column("current_stage", sa.String(20), server_default="script"),
        sa.Column("script_id", sa.String(50), nullable=True),
        sa.Column("script_version", sa.Integer(), server_default="0"),
        sa.Column("script_status", sa.String(20), server_default="not_started"),
        sa.Column("asset_set_id", sa.String(50), nullable=True),
        sa.Column("assets_version", sa.Integer(), server_default="0"),
        sa.Column("assets_status", sa.String(20), server_default="not_started"),
        sa.Column("storyboard_id", sa.String(50), nullable=True),
        sa.Column("storyboard_version", sa.Integer(), server_default="0"),
        sa.Column("storyboard_status", sa.String(20), server_default="not_started"),
        sa.Column("production_id", sa.String(50), nullable=True),
        sa.Column("production_version", sa.Integer(), server_default="0"),
        sa.Column("production_status", sa.String(20), server_default="not_started"),
        sa.Column("global_style_seed", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Scripts ──
    op.create_table(
        "scripts",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("episode_count", sa.Integer(), server_default="0"),
        sa.Column("scene_count", sa.Integer(), server_default="0"),
        sa.Column("segment_count", sa.Integer(), server_default="0"),
        sa.Column("character_count", sa.Integer(), server_default="0"),
        sa.Column("location_count", sa.Integer(), server_default="0"),
        sa.Column("prop_count", sa.Integer(), server_default="0"),
        sa.Column("latest_score", sa.Integer(), nullable=True),
        sa.Column("latest_verdict", sa.String(30), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scripts_project_id", "scripts", ["project_id"])

    # ── Asset Sets ──
    op.create_table(
        "asset_sets",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_id", sa.String(50), sa.ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("character_count", sa.Integer(), server_default="0"),
        sa.Column("location_count", sa.Integer(), server_default="0"),
        sa.Column("prop_count", sa.Integer(), server_default="0"),
        sa.Column("reference_images_generated", sa.Integer(), server_default="0"),
        sa.Column("art_style", sa.String(50), nullable=True),
        sa.Column("global_style_seed", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_asset_sets_project_id", "asset_sets", ["project_id"])

    # ── Storyboards ──
    op.create_table(
        "storyboards",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_id", sa.String(50), sa.ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_set_id", sa.String(50), sa.ForeignKey("asset_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("episode_count", sa.Integer(), server_default="0"),
        sa.Column("total_shots", sa.Integer(), server_default="0"),
        sa.Column("total_duration_ms", sa.Integer(), server_default="0"),
        sa.Column("latest_score", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_storyboards_project_id", "storyboards", ["project_id"])

    # ── Productions ──
    op.create_table(
        "productions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storyboard_id", sa.String(50), sa.ForeignKey("storyboards.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_set_id", sa.String(50), sa.ForeignKey("asset_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("shots_total", sa.Integer(), server_default="0"),
        sa.Column("shots_completed", sa.Integer(), server_default="0"),
        sa.Column("videos_exported", sa.Integer(), server_default="0"),
        sa.Column("total_duration_seconds", sa.Float(), server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), server_default="0"),
        sa.Column("budget_compliance", sa.String(20), nullable=True),
        sa.Column("completed_at", sa.String(30), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_productions_project_id", "productions", ["project_id"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("productions")
    op.drop_table("users")
    op.drop_table("storyboards")
    op.drop_table("asset_sets")
    op.drop_table("scripts")
    op.drop_table("projects")
