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
    "minimax": None,   # Lazy-loaded from minimax_video_provider.py
    "ffmpeg": None,    # Lazy-loaded from ffmpeg_video_provider.py
}


def create_video_provider(provider_name: str, **kwargs) -> VideoProvider:
    """Factory to create a video provider instance.

    Supported providers:
    - minimax: MiniMax (Hailuo) AI video generation (requires API key)
    - ffmpeg: Local FFmpeg Ken Burns effect (free, no API key)
    - veo: Google Veo (stub)
    - seedance: Seedance (stub)
    - kling: Kling (stub)
    """
    # Lazy-load providers not based on the abstract VideoProvider interface
    if provider_name == "minimax":
        from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

        class _MiniMaxAdapter(VideoProvider):
            """Adapter to make MiniMaxVideoProvider conform to VideoProvider interface."""

            def __init__(self, api_key: str = "", model: str = "video-01", **kw):
                self._provider = MiniMaxVideoProvider(api_key=api_key, model=model)

            async def generate(self, request: VideoGenRequest) -> VideoGenResult:
                result = await self._provider.generate(
                    shot_id=request.shot_id,
                    start_frame_url=request.start_frame_url,
                    prompt=request.motion_prompt,
                    duration_ms=request.duration_ms,
                )
                return VideoGenResult(
                    shot_id=request.shot_id,
                    success=result.success,
                    video_url=result.video_url,
                    duration_ms=result.duration_ms,
                    generation_time_ms=result.generation_time_ms,
                    cost_usd=result.cost_estimate_usd,
                    error_message=result.error_message,
                )

            def estimate_cost(self, request: VideoGenRequest) -> float:
                return self._provider._estimate_cost(request.duration_ms)

            @property
            def provider_name(self) -> str:
                return "minimax"

        return _MiniMaxAdapter(**kwargs)

    elif provider_name == "ffmpeg":
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        class _FFmpegAdapter(VideoProvider):
            """Adapter to make FFmpegVideoProvider conform to VideoProvider interface."""

            def __init__(self, output_dir: str = "./generated/videos", **kw):
                self._provider = FFmpegVideoProvider(output_dir=output_dir)

            async def generate(self, request: VideoGenRequest) -> VideoGenResult:
                result = await self._provider.generate(
                    shot_id=request.shot_id,
                    image_path_or_url=request.start_frame_url,
                    duration_ms=request.duration_ms,
                )
                return VideoGenResult(
                    shot_id=request.shot_id,
                    success=result.success,
                    video_url=result.video_url,
                    local_path=result.local_path,
                    duration_ms=result.duration_ms,
                    generation_time_ms=result.generation_time_ms,
                    cost_usd=0.0,
                    error_message=result.error_message,
                )

            def estimate_cost(self, request: VideoGenRequest) -> float:
                return 0.0

            @property
            def provider_name(self) -> str:
                return "ffmpeg"

        return _FFmpegAdapter(**kwargs)

    cls = _video_provider_registry.get(provider_name)
    if cls is None:
        raise ValueError(
            f"Unknown video provider: {provider_name}. "
            f"Available: minimax, ffmpeg, veo, seedance, kling"
        )
    return cls(**kwargs)
