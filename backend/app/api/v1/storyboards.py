"""Stage 3: Storyboard API endpoints."""

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_storyboard(project_id: str, user_id: str = Depends(get_current_user)):
    """Start storyboard generation (Stage 3). ShotComposer + PacingDirector + ContinuityCheck."""
    return {"project_id": project_id, "status": "generating"}


@router.get("/{project_id}/status")
async def get_storyboard_status(project_id: str, user_id: str = Depends(get_current_user)):
    return {"project_id": project_id, "storyboard_status": "not_started"}


@router.get("/{project_id}/shots")
async def get_shots(project_id: str, episode: int = 1, user_id: str = Depends(get_current_user)):
    """Get shot list for a specific episode."""
    return {"project_id": project_id, "episode": episode, "shots": []}


@router.post("/{project_id}/review/approve")
async def approve_storyboard(project_id: str, notes: str = "", user_id: str = Depends(get_current_user)):
    return {"project_id": project_id, "status": "approved"}
