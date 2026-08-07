"""Stage 1: Script API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_script(project_id: str, user_id: str = Depends(get_current_user)):
    """Start script generation for a project (Stage 1 entry).

    This triggers the ScriptWriter Agent and the review loop.
    Results are streamed via SSE.
    """
    return {
        "project_id": project_id,
        "status": "generating",
        "message": "Script generation started",
    }


@router.get("/{project_id}/status")
async def get_script_status(project_id: str, user_id: str = Depends(get_current_user)):
    """Get the current script generation status."""
    return {
        "project_id": project_id,
        "script_status": "not_started",
        "version": 0,
        "review_round": 0,
    }


@router.get("/{project_id}/latest")
async def get_latest_script(project_id: str, user_id: str = Depends(get_current_user)):
    """Get the latest version of the structured script."""
    return {
        "project_id": project_id,
        "script": None,
        "message": "No script generated yet",
    }


@router.post("/{project_id}/review/approve")
async def approve_script(project_id: str, notes: str = "", user_id: str = Depends(get_current_user)):
    """Human approves the script and locks the stage."""
    return {
        "project_id": project_id,
        "status": "approved",
        "next_stage": "assets",
    }


@router.post("/{project_id}/review/reject")
async def reject_script(project_id: str, notes: str, user_id: str = Depends(get_current_user)):
    """Human rejects the script with revision notes."""
    return {
        "project_id": project_id,
        "status": "rejected",
        "notes": notes,
    }
