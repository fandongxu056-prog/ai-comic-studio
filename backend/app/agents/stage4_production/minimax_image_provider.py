"""MiniMax Image Generation Provider.

Endpoint: POST https://api.minimax.chat/v1/image_generation
Auth: Bearer <same MiniMax API key used for video>
Model: image-01 (supports both anime and photorealistic styles)

Uses the shared StyleInjector — style follows the project's art_style
preference (anime / realistic / 3d_render / etc.), NOT hardcoded anime.
"""

import asyncio
import time
from typing import Optional

import httpx

from app.agents.stage4_production.style_injector import StyleInjector

MINIMAX_BASE_URL = "https://api.minimax.chat"
MINIMAX_IMAGE_MODEL = "image-01"


class MiniMaxImageResult:
    """Result from MiniMax image generation."""

    def __init__(
        self,
        shot_id: str,
        success: bool,
        image_url: str = "",
        task_id: str = "",
        generation_time_ms: int = 0,
        cost_estimate_usd: float = 0.0,
        error_message: str = "",
    ):
        self.shot_id = shot_id
        self.success = success
        self.image_url = image_url
        self.task_id = task_id
        self.generation_time_ms = generation_time_ms
        self.cost_estimate_usd = cost_estimate_usd
        self.error_message = error_message


class MiniMaxImageProvider:
    """MiniMax image generation (image-01) with dynamic style injection.

    Uses the SAME MiniMax API key as video generation — no extra key needed.
    """

    def __init__(self, api_key: str, model: str = MINIMAX_IMAGE_MODEL, art_style: str = "anime"):
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
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        max_poll_seconds: int = 120,
    ) -> MiniMaxImageResult:
        """Generate a single keyframe image.

        Args:
            shot_id: Shot identifier.
            prompt: Image description (any language, max ~2000 chars).
            negative_prompt: What to avoid.
            aspect_ratio: "16:9" | "1:1" | "9:16" | "4:3" | "3:4".
            max_poll_seconds: Max wait time if task-based.

        Returns:
            MiniMaxImageResult with image_url on success.
        """
        client = await self._get_client()
        start_time = time.time()

        # Dynamic style injection (anime/realistic/etc. from art_style)
        enhanced = self.injector.enhance_prompt(prompt, negative_prompt)

        try:
            body = {
                "model": self.model,
                "prompt": enhanced[:2000],
                "aspect_ratio": aspect_ratio,
                "response_format": "url",
                "n": 1,
            }

            print(f"  [MiniMaxImg] Generating {shot_id} (style={self.art_style})...")
            resp = await client.post("/v1/image_generation", json=body)
            resp.raise_for_status()
            data = resp.json()

            # Check API-level error
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                return MiniMaxImageResult(
                    shot_id=shot_id, success=False,
                    error_message=f"API error {base_resp.get('status_code')}: {base_resp.get('status_msg', '')}",
                )

            # Path A: synchronous response with image_urls
            images = data.get("data", {}).get("image_urls", []) or data.get("image_urls", [])
            if images:
                elapsed = int((time.time() - start_time) * 1000)
                url = images[0] if isinstance(images[0], str) else images[0].get("url", "")
                print(f"  [MiniMaxImg] {shot_id} OK ({elapsed}ms)")
                return MiniMaxImageResult(
                    shot_id=shot_id, success=True, image_url=url,
                    generation_time_ms=elapsed, cost_estimate_usd=0.02,
                )

            # Path B: task-based (submit + poll)
            task_id = data.get("task_id", "")
            if task_id:
                poll_interval = 2.0
                max_polls = int(max_poll_seconds / poll_interval)
                for i in range(max_polls):
                    await asyncio.sleep(poll_interval)
                    q = await client.get("/v1/query/image_generation", params={"task_id": task_id})
                    q.raise_for_status()
                    qd = q.json()
                    if qd.get("status") == "Success":
                        urls = qd.get("data", {}).get("image_urls", []) or qd.get("image_urls", [])
                        if urls:
                            url = urls[0] if isinstance(urls[0], str) else urls[0].get("url", "")
                            elapsed = int((time.time() - start_time) * 1000)
                            return MiniMaxImageResult(
                                shot_id=shot_id, success=True, image_url=url,
                                task_id=task_id, generation_time_ms=elapsed,
                                cost_estimate_usd=0.02,
                            )
                    elif qd.get("status") == "Failed":
                        return MiniMaxImageResult(
                            shot_id=shot_id, success=False, task_id=task_id,
                            error_message=str(qd.get("error", "Unknown"))[:200],
                        )
                return MiniMaxImageResult(
                    shot_id=shot_id, success=False, task_id=task_id,
                    error_message=f"Timeout after {max_poll_seconds}s",
                )

            return MiniMaxImageResult(
                shot_id=shot_id, success=False,
                error_message=f"No image in response: {str(data)[:200]}",
            )

        except httpx.HTTPStatusError as e:
            return MiniMaxImageResult(
                shot_id=shot_id, success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            return MiniMaxImageResult(shot_id=shot_id, success=False, error_message=str(e))

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
