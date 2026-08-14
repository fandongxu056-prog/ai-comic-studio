"""Image generation provider abstraction for Stage 4 Pipeline.

Pattern: Strategy + Factory — each provider implements a common interface.
Plug in new image providers without changing pipeline code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageGenRequest:
    """Standardized image generation request."""
    shot_id: str
    prompt: str
    negative_prompt: str
    seed: int
    width: int = 1920
    height: int = 1080
    cfg_scale: float = 7.0
    steps: int = 30
    reference_image_url: str = ""


@dataclass
class ImageGenResult:
    """Standardized image generation result."""
    shot_id: str
    success: bool
    image_url: str = ""
    local_path: str = ""
    seed_used: int = 0
    actual_prompt: str = ""
    generation_time_ms: int = 0
    cost_usd: float = 0.0
    error_message: str = ""


class ImageProvider(ABC):
    """Abstract base for image generation providers."""

    @abstractmethod
    async def generate(self, request: ImageGenRequest) -> ImageGenResult:
        """Generate a single image."""
        ...

    @abstractmethod
    def estimate_cost(self, request: ImageGenRequest) -> float:
        """Estimate cost before making the API call."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class OpenAIDalleProvider(ImageProvider):
    """DALL-E 3 image generation provider."""

    provider_name = "openai"
    model_name = "dall-e-3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, request: ImageGenRequest) -> ImageGenResult:
        """Generate via DALL-E 3."""
        import time
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        start = time.time()

        try:
            # DALL-E doesn't support seed/negative_prompt directly
            size = "1792x1024" if request.width > request.height else "1024x1792"
            response = await client.images.generate(
                model=self.model_name,
                prompt=request.prompt[:4000],
                size=size,
                quality="hd",
                n=1,
            )
            elapsed_ms = int((time.time() - start) * 1000)

            return ImageGenResult(
                shot_id=request.shot_id,
                success=True,
                image_url=response.data[0].url or "",
                seed_used=request.seed,
                actual_prompt=request.prompt,
                generation_time_ms=elapsed_ms,
                cost_usd=0.040,  # $0.04 per DALL-E 3 image
            )
        except Exception as e:
            return ImageGenResult(
                shot_id=request.shot_id,
                success=False,
                error_message=str(e),
                generation_time_ms=int((time.time() - start) * 1000),
            )

    def estimate_cost(self, request: ImageGenRequest) -> float:
        return 0.040  # Standard quality 1024x1024


class StableDiffusionProvider(ImageProvider):
    """Stable Diffusion (local or API) provider."""

    provider_name = "stable_diffusion"
    model_name = "sdxl"

    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    async def generate(self, request: ImageGenRequest) -> ImageGenResult:
        """Generate via Stable Diffusion API."""
        import time
        import httpx

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.endpoint_url}/txt2img",
                    json={
                        "prompt": request.prompt,
                        "negative_prompt": request.negative_prompt,
                        "seed": request.seed,
                        "width": request.width,
                        "height": request.height,
                        "cfg_scale": request.cfg_scale,
                        "steps": request.steps,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                elapsed = int((time.time() - start) * 1000)

                return ImageGenResult(
                    shot_id=request.shot_id,
                    success=True,
                    image_url=data.get("url", ""),
                    seed_used=request.seed,
                    actual_prompt=request.prompt,
                    generation_time_ms=elapsed,
                    cost_usd=0.0,  # Local = free
                )
        except Exception as e:
            return ImageGenResult(
                shot_id=request.shot_id,
                success=False,
                error_message=str(e),
            )

    def estimate_cost(self, request: ImageGenRequest) -> float:
        return 0.0


# ── Provider Factory ──

_provider_registry: dict[str, type[ImageProvider]] = {
    "openai": OpenAIDalleProvider,
    "dalle": OpenAIDalleProvider,
    "stable_diffusion": StableDiffusionProvider,
    "sdxl": StableDiffusionProvider,
    "minimax": None,  # Lazy-loaded from minimax_image_provider.py
}


def create_image_provider(provider_name: str, **kwargs) -> ImageProvider:
    """Factory to create an image provider instance.

    Supported: openai/dalle, stable_diffusion/sdxl, minimax (same key as video).
    """
    if provider_name == "minimax":
        from app.agents.stage4_production.minimax_image_provider import MiniMaxImageProvider

        class _MiniMaxImgAdapter(ImageProvider):
            """Adapter: MiniMaxImageProvider → ImageProvider interface."""

            def __init__(self, api_key: str = "", art_style: str = "anime", **kw):
                self._provider = MiniMaxImageProvider(api_key=api_key, art_style=art_style)

            async def generate(self, request: ImageGenRequest) -> ImageGenResult:
                result = await self._provider.generate(
                    shot_id=request.shot_id,
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                )
                return ImageGenResult(
                    shot_id=request.shot_id,
                    success=result.success,
                    image_url=result.image_url,
                    seed_used=request.seed,
                    actual_prompt=request.prompt,
                    generation_time_ms=result.generation_time_ms,
                    cost_usd=result.cost_estimate_usd,
                    error_message=result.error_message,
                )

            def estimate_cost(self, request: ImageGenRequest) -> float:
                return 0.02

            @property
            def provider_name(self) -> str:
                return "minimax"

            @property
            def model_name(self) -> str:
                return self._provider.model_name

        return _MiniMaxImgAdapter(**kwargs)

    provider_cls = _provider_registry.get(provider_name)
    if not provider_cls:
        raise ValueError(
            f"Unknown image provider: {provider_name}. "
            f"Available: minimax, openai, dalle, stable_diffusion, sdxl"
        )
    return provider_cls(**kwargs)
