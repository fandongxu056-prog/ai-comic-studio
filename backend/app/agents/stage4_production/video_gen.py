"""Video generation provider abstraction for Stage 4 Pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VideoGenRequest:
    shot_id: str
    start_frame_url: str
    end_frame_url: str = ""
    motion_prompt: str = ""
    duration_ms: int = 3000
    fps: int = 24
    motion_strength: float = 0.7
    seed: int = 42


@dataclass
class VideoGenResult:
    shot_id: str
    success: bool
    video_url: str = ""
    local_path: str = ""
    duration_ms: int = 0
    resolution: str = ""
    fps: int = 24
    generation_time_ms: int = 0
    cost_usd: float = 0.0
    error_message: str = ""


class VideoProvider(ABC):
    """Abstract base for video generation providers."""

    @abstractmethod
    async def generate(self, request: VideoGenRequest) -> VideoGenResult:
        ...

    @abstractmethod
    def estimate_cost(self, request: VideoGenRequest) -> float:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class VeoProvider(VideoProvider):
    """Google Veo video generation provider."""
    provider_name = "veo"

    def __init__(self, api_key: str, model: str = "veo-3.1"):
        self.api_key = api_key
        self._model = model

    async def generate(self, request: VideoGenRequest) -> VideoGenResult:
        return VideoGenResult(
            shot_id=request.shot_id,
            success=False,
            error_message="Veo provider not yet implemented",
        )

    def estimate_cost(self, request: VideoGenRequest) -> float:
        return 0.50  # ~$0.50/second for Veo


class SeedanceProvider(VideoProvider):
    """Seedance video generation provider."""
    provider_name = "seedance"

    def __init__(self, api_key: str, model: str = "seedance-2.0"):
        self.api_key = api_key
        self._model = model

    async def generate(self, request: VideoGenRequest) -> VideoGenResult:
        return VideoGenResult(
            shot_id=request.shot_id,
            success=False,
            error_message="Seedance provider not yet implemented",
        )

    def estimate_cost(self, request: VideoGenRequest) -> float:
        return 0.30


class KlingProvider(VideoProvider):
    """Kling (可灵) video generation provider."""
    provider_name = "kling"

    def __init__(self, api_key: str, model: str = "kling-v2"):
        self.api_key = api_key
        self._model = model

    async def generate(self, request: VideoGenRequest) -> VideoGenResult:
        return VideoGenResult(
            shot_id=request.shot_id,
            success=False,
            error_message="Kling provider not yet implemented",
        )

    def estimate_cost(self, request: VideoGenRequest) -> float:
        return 0.25


# ── Provider Registry ──

_video_provider_registry: dict[str, type[VideoProvider]] = {
    "veo": VeoProvider,
    "seedance": SeedanceProvider,
    "kling": KlingProvider,
}


def create_video_provider(provider_name: str, **kwargs) -> VideoProvider:
    cls = _video_provider_registry.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown video provider: {provider_name}")
    return cls(**kwargs)
