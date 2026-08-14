"""Qwen/Wanx Image Generation Provider (DashScope).

Endpoint: POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis
Model: wanx2.1-t2i-turbo
Auth: Bearer sk-xxx
Flow: Submit task → Poll GET /api/v1/tasks/{task_id} → Get image URL

Style: dynamic via StyleInjector (anime/realistic/etc.) — not hardcoded.
"""

import asyncio
import time
from typing import Optional

import httpx

from app.agents.stage4_production.style_injector import StyleInjector

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"
DASHSCOPE_MODEL = "wanx2.1-t2i-turbo"


class QwenImageResult:
    def __init__(self, shot_id: str, success: bool, image_url: str = "",
                 task_id: str = "", generation_time_ms: int = 0,
                 error_message: str = ""):
        self.shot_id = shot_id
        self.success = success
        self.image_url = image_url
        self.task_id = task_id
        self.generation_time_ms = generation_time_ms
        self.error_message = error_message


class QwenImageProvider:
    """Qwen/Wanx image generation via DashScope async API.

    Features:
    - Async submit + poll
    - Consistent anime style via prompt prefix (日漫动画风格)
    - Maximum 1024 chars prompt
    """

    def __init__(self, api_key: str, art_style: str = "anime"):
        self.api_key = api_key
        self.art_style = art_style
        self.injector = StyleInjector(art_style)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=DASHSCOPE_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                timeout=180.0,
            )
        return self._client

    async def generate(
        self,
        shot_id: str,
        prompt: str,
        negative_prompt: str = "",
        size: str = "1280*720",
    ) -> QwenImageResult:
        """Generate an anime-style image via Wanx.

        Args:
            shot_id: Identifier for this shot
            prompt: Image description (max 1024 chars)
            negative_prompt: Merged into prompt as avoidance instruction
            size: "1280*720" (16:9) or "1024*1024" (square)
        """
        client = await self._get_client()
        start_time = time.time()

        # Dynamic style injection
        enhanced_prompt = self.injector.enhance_prompt(prompt, negative_prompt)

        try:
            # Step 1: Submit task
            body = {
                "model": DASHSCOPE_MODEL,
                "input": {"prompt": enhanced_prompt[:1024]},
                "parameters": {"size": size, "n": 1},
            }

            print(f"  [QwenImg] Submitting {shot_id}...")
            resp = await client.post(
                "/api/v1/services/aigc/text2image/image-synthesis",
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

            # Check for error
            if "code" in data and data["code"] != "":
                return QwenImageResult(
                    shot_id=shot_id, success=False,
                    error_message=f"{data.get('code')}: {data.get('message', '')}",
                )

            task_id = data.get("output", {}).get("task_id", "")
            if not task_id:
                return QwenImageResult(shot_id=shot_id, success=False, error_message="No task_id")

            # Step 2: Poll for result
            for poll in range(20):
                await asyncio.sleep(2)

                task_resp = await client.get(f"/api/v1/tasks/{task_id}")
                task_resp.raise_for_status()
                task_data = task_resp.json()

                status = task_data.get("output", {}).get("task_status", "")

                if status == "SUCCEEDED":
                    elapsed = int((time.time() - start_time) * 1000)
                    results = task_data.get("output", {}).get("results", [])
                    image_url = results[0].get("url", "") if results else ""

                    print(f"  [QwenImg] {shot_id} OK ({elapsed}ms)")
                    return QwenImageResult(
                        shot_id=shot_id, success=True,
                        image_url=image_url, task_id=task_id,
                        generation_time_ms=elapsed,
                    )

                elif status == "FAILED":
                    err = task_data.get("output", {}).get("message", "Unknown")
                    return QwenImageResult(
                        shot_id=shot_id, success=False,
                        task_id=task_id, error_message=err,
                    )

                if poll % 3 == 0:
                    print(f"  [QwenImg] {shot_id} polling... ({poll+1}/20)")

            return QwenImageResult(shot_id=shot_id, success=False,
                task_id=task_id, error_message="Timeout after 40s")

        except Exception as e:
            elapsed = int((time.time() - start_time) * 1000)
            return QwenImageResult(shot_id=shot_id, success=False,
                error_message=str(e), generation_time_ms=elapsed)

    def _ensure_anime_style(self, prompt: str, negative: str = "") -> str:
        """Legacy alias — delegates to dynamic StyleInjector (anime style)."""
        return self.injector.enhance_prompt(prompt, negative)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
