"""Tencent Hunyuan Image Generation Provider (TokenHub).

Endpoint: POST https://tokenhub.tencentmaas.com/v1/api/image/lite
Auth: Bearer sk-xxx
Model: hy-image-lite (fast, synchronous)

Style: dynamically injected from project art_style via StyleInjector
(anime / realistic / 3d_render / etc.) — no longer hardcoded anime.
"""

import time
from typing import Optional

import httpx

from app.agents.stage4_production.style_injector import StyleInjector

HUNYUAN_BASE_URL = "https://tokenhub.tencentmaas.com"
HUNYUAN_MODEL = "hy-image-lite"


class HunyuanImageResult:
    def __init__(self, shot_id: str, success: bool, image_url: str = "",
                 seed_used: int = 0, generation_time_ms: int = 0,
                 error_message: str = ""):
        self.shot_id = shot_id
        self.success = success
        self.image_url = image_url
        self.seed_used = seed_used
        self.generation_time_ms = generation_time_ms
        self.error_message = error_message


class HunyuanImageProvider:
    """Tencent Hunyuan image generation via TokenHub lite endpoint.

    Synchronous API — returns image URL immediately.
    All prompts are auto-injected with anime style keywords to ensure
    consistent visual style across every generated image.
    """

    def __init__(self, api_key: str, art_style: str = "anime"):
        self.api_key = api_key
        self.art_style = art_style
        self.injector = StyleInjector(art_style)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=HUNYUAN_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._client

    async def generate(
        self,
        shot_id: str,
        prompt: str,
        negative_prompt: str = "",
        seed: int = 0,
        resolution: str = "1280:720",
    ) -> HunyuanImageResult:
        """Generate a style-consistent image via TokenHub lite endpoint.

        Style follows self.art_style (anime/realistic/etc.) via StyleInjector.
        Negative prompt is merged into the positive prompt (lite endpoint
        may not support separate negative_prompt param).
        """
        client = await self._get_client()
        start_time = time.time()

        # Dynamic style injection
        enhanced_prompt = self.injector.enhance_prompt(prompt, negative_prompt)

        try:
            body = {
                "model": HUNYUAN_MODEL,
                "prompt": enhanced_prompt[:800],  # Lite endpoint prompt limit
                "rsp_img_type": "url",
            }

            print(f"  [Hunyuan] Generating {shot_id}... seed={seed}")
            print(f"  [Hunyuan] Prompt preview: {enhanced_prompt[:120]}...")

            resp = await client.post("/v1/api/image/lite", json=body)
            resp.raise_for_status()
            data = resp.json()

            elapsed_ms = int((time.time() - start_time) * 1000)

            images = data.get("data", [])
            if images:
                image_url = images[0].get("url", "")
                credits = data.get("usage", {}).get("credits", "?")
                print(f"  [Hunyuan] {shot_id} OK ({elapsed_ms}ms, credits={credits})")
                return HunyuanImageResult(
                    shot_id=shot_id,
                    success=True,
                    image_url=image_url,
                    seed_used=seed,
                    generation_time_ms=elapsed_ms,
                )
            else:
                return HunyuanImageResult(
                    shot_id=shot_id,
                    success=False,
                    error_message=f"No image in response: {str(data)[:200]}",
                )

        except httpx.HTTPStatusError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return HunyuanImageResult(
                shot_id=shot_id,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                generation_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return HunyuanImageResult(
                shot_id=shot_id,
                success=False,
                error_message=str(e),
                generation_time_ms=elapsed_ms,
            )

    def _ensure_anime_style(self, prompt: str, negative_prompt: str = "") -> str:
        """Legacy alias — delegates to dynamic StyleInjector (anime style)."""
        return self.injector.enhance_prompt(prompt, negative_prompt)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
