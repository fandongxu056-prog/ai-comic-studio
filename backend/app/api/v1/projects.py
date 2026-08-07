"""Project CRUD API endpoints (Stage 0)."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def create_project():
    """Create a new project with initial input."""
    return {"message": "Not implemented yet"}


@router.get("/")
async def list_projects():
    """List all projects for the current user."""
    return {"projects": []}


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project details and stage progress."""
    return {"project_id": project_id, "status": "not_started"}


@router.put("/{project_id}")
async def update_project(project_id: str):
    """Update project settings."""
    return {"project_id": project_id, "updated": True}


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all associated data."""
    return {"project_id": project_id, "deleted": True}
