"""Stage 4 Production Pipeline — deterministic execution (NOT agent-based).

Unlike Stages 1-3, this stage uses Celery Canvas for parallel task orchestration:
  ImageGen (parallel per shot) → VideoGen (parallel) → TTSGen (parallel) → Compositor → Export

Architecture:
- Provider abstraction layer: ImageProvider | VideoProvider | TTSProvider
- Celery Canvas: chain(chord(images), chord(videos), chord(audio), composite)
- Cost tracking: every API call records cost via CostService
- Progress: SSE updates sent to frontend after each chord completes

Design reference: docs/agent-collaboration-protocol.md §4 (note: Stage 4 is Pipeline, not Agent)
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from celery import chain, chord, group

from app.agents.stage4_production.compositor import (
    CompositeRequest,
    CompositeResult,
    FFmpegCompositor,
)
from app.agents.stage4_production.image_gen import (
    ImageGenRequest,
    ImageGenResult,
    ImageProvider,
    create_image_provider,
)
from app.agents.stage4_production.tts_gen import (
    TTSRequest,
    TTSResult,
    TTSProvider,
    create_tts_provider,
)
from app.agents.stage4_production.video_gen import (
    VideoGenRequest,
    VideoGenResult,
    VideoProvider,
    create_video_provider,
)
from app.config import settings
from app.services.cost_service import ProjectCostTracker, get_tracker
from app.tasks.celery_app import celery_app


@dataclass
class ProductionJob:
    """A complete production job for one episode."""
    episode_index: int
    shot_ids: list[str]
    shot_data: dict
    output_dir: str
    status: str = "pending"  # pending → images → videos → audio → compositing → complete | failed
    progress: float = 0.0  # 0.0 - 1.0
    images_done: int = 0
    videos_done: int = 0
    audio_done: int = 0
    total_images: int = 0
    total_videos: int = 0
    total_audio: int = 0
    results: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProductionOrchestrator:
    """Orchestrates Stage 4 production for all episodes.

    Responsibilities:
    1. Extract shot data from ShotPlan (Stage 3 output)
    2. Create ProductionJob per episode
    3. Execute pipeline: Images → Videos → Audio → Composite
    4. Track progress and cost
    5. Generate ProductionOutput (Stage 4 output schema)
    """

    def __init__(
        self,
        project_id: str,
        image_provider: Optional[ImageProvider] = None,
        video_provider: Optional[VideoProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
    ):
        self.project_id = project_id
        self.image_provider = image_provider or create_image_provider(
            settings.image_provider,
            api_key=settings.openai_api_key,
        )
        self.video_provider = video_provider or create_video_provider(
            settings.video_provider or "kling",
            api_key="",
        )
        self.tts_provider = tts_provider or create_tts_provider(
            settings.tts_provider,
            api_key=settings.openai_api_key,
        )
        self.compositor = FFmpegCompositor()
        self.cost_tracker = get_tracker(project_id)
        self.jobs: dict[int, ProductionJob] = {}

    def create_jobs_from_shot_plan(self, shot_plan: dict, output_dir: str) -> list[ProductionJob]:
        """Parse ShotPlan into per-episode ProductionJobs."""
        jobs = []
        for ep in shot_plan.get("episodes", []):
            ep_idx = ep.get("episode_index", 0)
            shot_ids = []
            shot_data = {}

            for scene in ep.get("scenes", []):
                for shot in scene.get("shots", []):
                    sid = shot["shot_id"]
                    shot_ids.append(sid)
                    shot_data[sid] = {
                        "prompt": shot["keyframe"]["image_prompt"]["positive"],
                        "negative_prompt": shot["keyframe"]["image_prompt"]["negative"],
                        "seed": shot["keyframe"]["image_prompt"]["seed"],
                        "width": shot["keyframe"]["image_prompt"]["model_params"].get("width", 1920),
                        "height": shot["keyframe"]["image_prompt"]["model_params"].get("height", 1080),
                        "dialogue": [
                            {
                                "character_id": d["character_id"],
                                "text": d["text"],
                                "voice_id": d.get("voice_id", ""),
                                "emotion": d.get("emotion", ""),
                            }
                            for d in shot.get("dialogue", [])
                        ],
                        "duration_ms": shot["duration_ms"],
                        "video_prompt": shot["keyframe"].get("video_prompt", {}),
                    }

            total_shots = len(shot_ids)
            total_dialogues = sum(len(shot_data[s]["dialogue"]) for s in shot_ids)

            job = ProductionJob(
                episode_index=ep_idx,
                shot_ids=shot_ids,
                shot_data=shot_data,
                output_dir=output_dir,
                total_images=total_shots,
                total_videos=total_shots,
                total_audio=total_dialogues,
            )
            self.jobs[ep_idx] = job
            jobs.append(job)

        return jobs

    async def execute_job(self, job: ProductionJob) -> ProductionJob:
        """Execute a single episode's production pipeline."""
        job.status = "images"
        job.started_at = datetime.now(timezone.utc).isoformat()

        try:
            # Phase 1: Generate all images in parallel
            await self._run_image_phase(job)
            if job.errors:
                raise Exception(f"Image phase errors: {job.errors[:3]}")

            # Phase 2: Generate videos from images
            await self._run_video_phase(job)
            if job.errors:
                raise Exception(f"Video phase errors: {job.errors[:3]}")

            # Phase 3: Generate TTS audio
            await self._run_audio_phase(job)
            if job.errors:
                raise Exception(f"Audio phase errors: {job.errors[:3]}")

            # Phase 4: Composite into final video
            await self._run_composite_phase(job)

            job.status = "complete"
        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))

        job.completed_at = datetime.now(timezone.utc).isoformat()
        return job

    async def _run_image_phase(self, job: ProductionJob):
        """Generate all keyframe images in parallel."""
        tasks = []
        for sid in job.shot_ids:
            data = job.shot_data[sid]
            req = ImageGenRequest(
                shot_id=sid,
                prompt=data["prompt"],
                negative_prompt=data["negative_prompt"],
                seed=data["seed"],
                width=data.get("width", 1920),
                height=data.get("height", 1080),
            )

            # Estimate cost before calling
            est_cost = self.image_provider.estimate_cost(req)
            self.cost_tracker.record_estimate(sid, "image", est_cost)

            tasks.append(self.image_provider.generate(req))

        results: list[ImageGenResult] = await asyncio.gather(*tasks)

        for r in results:
            job.results[r.shot_id] = {"image": r}
            if r.success:
                job.images_done += 1
                self.cost_tracker.record_actual(r.shot_id, "image", r.cost_usd)
                # Update shot_data with image URL for next phase
                job.shot_data[r.shot_id]["image_url"] = r.image_url
            else:
                job.errors.append(f"Image {r.shot_id}: {r.error_message}")

        job.progress = 0.25

    async def _run_video_phase(self, job: ProductionJob):
        """Generate video segments from keyframe images."""
        tasks = []
        for sid in job.shot_ids:
            data = job.shot_data[sid]
            vp = data.get("video_prompt", {})

            req = VideoGenRequest(
                shot_id=sid,
                start_frame_url=data.get("image_url", ""),
                motion_prompt=vp.get("motion_description", ""),
                duration_ms=data.get("duration_ms", 3000),
                motion_strength=vp.get("motion_strength", 0.7),
                seed=data["seed"],
            )

            est_cost = self.video_provider.estimate_cost(req)
            self.cost_tracker.record_estimate(sid, "video", est_cost)

            tasks.append(self.video_provider.generate(req))

        results: list[VideoGenResult] = await asyncio.gather(*tasks)

        for r in results:
            job.results[r.shot_id]["video"] = r
            if r.success:
                job.videos_done += 1
                self.cost_tracker.record_actual(r.shot_id, "video", r.cost_usd)
                job.shot_data[r.shot_id]["video_url"] = r.video_url
            else:
                job.errors.append(f"Video {r.shot_id}: {r.error_message}")

        job.progress = 0.50

    async def _run_audio_phase(self, job: ProductionJob):
        """Generate TTS audio for all dialogue segments."""
        tasks = []
        for sid in job.shot_ids:
            for dlg in job.shot_data[sid]["dialogue"]:
                req = TTSRequest(
                    shot_id=sid,
                    character_id=dlg["character_id"],
                    text=dlg["text"],
                    voice_id=dlg.get("voice_id", ""),
                    emotion=dlg.get("emotion", ""),
                )
                tasks.append(self.tts_provider.generate(req))

        results: list[TTSResult] = await asyncio.gather(*tasks)

        task_idx = 0
        for sid in job.shot_ids:
            for i, dlg in enumerate(job.shot_data[sid]["dialogue"]):
                r = results[task_idx] if task_idx < len(results) else TTSResult(sid, False, error_message="missing")
                job.shot_data[sid]["dialogue"][i]["audio_result"] = r
                if r.success:
                    job.audio_done += 1
                    self.cost_tracker.record_actual(sid, "tts", r.cost_usd)
                task_idx += 1

        job.progress = 0.75

    async def _run_composite_phase(self, job: ProductionJob):
        """Composite all assets into final video."""
        segments = []
        for sid in job.shot_ids:
            data = job.shot_data[sid]
            segments.append({
                "shot_id": sid,
                "image_path": data.get("image_url", ""),
                "video_path": data.get("video_url", ""),
                "duration_ms": data.get("duration_ms", 3000),
                "subtitle_text": " ".join(
                    d["text"] for d in data.get("dialogue", [])
                    if d.get("audio_result") and d["audio_result"].success
                ),
            })

        output_path = str(Path(job.output_dir) / f"episode_{job.episode_index:03d}.mp4")

        result: CompositeResult = await self.compositor.composite(
            CompositeRequest(
                episode_index=job.episode_index,
                title=f"Episode {job.episode_index}",
                shot_segments=segments,
                output_path=output_path,
                resolution="1920x1080",
            )
        )

        job.results["composite"] = result
        if result.success:
            job.progress = 1.0
        else:
            job.errors.append(f"Compositing failed: {result.error_message}")

    def generate_output(self) -> dict:
        """Generate ProductionOutput (Stage 4 output schema)."""
        generated_assets = {}
        task_log = []
        final_videos = []

        for job in self.jobs.values():
            for sid in job.shot_ids:
                r = job.results.get(sid, {})
                img: ImageGenResult = r.get("image")
                vid: VideoGenResult = r.get("video")

                generated_assets[sid] = {
                    "shot_id": sid,
                    "keyframe_image": {
                        "url": img.image_url if img and img.success else "",
                        "resolution": "1920x1080",
                        "seed_used": img.seed_used if img else 0,
                        "cost_usd": img.cost_usd if img else 0,
                    } if img else None,
                    "video_segment": {
                        "url": vid.video_url if vid and vid.success else "",
                        "duration_ms": vid.duration_ms if vid else 0,
                        "cost_usd": vid.cost_usd if vid else 0,
                    } if vid else None,
                    "status": "complete" if (img and img.success) else "failed",
                }

                if img:
                    task_log.append({
                        "shot_id": sid,
                        "type": "image_gen",
                        "status": "succeeded" if img.success else "failed",
                        "provider": self.image_provider.provider_name,
                        "cost_usd": img.cost_usd,
                    })

            # Composite result
            comp = job.results.get("composite")
            if isinstance(comp, CompositeResult) and comp.success:
                final_videos.append({
                    "episode_index": job.episode_index,
                    "output_url": comp.output_path,
                    "local_path": comp.output_path,
                    "format": "mp4",
                    "codec": "h264",
                    "resolution": "1920x1080",
                    "fps": 24,
                    "duration_ms": 0,
                    "file_size_bytes": comp.file_size_bytes,
                    "has_subtitles": True,
                })

        cost_summary = self.cost_tracker.summary()

        return {
            "production_id": self.project_id,
            "project_id": self.project_id,
            "version": 1,
            "total_duration_seconds": 0,
            "generated_assets": {"by_shot_id": generated_assets},
            "final_videos": final_videos,
            "task_log": task_log,
            "cost_report": {
                "total_cost_usd": cost_summary["total_cost_usd"],
                "breakdown": cost_summary["by_provider"],
                "budget_compliance": "under_budget" if not cost_summary["over_budget"] else "exceeded_warn",
            },
        }


