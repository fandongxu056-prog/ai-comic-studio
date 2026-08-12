"""Stage 2: Asset API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.asset import AssetSet
from app.models.project import Project

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_assets(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Start asset generation (Stage 2)."""
    project = await _get_project(project_id, user_id, db)
    if not project.script_id:
        raise HTTPException(status_code=400, detail="Script must be generated first")

    project.assets_status = "in_progress"
    await db.commit()

    return {"project_id": project_id, "status": "generating", "message": "Asset generation started"}


@router.get("/{project_id}/status")
async def get_asset_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get asset generation and review status."""
    project = await _get_project(project_id, user_id, db)
    asset_set = await _get_latest_assets(project_id, db)

    return {
        "project_id": project_id,
        "assets_status": project.assets_status,
        "asset_set_id": project.asset_set_id,
        "version": asset_set.version if asset_set else 0,
        "character_count": asset_set.character_count if asset_set else 0,
        "location_count": asset_set.location_count if asset_set else 0,
        "prop_count": asset_set.prop_count if asset_set else 0,
    }


@router.get("/{project_id}/characters")
async def get_characters(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get character design sheets."""
    await _get_project(project_id, user_id, db)
    asset_set = await _get_latest_assets(project_id, db)
    if asset_set is None:
        return {"project_id": project_id, "characters": []}
    return {
        "project_id": project_id,
        "characters": asset_set.content.get("characters", []),
        "style_manifest": asset_set.content.get("style_manifest", {}),
    }


@router.get("/{project_id}/locations")
async def get_locations(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get location design sheets."""
    await _get_project(project_id, user_id, db)
    asset_set = await _get_latest_assets(project_id, db)
    if asset_set is None:
        return {"project_id": project_id, "locations": []}
    return {
        "project_id": project_id,
        "locations": asset_set.content.get("locations", []),
    }


@router.post("/{project_id}/review/approve")
async def approve_assets(
    project_id: str,
    notes: str = "",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Human approves asset designs."""
    project = await _get_project(project_id, user_id, db)
    asset_set = await _get_latest_assets(project_id, db)
    if asset_set is None:
        raise HTTPException(status_code=400, detail="No assets to approve")

    asset_set.status = "approved"
    project.assets_status = "locked"
    project.current_stage = "storyboard"
    await db.commit()

    return {"project_id": project_id, "status": "approved", "next_stage": "storyboard"}


async def _get_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    q = select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    result = await db.execute(q)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


async def _get_latest_assets(project_id: str, db: AsyncSession) -> AssetSet | None:
    q = (
        select(AssetSet)
        .where(AssetSet.project_id == project_id)
        .order_by(AssetSet.version.desc())
        .limit(1)
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()
