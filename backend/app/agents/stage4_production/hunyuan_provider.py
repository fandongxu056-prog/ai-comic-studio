"""Tencent Hunyuan Image Generation Provider (TokenHub).

Endpoint: POST https://tokenhub.tencentmaas.com/v1/api/image/lite
Auth: Bearer sk-xxx
Model: hy-image-lite (fast, synchronous)

Style consistency: All prompts are prefixed with "日漫动画风格" and end with
"anime art style" — enforced by _ensure_anime_style().
"""

import time
from typing import Optional

import httpx

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

    def __init__(self, api_key: str):
        self.api_key = api_key
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
        """Generate a single anime-style image via TokenHub lite endpoint.

        Style consistency guarantee:
        - Every prompt is prefixed with "日漫动画风格"
        - Conflicting terms (realistic, 3D, photograph) are removed
        - Negative prompt is injected into the positive prompt
          (lite endpoint may not support separate negative_prompt param)
        """
        client = await self._get_client()
        start_time = time.time()

        # Build unified prompt with anime style enforcement
        enhanced_prompt = self._ensure_anime_style(prompt, negative_prompt)

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
        """Guarantee consistent anime style across ALL generated images.

        Strategy:
        1. Remove conflicting style keywords (realistic, photorealistic, 3D, etc.)
        2. Prefix with "日漫动画风格" if not present
        3. Append "anime art style" if not present
        4. Inject negative constraints directly into the prompt
        """
        # Remove conflicting style terms
        conflicting = [
            "realistic", "photorealistic", "3D render", "3d render",
            "8k photo", "photograph", "hyper-realistic", "photo-realistic",
            "realistic face", "realistic skin",
        ]
        cleaned = prompt
        for term in conflicting:
            cleaned = cleaned.replace(term, "")
            cleaned = cleaned.replace(term.capitalize(), "")

        # Build the final prompt with anime style guarantee
        parts = []

        # 1. Anime style prefix
        if "日漫" not in cleaned and "动漫" not in cleaned:
            parts.append("日漫动画风格")

        # 2. Cleaned prompt
        parts.append(cleaned.strip())

        # 3. Negative constraints (lite endpoint: inject into prompt)
        style_constraints = [
            "flat color illustration",
            "clean line art",
            "consistent anime character design",
            "no realistic textures",
            "no 3D rendering",
            "no photographic details",
        ]
        parts.append(", ".join(style_constraints))

        # 4. Anime keyword
        if "anime" not in cleaned.lower():
            parts.append("anime art style")

        return ", ".join(p for p in parts if p)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
