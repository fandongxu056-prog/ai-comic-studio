"""Master Pipeline Runner — wires all 4 stages together.

This is the top-level integration layer. It:
1. Creates the Orchestrator with initial state
2. Runs Stage 1 (Script) → Stage 2 (Assets) → Stage 3 (Storyboard) → Stage 4 (Production)
3. Validates cross-stage contracts at each transition
4. Manages human-in-the-loop checkpoints
5. Streams progress via SSE

Usage:
  runner = PipelineRunner(project_id)
  await runner.run_full_pipeline(input_data, callbacks)
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

from app.agents.orchestrator import (
    Orchestrator,
    PipelineState,
    Stage,
    StageStatus,
    get_next_stage,
)
from app.contracts.s1_to_s2 import ScriptToAssetContract
from app.contracts.s2_to_s3 import AssetToStoryboardContract
from app.contracts.s3_to_s4 import StoryboardToProductionContract


@dataclass
class PipelineEvent:
    """SSE event emitted during pipeline execution."""
    event_type: str  # stage_start | stage_progress | review_complete | stage_complete | contract_check | error
    stage: str
    data: dict = field(default_factory=dict)


class PipelineRunner:
    """Runs the full 4-stage creative pipeline with contract validation."""

    def __init__(self, project_id: str, llm_service: Any = None):
        """Initialize the pipeline runner.

        Args:
            project_id: The project to run.
            llm_service: Optional LLMService instance. If None, attempts to create
                         from settings (requires API keys in config).
        """
        self.project_id = project_id
        self.state = PipelineState(project_id=project_id)

        # LLM service — try to create from settings if not provided
        if llm_service is not None:
            self.llm_service = llm_service
        else:
            try:
                from app.services.llm_service import get_llm_service
                self.llm_service = get_llm_service()
            except Exception:
                self.llm_service = None

        # Cross-stage contracts
        self.contract_s1_s2 = ScriptToAssetContract()
        self.contract_s2_s3 = AssetToStoryboardContract()
        self.contract_s3_s4 = StoryboardToProductionContract()

        # Stage outputs (accumulated)
        self.script_output: dict = {}
        self.asset_output: dict = {}
        self.storyboard_output: dict = {}
        self.production_output: dict = {}

    async def run_full_pipeline(
        self,
        input_data: dict,
        on_event: Optional[Callable[[PipelineEvent], None]] = None,
    ) -> dict:
        """Run the complete pipeline from Stage 0 → Stage 4.

        Args:
            input_data: ProjectInput (Stage 0) — must include:
                project_id, source_material, creative_direction, target_spec, genre, style_preference
            on_event: Optional callback for SSE progress events

        Returns:
            Complete pipeline results with all stage outputs
        """
        events: list[PipelineEvent] = []

        def emit(event: PipelineEvent):
            events.append(event)
            if on_event:
                on_event(event)

        try:
            # ── Stage 1: Script ──
            emit(PipelineEvent("stage_start", "script", {"message": "Starting script generation"}))

            self.script_output = await self._run_stage1(input_data, emit)

            if self.script_output.get("status") == "escalated":
                emit(PipelineEvent("stage_complete", "script", {"verdict": "escalated_to_human"}))
                return {
                    "status": "escalated",
                    "stage": "script",
                    "script": self.script_output,
                }

            self.state.complete_stage(self.script_output.get("script_id", ""))

            # Contract check: S1 → S2
            emit(PipelineEvent("contract_check", "script→assets", {"contract": "s1_to_s2"}))
            contract_result = await self.contract_s1_s2.validate(
                input_data, self.script_output
            )
            if not contract_result.can_proceed:
                emit(PipelineEvent("error", "script→assets", {
                    "message": f"Contract validation failed: {contract_result.blocker_count} blockers",
                    "violations": [v.model_dump() for v in contract_result.violations],
                }))
                return {
                    "status": "failed",
                    "stage": "script→assets",
                    "contract_violations": [v.model_dump() for v in contract_result.violations],
                }

            # Auto-approve check
            review_history = self.script_output.get("review_history", [])
            last_review = review_history[-1] if review_history else {}
            if last_review.get("merged_score", 0) >= 85:
                self.state.process_human_decision("approved", "Auto-approved: score >= 85")
                emit(PipelineEvent("stage_complete", "script", {
                    "verdict": "auto_approved",
                    "score": last_review.get("merged_score"),
                    "rounds": len(review_history),
                }))
            else:
                emit(PipelineEvent("stage_complete", "script", {
                    "verdict": "awaiting_human",
                    "score": last_review.get("merged_score"),
                    "rounds": len(review_history),
                }))

            # ── Stage 2: Assets ──
            emit(PipelineEvent("stage_start", "assets", {"message": "Starting asset design"}))
            self.asset_output = await self._run_stage2(input_data, self.script_output, emit)
            self.state.complete_stage(self.asset_output.get("asset_set_id", ""))

            # Contract check: S2 → S3
            emit(PipelineEvent("contract_check", "assets→storyboard", {"contract": "s2_to_s3"}))
            contract_result = await self.contract_s2_s3.validate(
                self.script_output, self.asset_output
            )
            if not contract_result.can_proceed:
                emit(PipelineEvent("error", "assets→storyboard", {
                    "violations": [v.model_dump() for v in contract_result.violations],
                }))
                return {"status": "failed", "stage": "assets→storyboard"}

            emit(PipelineEvent("stage_complete", "assets", {"verdict": "completed"}))

            # ── Stage 3: Storyboard ──
            emit(PipelineEvent("stage_start", "storyboard", {"message": "Starting storyboard composition"}))
            self.storyboard_output = await self._run_stage3(
                input_data, self.script_output, self.asset_output, emit
            )
            self.state.complete_stage(self.storyboard_output.get("storyboard_id", ""))

            # Contract check: S3 → S4
            emit(PipelineEvent("contract_check", "storyboard→production", {"contract": "s3_to_s4"}))
            contract_result = await self.contract_s3_s4.validate(
                self.storyboard_output, {}
            )
            if not contract_result.can_proceed:
                emit(PipelineEvent("error", "storyboard→production", {
                    "violations": [v.model_dump() for v in contract_result.violations],
                }))
                return {"status": "failed", "stage": "storyboard→production"}

            emit(PipelineEvent("stage_complete", "storyboard", {"verdict": "completed"}))

            # ── Stage 4: Production ──
            emit(PipelineEvent("stage_start", "production", {"message": "Starting video production pipeline"}))
            self.production_output = await self._run_stage4(
                input_data, self.storyboard_output, emit
            )
            self.state.complete_stage(self.production_output.get("production_id", ""))
            self.state.current_stage = Stage.COMPLETE

            emit(PipelineEvent("stage_complete", "production", {"verdict": "completed"}))

            return {
                "status": "complete",
                "project_id": self.project_id,
                "script": self.script_output,
                "assets": self.asset_output,
                "storyboard": self.storyboard_output,
                "production": self.production_output,
                "events": [e.__dict__ for e in events],
                "state": self.state.summary(),
            }

        except Exception as e:
            emit(PipelineEvent("error", self.state.current_stage.value, {"message": str(e)}))
            return {
                "status": "failed",
                "error": str(e),
                "stage": self.state.current_stage.value,
                "events": [e.__dict__ for e in events],
            }

    # ── Stage Runners ──

    async def _run_stage1(self, input_data: dict, emit) -> dict:
        """Run Stage 1: Script generation with review loop.

        Passes the full project input to the Writer agent and runs
        the DramaCritic + StyleGuard parallel review loop via LangGraph.
        """
        from app.agents.stage1_script.graph import create_stage1_graph

        graph = create_stage1_graph(llm_service=self.llm_service)

        initial_state = {
            "project_id": self.project_id,
            "iteration": 1,
            "max_iterations": 3,
            "script": {},
            "input_data": input_data,
            "drama_critic_feedback": None,
            "style_guard_feedback": None,
            "merged_verdict": "pending",
            "merged_score": 0,
            "blocker_count": 0,
            "review_history": [],
            "error": None,
        }

        try:
            result = await graph.ainvoke(initial_state)
        except Exception as e:
            emit(PipelineEvent("error", "script", {"message": f"Graph execution failed: {e}"}))
            return {"status": "failed", "error": str(e)}

        script = result.get("script", {})

        emit(PipelineEvent("review_complete", "script", {
            "verdict": result.get("merged_verdict"),
            "score": result.get("merged_score"),
            "rounds": result.get("iteration"),
            "blocker_count": result.get("blocker_count"),
        }))

        return script

    async def _run_stage2(self, input_data: dict, script_output: dict, emit) -> dict:
        """Run Stage 2: Asset design with parallel design + audit."""
        from app.agents.stage2_asset.graph import create_stage2_graph

        graph = create_stage2_graph()
        initial_state = {
            "project_id": self.project_id,
            "iteration": 1,
            "max_iterations": 3,
            "characters": [],
            "locations": [],
            "props": [],
            "style_manifest": {},
            "audit_feedback": None,
            "merged_verdict": "pending",
            "merged_score": 0,
            "blocker_count": 0,
            "script": script_output,
            "style_preference": input_data.get("style_preference", {}),
            "consistency_requirements": {},
            "review_history": [],
            "error": None,
        }

        result = await graph.ainvoke(initial_state)
        return {
            "asset_set_id": self.project_id,
            "characters": result.get("characters", []),
            "locations": result.get("locations", []),
            "props": result.get("props", []),
            "style_manifest": result.get("style_manifest", {}),
        }

    async def _run_stage3(
        self, input_data: dict, script_output: dict, asset_output: dict, emit
    ) -> dict:
        """Run Stage 3: Storyboard composition with parallel review."""
        from app.agents.stage3_storyboard.graph import create_stage3_graph

        graph = create_stage3_graph()
        initial_state = {
            "project_id": self.project_id,
            "iteration": 1,
            "max_iterations": 3,
            "shot_plan": {},
            "assets": asset_output,
            "script": script_output,
            "continuity_rules": script_output.get("global_context", {}).get("continuity_rules", []),
            "pacing_feedback": None,
            "continuity_feedback": None,
            "merged_verdict": "pending",
            "merged_score": 0,
            "blocker_count": 0,
            "review_history": [],
            "error": None,
        }

        result = await graph.ainvoke(initial_state)
        return result.get("shot_plan", {})

    async def _run_stage4(self, input_data: dict, storyboard_output: dict, emit) -> dict:
        """Run Stage 4: Production pipeline."""
        from app.agents.stage4_production.pipeline import ProductionOrchestrator

        orchestrator = ProductionOrchestrator(project_id=self.project_id)
        jobs = orchestrator.create_jobs_from_shot_plan(
            storyboard_output,
            output_dir=f"./outputs/{self.project_id}",
        )

        for job in jobs:
            await orchestrator.execute_job(job)
            emit(PipelineEvent("stage_progress", "production", {
                "episode": job.episode_index,
                "status": job.status,
                "progress": job.progress,
                "images_done": job.images_done,
                "videos_done": job.videos_done,
            }))

        return orchestrator.generate_output()

    # ── Persistence ──

    async def save_outputs(self) -> dict[str, str]:
        """Persist all accumulated stage outputs to the database.

        Returns a dict mapping stage → artifact_id.
        """
        from app.api.deps import async_session

        saved = {}

        async with async_session() as db:
            # Stage 1: Script
            if self.script_output and self.script_output.get("script_id"):
                saved["script"] = await self._persist_script(db)

            # Stage 2: Assets
            if self.asset_output and self.asset_output.get("asset_set_id"):
                saved["assets"] = await self._persist_assets(db)

            # Stage 3: Storyboard
            if self.storyboard_output and self.storyboard_output.get("storyboard_id"):
                saved["storyboard"] = await self._persist_storyboard(db)

            # Stage 4: Production
            if self.production_output and self.production_output.get("production_id"):
                saved["production"] = await self._persist_production(db)

            await db.commit()

        return saved

    async def _persist_script(self, db) -> str:
        """Persist Stage 1 script output to database."""
        from app.models.project import Project
        from app.models.script import Script

        sid = self.script_output.get("script_id", "")
        script = Script(
            id=sid,
            project_id=self.project_id,
            owner_id="dev-user-001",  # TODO: get from auth context
            version=self.script_output.get("version", 1),
            status=self.script_output.get("status", "draft"),
            content=self.script_output,
        )

        # Compute denormalized counts
        episodes = self.script_output.get("episodes", [])
        script.episode_count = len(episodes)
        script.scene_count = sum(len(ep.get("scenes", [])) for ep in episodes)
        script.segment_count = sum(
            len(sc.get("content", {}).get("segments", []))
            for ep in episodes
            for sc in ep.get("scenes", [])
        )
        script.character_count = len(self.script_output.get("character_index", []))
        script.location_count = len(self.script_output.get("location_index", []))
        script.prop_count = len(self.script_output.get("prop_index", []))

        # Latest review
        review_history = self.script_output.get("review_history", [])
        if review_history:
            latest = review_history[-1]
            script.latest_score = latest.get("merged_score")
            script.latest_verdict = latest.get("verdict")

        db.add(script)

        # Update project reference
        project = await db.get(Project, self.project_id)
        if project:
            project.script_id = sid
            project.script_version = script.version
            project.script_status = "review" if script.latest_score else "in_progress"

        return sid

    async def _persist_assets(self, db) -> str:
        """Persist Stage 2 asset output."""
        from app.models.asset import AssetSet
        from app.models.project import Project

        aid = self.asset_output.get("asset_set_id", "")
        asset_set = AssetSet(
            id=aid,
            project_id=self.project_id,
            owner_id="dev-user-001",
            script_id=self.script_output.get("script_id"),
            version=self.asset_output.get("version", 1),
            status=self.asset_output.get("status", "draft"),
            content=self.asset_output,
            character_count=len(self.asset_output.get("characters", [])),
            location_count=len(self.asset_output.get("locations", [])),
            prop_count=len(self.asset_output.get("props", [])),
        )

        style = self.asset_output.get("style_manifest", {})
        asset_set.art_style = style.get("art_style")
        asset_set.global_style_seed = style.get("global_style_seed")

        db.add(asset_set)

        project = await db.get(Project, self.project_id)
        if project:
            project.asset_set_id = aid
            project.assets_version = asset_set.version
            project.assets_status = asset_set.status

        return aid

    async def _persist_storyboard(self, db) -> str:
        """Persist Stage 3 storyboard output."""
        from app.models.project import Project
        from app.models.storyboard import Storyboard

        sbid = self.storyboard_output.get("storyboard_id", "")
        episodes = self.storyboard_output.get("episodes", [])
        total_shots = sum(
            len(sc.get("shots", []))
            for ep in episodes
            for sc in ep.get("scenes", [])
        )
        total_duration = sum(
            shot.get("duration_ms", 0)
            for ep in episodes
            for sc in ep.get("scenes", [])
            for shot in sc.get("shots", [])
        )

        storyboard = Storyboard(
            id=sbid,
            project_id=self.project_id,
            owner_id="dev-user-001",
            script_id=self.script_output.get("script_id"),
            asset_set_id=self.asset_output.get("asset_set_id"),
            version=self.storyboard_output.get("version", 1),
            status=self.storyboard_output.get("status", "draft"),
            content=self.storyboard_output,
            episode_count=len(episodes),
            total_shots=total_shots,
            total_duration_ms=total_duration,
        )

        review_history = self.storyboard_output.get("review_history", [])
        if review_history:
            storyboard.latest_score = review_history[-1].get("merged_score")

        db.add(storyboard)

        project = await db.get(Project, self.project_id)
        if project:
            project.storyboard_id = sbid
            project.storyboard_version = storyboard.version
            project.storyboard_status = storyboard.status

        return sbid

    async def _persist_production(self, db) -> str:
        """Persist Stage 4 production output."""
        from app.models.production import Production
        from app.models.project import Project

        pid = self.production_output.get("production_id", "")
        gen_assets = self.production_output.get("generated_assets", {}).get("by_shot_id", {})
        shots_total = len(gen_assets)
        shots_completed = sum(1 for a in gen_assets.values() if a.get("status") == "complete")

        cost = self.production_output.get("cost_report", {})

        production = Production(
            id=pid,
            project_id=self.project_id,
            owner_id="dev-user-001",
            storyboard_id=self.storyboard_output.get("storyboard_id"),
            asset_set_id=self.asset_output.get("asset_set_id"),
            version=self.production_output.get("version", 1),
            status="completed",
            content=self.production_output,
            shots_total=shots_total,
            shots_completed=shots_completed,
            videos_exported=len(self.production_output.get("final_videos", [])),
            total_duration_seconds=self.production_output.get("total_duration_seconds", 0),
            total_cost_usd=cost.get("total_cost_usd", 0),
            budget_compliance=cost.get("budget_compliance"),
        )

        db.add(production)

        project = await db.get(Project, self.project_id)
        if project:
            project.production_id = pid
            project.production_version = production.version
            project.production_status = "completed"
            project.current_stage = "complete"

        return pid

    async def stream_events(self, input_data: dict) -> AsyncGenerator[str, None]:
        """Async generator for SSE streaming of pipeline events."""
        yield f"data: {{\"type\": \"pipeline_start\", \"project_id\": \"{self.project_id}\"}}\n\n"

        async def sse_emit(event: PipelineEvent):
            import json
            return f"data: {json.dumps({'type': event.event_type, 'stage': event.stage, **event.data})}\n\n"

        result = await self.run_full_pipeline(input_data, on_event=lambda e: None)
        yield f"data: {{\"type\": \"pipeline_complete\", \"status\": \"{result.get('status')}\"}}\n\n"
