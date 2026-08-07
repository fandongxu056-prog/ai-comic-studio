"""Stage 2: Asset API endpoints."""

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_assets(project_id: str, user_id: str = Depends(get_current_user)):
    """Start asset generation (Stage 2). Runs CharDesigner + SceneDesigner + PropDesigner in parallel."""
    return {"project_id": project_id, "status": "generating"}


@router.get("/{project_id}/status")
async def get_asset_status(project_id: str, user_id: str = Depends(get_current_user)):
    """Get asset generation and review status."""
    return {"project_id": project_id, "assets_status": "not_started"}


@router.get("/{project_id}/characters")
async def get_characters(project_id: str, user_id: str = Depends(get_current_user)):
    """Get character design sheets."""
    return {"project_id": project_id, "characters": []}


@router.get("/{project_id}/locations")
async def get_locations(project_id: str, user_id: str = Depends(get_current_user)):
    """Get location design sheets."""
    return {"project_id": project_id, "locations": []}


@router.post("/{project_id}/review/approve")
async def approve_assets(project_id: str, notes: str = "", user_id: str = Depends(get_current_user)):
    """Human approves asset designs."""
    return {"project_id": project_id, "status": "approved"}
