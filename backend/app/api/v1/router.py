"""API v1 router — aggregates all resource routers."""

from fastapi import APIRouter

from app.api.v1 import assets, auth, productions, projects, scripts, storyboards

api_router = APIRouter()

# Auth (no prefix — mounted at /api/v1/auth)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Stage 0: Project management
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Stage 1: Script
api_router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])

# Stage 2: Asset Design
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])

# Stage 3: Storyboard
api_router.include_router(storyboards.router, prefix="/storyboards", tags=["storyboards"])

# Stage 4: Production
api_router.include_router(productions.router, prefix="/productions", tags=["productions"])
