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
from dataclasses import dataclass
from typing import AsyncGenerator, Callable, Optional

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
    data: dict


class PipelineRunner:
    """Runs the full 4-stage creative pipeline with contract validation."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.state = PipelineState(project_id=project_id)

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
            input_data: ProjectInput (Stage 0)
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
                return {"status": "failed", "stage": "script→assets", "contract_violations": contract_result.violations}

            # Human checkpoint (auto-approve if score >= 85)
            review = self.script_output.get("review_history", [{}])[-1] if self.script_output.get("review_history") else {}
            if review.get("total_score", 0) >= 85:
                self.state.process_human_decision("approved", "Auto-approved: score >= 85")
                emit(PipelineEvent("stage_complete", "script", {"verdict": "auto_approved"}))
            else:
                emit(PipelineEvent("stage_complete", "script", {"verdict": "awaiting_human"}))

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
        """Run Stage 1: Script generation with review loop."""
        from app.agents.stage1_script.graph import create_stage1_graph

        graph = create_stage1_graph()
        initial_state = {
            "project_id": self.project_id,
            "iteration": 1,
            "max_iterations": 3,
            "script": input_data,
            "drama_critic_feedback": None,
            "style_guard_feedback": None,
            "merged_verdict": "pending",
            "merged_score": 0,
            "blocker_count": 0,
            "review_history": [],
            "error": None,
        }

        result = await graph.ainvoke(initial_state)
        emit(PipelineEvent("stage_progress", "script", {
            "verdict": result.get("merged_verdict"),
            "score": result.get("merged_score"),
            "round": result.get("iteration"),
        }))

        return result.get("script", {})

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

    async def _run_stage3(self, input_data: dict, script_output: dict, asset_output: dict, emit) -> dict:
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

    async def stream_events(self, input_data: dict) -> AsyncGenerator[str, None]:
        """Async generator for SSE streaming of pipeline events."""
        async def sse_emit(event: PipelineEvent):
            import json
            return f"data: {json.dumps({'type': event.event_type, 'stage': event.stage, **event.data})}\n\n"

        # This would be used with FastAPI StreamingResponse
        yield "data: {\"type\": \"pipeline_start\", \"project_id\": \"" + self.project_id + "\"}\n\n"
        # ... pipeline execution with sse_emit for each event
        yield "data: {\"type\": \"pipeline_complete\"}\n\n"
