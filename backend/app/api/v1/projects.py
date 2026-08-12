"""Project CRUD API endpoints (Stage 0)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PaginationParams, get_current_user, get_db
from app.models.project import Project
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.utils.id_generator import generate_project_id

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Create a new project (Stage 0 entry point)."""
    project = Project(
        id=generate_project_id(),
        owner_id=user_id,
        title=body.title,
        source_type=body.source_type.value if hasattr(body.source_type, 'value') else body.source_type,
        source_content=body.source_content,
        source_url=str(body.source_url) if body.source_url else None,
        genre=body.genre.model_dump() if body.genre else None,
        format=body.target_spec.format.value if body.target_spec else "horizontal_standard",
        aspect_ratio=body.target_spec.aspect_ratio.value if body.target_spec else "16:9",
        target_resolution=body.target_spec.target_resolution if body.target_spec else "1920x1080",
        total_duration_seconds=body.target_spec.total_duration_seconds if body.target_spec else None,
        episode_count=body.target_spec.episode_count if body.target_spec else 1,
        art_style=body.style_preference.art_style.value if body.style_preference else None,
        style_preference=body.style_preference.model_dump() if body.style_preference else None,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _to_response(project)


@router.get("/")
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """List projects for the current user."""
    pagination = PaginationParams(page=page, page_size=page_size)

    count_q = select(func.count()).select_from(Project).where(Project.owner_id == user_id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Project)
        .where(Project.owner_id == user_id)
        .order_by(Project.updated_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    projects = (await db.execute(q)).scalars().all()

    return {
        "data": [_to_response(p) for p in projects],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get project details and stage progress."""
    project = await _get_owned(project_id, user_id, db)
    return _to_response(project)


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Update project settings (partial update)."""
    project = await _get_owned(project_id, user_id, db)
    for key, value in body.model_dump(exclude_unset=True).items():
        if hasattr(project, key) and value is not None:
            setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return _to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Delete a project and all associated data (CASCADE)."""
    project = await _get_owned(project_id, user_id, db)
    await db.delete(project)
    await db.commit()


async def _get_owned(project_id: str, user_id: str, db: AsyncSession) -> Project:
    q = select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    result = await db.execute(q)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


def _to_response(p: Project) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "source_type": p.source_type,
        "genre": p.genre,
        "format": p.format,
        "aspect_ratio": p.aspect_ratio,
        "target_resolution": p.target_resolution,
        "total_duration_seconds": p.total_duration_seconds,
        "episode_count": p.episode_count,
        "art_style": p.art_style,
        "style_preference": p.style_preference,
        "current_stage": p.current_stage,
        "stages": p.stage_summary(),
        "global_style_seed": p.global_style_seed,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
