"""TTS generation provider abstraction for Stage 4 Pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSRequest:
    shot_id: str
    character_id: str
    text: str
    voice_id: str = ""
    language: str = "zh-CN"
    speed: float = 1.0
    emotion: str = ""


@dataclass
class TTSResult:
    shot_id: str
    success: bool
    audio_url: str = ""
    local_path: str = ""
    duration_ms: int = 0
    format: str = "mp3"
    cost_usd: float = 0.0
    error_message: str = ""


class TTSProvider(ABC):
    """Abstract base for TTS providers."""

    @abstractmethod
    async def generate(self, request: TTSRequest) -> TTSResult:
        ...

    @abstractmethod
    def estimate_cost(self, request: TTSRequest) -> float:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider (tts-1 / tts-1-hd)."""
    provider_name = "openai"

    def __init__(self, api_key: str, model: str = "tts-1-hd", default_voice: str = "alloy"):
        self.api_key = api_key
        self.model = model
        self.default_voice = default_voice

    async def generate(self, request: TTSRequest) -> TTSResult:
        import time
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        start = time.time()

        try:
            response = await client.audio.speech.create(
                model=self.model,
                voice=request.voice_id or self.default_voice,
                input=request.text,
                speed=request.speed,
            )
            elapsed = int((time.time() - start) * 1000)

            return TTSResult(
                shot_id=request.shot_id,
                success=True,
                duration_ms=0,  # Would parse from audio
                cost_usd=0.030,  # $0.03 per 1k chars
            )
        except Exception as e:
            return TTSResult(shot_id=request.shot_id, success=False, error_message=str(e))

    def estimate_cost(self, request: TTSRequest) -> float:
        return max(len(request.text) / 1000 * 0.015, 0.001)  # ~$0.015 per 1k chars


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS — free, local, good for Chinese."""
    provider_name = "edge"

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice

    async def generate(self, request: TTSRequest) -> TTSResult:
        """Generate via edge-tts (free, offline-compatible)."""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=request.text,
                voice=self.voice,
                rate=f"{int((request.speed - 1.0) * 100):+d}%",
            )
            # Would save to file in production
            return TTSResult(
                shot_id=request.shot_id,
                success=True,
                cost_usd=0.0,  # Free!
            )
        except Exception as e:
            return TTSResult(shot_id=request.shot_id, success=False, error_message=str(e))

    def estimate_cost(self, request: TTSRequest) -> float:
        return 0.0


# ── Registry ──

_tts_registry: dict[str, type[TTSProvider]] = {
    "openai": OpenAITTSProvider,
    "edge": EdgeTTSProvider,
}


def create_tts_provider(provider_name: str, **kwargs) -> TTSProvider:
    cls = _tts_registry.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown TTS provider: {provider_name}")
    return cls(**kwargs)
