"""MiniMax (Hailuo) Video Generation Provider.

Endpoint: POST https://api.minimax.chat/v1/video_generation
Auth: Bearer <api_key>
Model: video-01 (image-to-video), T2V-01 (text-to-video)
Flow: Submit task → Poll GET /v1/query/video_generation?task_id={id} → Get video URL

Style: dynamic via StyleInjector (anime/realistic/etc.).
"""

import asyncio
import time
from typing import Optional

import httpx

from app.agents.stage4_production.style_injector import StyleInjector

MINIMAX_BASE_URL = "https://api.minimax.chat"
MINIMAX_MODEL = "video-01"  # image-to-video model


class MiniMaxVideoResult:
    """Result from MiniMax video generation."""

    def __init__(
        self,
        shot_id: str,
        success: bool,
        video_url: str = "",
        task_id: str = "",
        duration_ms: int = 0,
        generation_time_ms: int = 0,
        cost_estimate_usd: float = 0.0,
        error_message: str = "",
    ):
        self.shot_id = shot_id
        self.success = success
        self.video_url = video_url
        self.task_id = task_id
        self.duration_ms = duration_ms
        self.generation_time_ms = generation_time_ms
        self.cost_estimate_usd = cost_estimate_usd
        self.error_message = error_message


class MiniMaxVideoProvider:
    """MiniMax (Hailuo) video generation via async submit + poll API.

    Features:
    - Image-to-video: animate a keyframe image with a motion prompt
    - Text-to-video: generate video from text description (fallback)
    - Async polling with configurable timeout
    - Anime-aware prompt enhancement
    - Cost estimation ($0.10-$0.50 per generation)

    API Reference: https://platform.minimax.chat
    """

    def __init__(self, api_key: str, model: str = MINIMAX_MODEL, art_style: str = "anime"):
        self.api_key = api_key
        self.model = model
        self.art_style = art_style
        self.injector = StyleInjector(art_style)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=MINIMAX_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def generate(
        self,
        shot_id: str,
        start_frame_url: str = "",
        prompt: str = "",
        duration_ms: int = 3000,
        resolution: str = "1280x720",
        max_poll_seconds: int = 120,
    ) -> MiniMaxVideoResult:
        """Generate a video segment from an image (image-to-video).

        Args:
            shot_id: Shot identifier for tracking.
            start_frame_url: URL of the keyframe image to animate.
            prompt: Motion description (e.g., "gentle camera pan, character blinking").
            duration_ms: Target video duration in milliseconds.
            resolution: Output resolution (width x height).
            max_poll_seconds: Maximum time to wait for generation.

        Returns:
            MiniMaxVideoResult with video_url on success.
        """
        client = await self._get_client()
        start_time = time.time()

        # Enhance prompt for anime/manga consistency
        motion_prompt = self._build_motion_prompt(prompt)

        try:
            # Step 1: Submit generation task
            body = {
                "model": self.model,
                "prompt": motion_prompt[:1000],
                "duration": max(duration_ms, 2000),  # Minimum 2 seconds
            }

            # Image-to-video: include the first frame
            if start_frame_url:
                body["first_frame_image"] = start_frame_url

            print(f"  [MiniMax] Submitting {shot_id}... duration={duration_ms}ms")
            resp = await client.post("/v1/video_generation", json=body)
            resp.raise_for_status()
            data = resp.json()

            # Check for API-level errors
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                return MiniMaxVideoResult(
                    shot_id=shot_id,
                    success=False,
                    error_message=f"API error {base_resp.get('status_code')}: {base_resp.get('status_msg', '')}",
                )

            task_id = data.get("task_id", "")
            if not task_id:
                return MiniMaxVideoResult(
                    shot_id=shot_id,
                    success=False,
                    error_message="No task_id in response",
                )

            # Step 2: Poll for completion
            poll_interval = 3.0  # seconds between polls
            max_polls = int(max_poll_seconds / poll_interval)

            for poll_count in range(max_polls):
                await asyncio.sleep(poll_interval)

                query_resp = await client.get(
                    "/v1/query/video_generation",
                    params={"task_id": task_id},
                )
                query_resp.raise_for_status()
                query_data = query_resp.json()

                status = query_data.get("status", "")

                if status == "Success":
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    video_url = query_data.get("video_url", "")

                    print(f"  [MiniMax] {shot_id} OK ({elapsed_ms}ms, url={video_url[:60]}...)")
                    return MiniMaxVideoResult(
                        shot_id=shot_id,
                        success=True,
                        video_url=video_url,
                        task_id=task_id,
                        duration_ms=duration_ms,
                        generation_time_ms=elapsed_ms,
                        cost_estimate_usd=self._estimate_cost(duration_ms),
                    )

                elif status == "Failed":
                    err_msg = query_data.get("error", {}).get("message", "Unknown error")
                    return MiniMaxVideoResult(
                        shot_id=shot_id,
                        success=False,
                        task_id=task_id,
                        error_message=err_msg,
                    )

                elif status == "Processing" or status == "Queueing":
                    if poll_count % 5 == 0:
                        print(f"  [MiniMax] {shot_id} still processing... ({poll_count+1}/{max_polls})")
                    continue

                else:
                    print(f"  [MiniMax] {shot_id} unknown status: {status}")

            # Timeout
            return MiniMaxVideoResult(
                shot_id=shot_id,
                success=False,
                task_id=task_id,
                error_message=f"Timeout after {max_poll_seconds}s",
            )

        except httpx.HTTPStatusError as e:
            return MiniMaxVideoResult(
                shot_id=shot_id,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            return MiniMaxVideoResult(
                shot_id=shot_id,
                success=False,
                error_message=str(e),
            )

    def _build_motion_prompt(self, prompt: str) -> str:
        """Build a motion-aware prompt with style-appropriate hints.

        MiniMax works best with clear, action-oriented prompts describing
        what should MOVE in the scene, not what the scene contains.
        """
        return self.injector.enhance_motion_prompt(prompt)

    def _estimate_cost(self, duration_ms: int) -> float:
        """Estimate cost based on video duration.

        MiniMax pricing (approximate, as of 2025):
        - video-01: ~$0.03/second for basic generation
        - Shorter videos are proportionally cheaper
        """
        seconds = max(duration_ms / 1000.0, 2.0)
        return round(seconds * 0.03, 4)

    @property
    def provider_name(self) -> str:
        return "minimax"

    @property
    def model_name(self) -> str:
        return self.model

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
