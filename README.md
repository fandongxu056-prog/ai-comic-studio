# AI 漫剧创作平台 (AI Comic Studio)

AI-native comic animation creation SaaS platform for 16:9 horizontal content. Covers the full pipeline: Script → Asset Design → Storyboard → Production.

## Architecture

```
Stage 1 (Multi-Agent)    Stage 2 (Multi-Agent)    Stage 3 (Multi-Agent)   Stage 4 (Pipeline)
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  剧本创作     │  ────→ │  资产设计     │  ────→ │  分镜脚本     │  ────→ │  制作合成     │
│  ScriptWriter│        │ CharDesigner │        │ ShotComposer │        │ ImageGen     │
│  DramaCritic │        │ SceneDesigner│        │ PacingDir    │        │ VideoGen     │
│  StyleGuard  │        │ PropDesigner │        │ ContinuityChk│        │ TTSGen       │
│              │        │ConsistencyAud│        │              │        │ Compositor   │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
      ↓                       ↓                       ↓                       ↓
structured_script.json   asset_profiles.json     shot_plan.json         final_video.mp4
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI + LangGraph + Celery |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS 4 + shadcn/ui |
| Database | PostgreSQL + Redis + MinIO (S3) |
| Deployment | Docker Compose |

## Quick Start

```bash
# Clone & setup
git clone <repo-url> && cd ai-comic-studio

# Copy environment config
cp docker/.env.example docker/.env

# Start all services
docker compose -f docker/docker-compose.yml up -d
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

## Project Structure

```
ai-comic-studio/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/v1/       # REST API endpoints
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── agents/       # LangGraph agent definitions
│   │   ├── contracts/    # Cross-stage continuity contracts
│   │   ├── services/     # Business logic
│   │   ├── tasks/        # Celery async tasks
│   │   └── utils/        # Utilities
│   └── tests/
├── frontend/             # React frontend
│   └── src/
│       ├── app/          # Page routes
│       ├── components/   # UI components
│       ├── stores/       # Zustand state
│       └── services/     # API client
├── docs/                 # Design documents
│   ├── schema-design.md
│   └── agent-collaboration-protocol.md
└── docker/               # Docker deployment
```

## Documentation

- [Schema Design](docs/schema-design.md) — Four-stage data contract definitions
- [Agent Collaboration Protocol](docs/agent-collaboration-protocol.md) — Multi-Agent collaboration & QC standards
