"""Stage 1: Script API endpoints — CRUD + generation trigger."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.project import Project
from app.models.script import Script
from app.schemas.stage1_script import StructuredScript

router = APIRouter()


@router.post("/{project_id}/generate")
async def generate_script(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Start script generation for a project (Stage 1 entry).

    Triggers the ScriptWriter Agent and review loop in the background.
    Results are persisted to the scripts table.
    """
    # Verify project exists and belongs to user
    project = await _get_project(project_id, user_id, db)

    # Update project stage status
    project.script_status = "in_progress"
    await db.commit()

    # Launch generation in background (non-blocking)
    background_tasks.add_task(_run_script_generation, project_id, project)

    return {
        "project_id": project_id,
        "status": "generating",
        "message": "Script generation started — review loop will run automatically",
    }


@router.get("/{project_id}/status")
async def get_script_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get current script generation status."""
    project = await _get_project(project_id, user_id, db)
    script = await _get_latest_script(project_id, db)

    return {
        "project_id": project_id,
        "script_status": project.script_status,
        "script_id": project.script_id,
        "version": script.version if script else 0,
        "latest_score": script.latest_score if script else None,
        "latest_verdict": script.latest_verdict if script else None,
    }


@router.get("/{project_id}/latest")
async def get_latest_script(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get the latest version of the structured script."""
    await _get_project(project_id, user_id, db)  # Verify ownership
    script = await _get_latest_script(project_id, db)

    if script is None:
        return {"project_id": project_id, "script": None, "message": "No script generated yet"}

    return {
        "project_id": project_id,
        "script_id": script.id,
        "version": script.version,
        "status": script.status,
        "episode_count": script.episode_count,
        "scene_count": script.scene_count,
        "character_count": script.character_count,
        "latest_score": script.latest_score,
        "content": script.content,
        "created_at": script.created_at.isoformat() if script.created_at else None,
    }


@router.post("/{project_id}/review/approve")
async def approve_script(
    project_id: str,
    notes: str = "",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Human approves the script and locks the stage."""
    project = await _get_project(project_id, user_id, db)
    script = await _get_latest_script(project_id, db)

    if script is None:
        raise HTTPException(status_code=400, detail="No script to approve")

    script.status = "approved"
    project.script_status = "locked"
    project.current_stage = "assets"
    await db.commit()

    return {"project_id": project_id, "status": "approved", "next_stage": "assets"}


@router.post("/{project_id}/review/reject")
async def reject_script(
    project_id: str,
    notes: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Human rejects the script with revision notes."""
    project = await _get_project(project_id, user_id, db)
    script = await _get_latest_script(project_id, db)

    if script is None:
        raise HTTPException(status_code=400, detail="No script to reject")

    script.status = "draft"
    project.script_status = "revision"
    await db.commit()

    return {"project_id": project_id, "status": "rejected", "notes": notes}


# ── Helpers ──

async def _get_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    q = select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    result = await db.execute(q)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


async def _get_latest_script(project_id: str, db: AsyncSession) -> Script | None:
    # Filter out empty/broken records (id='' from failed runs), prefer latest version
    q = (
        select(Script)
        .where(Script.project_id == project_id, Script.id != "", Script.episode_count > 0)
        .order_by(Script.version.desc())
        .limit(1)
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def _run_script_generation(project_id: str, project: Project):
    """Background task: run Stage 1 generation and persist result."""
    from app.agents.pipeline_runner import PipelineRunner

    runner = PipelineRunner(project_id=project_id)
    # Build input from project
    input_data = {
        "project_id": project_id,
        "source_material": {
            "type": project.source_type,
            "raw_text": project.source_content or "",
        },
        "genre": project.genre or {},
        "target_spec": {
            "episode_count": project.episode_count,
            "duration_per_episode_seconds": (project.total_duration_seconds or 120) // max(project.episode_count, 1),
        },
        "style_preference": project.style_preference or {},
        "creative_direction": {},
    }

    result = await runner._run_stage1(input_data, emit=lambda e: None)

    # Persist to database
    # This needs a new DB session since this runs outside the request context
    from app.api.deps import async_session
    async with async_session() as db:
        script = Script(
            id=result.get("script_id", ""),
            project_id=project_id,
            owner_id=project.owner_id,
            version=result.get("version", 1),
            status=result.get("status", "draft"),
            content=result,
            episode_count=len(result.get("episodes", [])),
        )
        # Compute counts
        total_scenes = sum(len(ep.get("scenes", [])) for ep in result.get("episodes", []))
        total_segs = sum(
            len(sc.get("content", {}).get("segments", []))
            for ep in result.get("episodes", [])
            for sc in ep.get("scenes", [])
        )
        script.scene_count = total_scenes
        script.segment_count = total_segs
        script.character_count = len(result.get("character_index", []))
        script.location_count = len(result.get("location_index", []))
        script.prop_count = len(result.get("prop_index", []))

        # Latest review score
        review_history = result.get("review_history", [])
        if review_history:
            latest = review_history[-1]
            script.latest_score = latest.get("merged_score")
            script.latest_verdict = latest.get("verdict")

        db.add(script)

        # Update project reference
        p = await db.get(Project, project_id)
        if p:
            p.script_id = script.id
            p.script_version = script.version
            p.script_status = "review" if script.latest_score else "in_progress"

        await db.commit()
