"""Stage 4: Production API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.production import Production
from app.models.project import Project

router = APIRouter()


@router.post("/{project_id}/start")
async def start_production(
    project_id: str,
    episode_indices: list[int] | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Start video production (Stage 4)."""
    project = await _get_project(project_id, user_id, db)
    if not project.storyboard_id:
        raise HTTPException(status_code=400, detail="Storyboard must be completed first")

    project.production_status = "in_progress"
    await db.commit()

    return {
        "project_id": project_id,
        "status": "starting",
        "episodes": episode_indices or "all",
    }


@router.get("/{project_id}/status")
async def get_production_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get production progress."""
    project = await _get_project(project_id, user_id, db)
    production = await _get_latest_production(project_id, db)

    return {
        "project_id": project_id,
        "status": project.production_status,
        "production_id": project.production_id,
        "shots_completed": production.shots_completed if production else 0,
        "shots_total": production.shots_total if production else 0,
        "videos_exported": production.videos_exported if production else 0,
        "total_cost_usd": production.total_cost_usd if production else 0,
    }


@router.get("/{project_id}/progress")
async def get_production_progress(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get real-time production progress."""
    production = await _get_latest_production(project_id, db)
    if production is None:
        return {"project_id": project_id, "progress": 0.0, "current_phase": "pending"}

    total = production.shots_total
    done = production.shots_completed
    progress = done / total if total > 0 else 0.0

    return {
        "project_id": project_id,
        "progress": round(progress, 2),
        "current_phase": production.status,
        "shots_completed": done,
        "shots_total": total,
    }


@router.get("/{project_id}/videos/{episode_index}")
async def get_final_video(
    project_id: str,
    episode_index: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get download URL for final video."""
    await _get_project(project_id, user_id, db)
    production = await _get_latest_production(project_id, db)

    if production is None:
        raise HTTPException(status_code=404, detail="No production found")

    videos = production.content.get("final_videos", [])
    target = next((v for v in videos if v.get("episode_index") == episode_index), None)

    if target is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_index} not found")

    return {
        "project_id": project_id,
        "episode": episode_index,
        "video_url": target.get("output_url", ""),
        "duration_ms": target.get("duration_ms", 0),
        "file_size_bytes": target.get("file_size_bytes", 0),
        "has_subtitles": target.get("has_subtitles", True),
    }


@router.get("/{project_id}/cost")
async def get_cost_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get detailed cost report."""
    await _get_project(project_id, user_id, db)
    production = await _get_latest_production(project_id, db)

    if production is None:
        return {"project_id": project_id, "total_cost_usd": 0, "breakdown": {}}

    cost_report = production.content.get("cost_report", {})
    return {
        "project_id": project_id,
        "total_cost_usd": production.total_cost_usd,
        "breakdown": cost_report.get("breakdown", {}),
        "budget_compliance": production.budget_compliance or "under_budget",
    }


async def _get_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    q = select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    result = await db.execute(q)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


async def _get_latest_production(project_id: str, db: AsyncSession) -> Production | None:
    q = (
        select(Production)
        .where(Production.project_id == project_id)
        .order_by(Production.version.desc())
        .limit(1)
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()
