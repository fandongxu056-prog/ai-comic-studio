"""Stage 4: Production API endpoints."""

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/{project_id}/start")
async def start_production(project_id: str, episode_indices: list[int] | None = None, user_id: str = Depends(get_current_user)):
    """Start video production (Stage 4). Kicks off the deterministic pipeline."""
    return {"project_id": project_id, "status": "starting", "episodes": episode_indices}


@router.get("/{project_id}/status")
async def get_production_status(project_id: str, user_id: str = Depends(get_current_user)):
    """Get production progress for all episodes."""
    return {
        "project_id": project_id,
        "status": "not_started",
        "episodes": [],
        "total_cost_usd": 0,
    }


@router.get("/{project_id}/progress")
async def get_production_progress(project_id: str, user_id: str = Depends(get_current_user)):
    """Get real-time production progress with per-shot status."""
    return {
        "project_id": project_id,
        "progress": 0.0,
        "current_phase": "pending",
        "shots_completed": 0,
        "shots_total": 0,
    }


@router.get("/{project_id}/videos/{episode_index}")
async def get_final_video(project_id: str, episode_index: int, user_id: str = Depends(get_current_user)):
    """Get download URL for final composited video."""
    return {"project_id": project_id, "episode": episode_index, "video_url": ""}


@router.get("/{project_id}/cost")
async def get_cost_report(project_id: str, user_id: str = Depends(get_current_user)):
    """Get detailed cost report for the production."""
    return {
        "project_id": project_id,
        "total_cost_usd": 0,
        "breakdown": {},
        "budget_compliance": "under_budget",
    }