def build_production_pipeline(
    episode_index: int,
    shot_ids: list[str],
    shot_data: dict,
    output_path: str,
) -> chain:
    """Build a Celery Canvas pipeline for one episode (used by Celery tasks)."""
    from app.tasks.image_tasks import generate_keyframe_image
    from app.tasks.video_tasks import composite_episode_video, generate_shot_video
    from app.tasks.tts_tasks import generate_dialogue_audio

    image_tasks = group(
        generate_keyframe_image.s(
            shot_id=sid,
            prompt=shot_data[sid]["prompt"],
            negative_prompt=shot_data[sid]["negative_prompt"],
            seed=shot_data[sid]["seed"],
        )
        for sid in shot_ids
    )

    video_tasks = group(
        generate_shot_video.s(
            shot_id=sid,
            start_frame_url=shot_data[sid].get("image_url", ""),
            end_frame_url=shot_data[sid].get("end_frame_url", ""),
            motion_prompt=shot_data[sid].get("motion_description", ""),
        )
        for sid in shot_ids
    )

    tts_tasks = group(
        generate_dialogue_audio.s(
            shot_id=sid,
            character_id=dlg["character_id"],
            text=dlg["text"],
            voice_id=dlg.get("voice_id", ""),
        )
        for sid in shot_ids
        for dlg in shot_data[sid].get("dialogue", [])
    )

    composite_task = composite_episode_video.s(
        episode_index=episode_index,
        shot_ids=shot_ids,
        output_path=output_path,
    )

    return chain(chord(image_tasks)(), chord(video_tasks)(), chord(tts_tasks)(), composite_task)
