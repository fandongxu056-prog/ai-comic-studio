"""Stage 3: Storyboard API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.project import Project
from app.models.storyboard import Storyboard

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_storyboard(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Start storyboard generation (Stage 3)."""
    project = await _get_project(project_id, user_id, db)
    if not project.asset_set_id:
        raise HTTPException(status_code=400, detail="Assets must be designed first")

    project.storyboard_status = "in_progress"
    await db.commit()

    return {"project_id": project_id, "status": "generating"}


@router.get("/{project_id}/status")
async def get_storyboard_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get storyboard generation status."""
    project = await _get_project(project_id, user_id, db)
    storyboard = await _get_latest_storyboard(project_id, db)

    return {
        "project_id": project_id,
        "storyboard_status": project.storyboard_status,
        "storyboard_id": project.storyboard_id,
        "version": storyboard.version if storyboard else 0,
        "total_shots": storyboard.total_shots if storyboard else 0,
        "total_duration_ms": storyboard.total_duration_ms if storyboard else 0,
    }


@router.get("/{project_id}/shots")
async def get_shots(
    project_id: str,
    episode: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get shot list for a specific episode."""
    await _get_project(project_id, user_id, db)
    storyboard = await _get_latest_storyboard(project_id, db)

    if storyboard is None:
        return {"project_id": project_id, "episode": episode, "shots": []}

    episodes = storyboard.content.get("episodes", [])
    target_ep = next((ep for ep in episodes if ep.get("episode_index") == episode), None)

    return {
        "project_id": project_id,
        "episode": episode,
        "shots": target_ep.get("scenes", []) if target_ep else [],
    }


@router.post("/{project_id}/review/approve")
async def approve_storyboard(
    project_id: str,
    notes: str = "",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Human approves the storyboard."""
    project = await _get_project(project_id, user_id, db)
    storyboard = await _get_latest_storyboard(project_id, db)
    if storyboard is None:
        raise HTTPException(status_code=400, detail="No storyboard to approve")

    storyboard.status = "approved"
    project.storyboard_status = "locked"
    project.current_stage = "production"
    await db.commit()

    return {"project_id": project_id, "status": "approved", "next_stage": "production"}


async def _get_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    q = select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    result = await db.execute(q)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


async def _get_latest_storyboard(project_id: str, db: AsyncSession) -> Storyboard | None:
    q = (
        select(Storyboard)
        .where(Storyboard.project_id == project_id)
        .order_by(Storyboard.version.desc())
        .limit(1)
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()
