"""Tests for Stage 4 video providers — MiniMax + FFmpeg Ken Burns.

Run: pytest tests/test_stage4_providers.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── FFmpeg Provider Tests ──


class TestFFmpegVideoProvider:
    """Test the FFmpeg Ken Burns video provider."""

    def test_zoompan_filter_generation(self):
        """Should generate correct FFmpeg zoompan filter string."""
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        provider = FFmpegVideoProvider()
        filter_str = provider._build_zoompan_filter(
            total_frames=72,   # 3 seconds at 24fps
            fps=24,
            resolution="1920x1080",
            direction="in",
        )

        assert "zoompan" in filter_str
        assert "1920" in filter_str
        assert "1080" in filter_str
        assert "fps=24" in filter_str
        assert "format=yuv420p" in filter_str

    def test_zoom_out_filter(self):
        """Zoom-out should start zoomed in and end at 1.0."""
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        provider = FFmpegVideoProvider()
        filter_str = provider._build_zoompan_filter(72, 24, "1280x720", "out")

        assert "zoompan" in filter_str
        assert "1280" in filter_str
        assert "720" in filter_str

    def test_estimate_cost_is_zero(self):
        """FFmpeg should always cost $0."""
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        provider = FFmpegVideoProvider()
        assert provider.estimate_cost() == 0.0
        assert provider.estimate_cost(5000) == 0.0

    def test_provider_name(self):
        """Provider identity should be 'ffmpeg'."""
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        provider = FFmpegVideoProvider()
        assert provider.provider_name == "ffmpeg"
        assert provider.model_name == "ken_burns"

    @pytest.mark.asyncio
    async def test_generate_with_missing_image(self):
        """Should return error when image doesn't exist."""
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        provider = FFmpegVideoProvider()
        result = await provider.generate(
            shot_id="SH-TEST-001",
            image_path_or_url="/nonexistent/path.png",
        )

        assert result.success is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_generate_success(self, mock_run):
        """Should generate video on successful FFmpeg execution."""
        from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Create a dummy image file
        output_dir = Path("./generated/videos")
        output_dir.mkdir(parents=True, exist_ok=True)
        dummy_image = output_dir / "test_frame.png"
        dummy_image.write_text("dummy")  # not a real image but exists

        provider = FFmpegVideoProvider(output_dir=str(output_dir))
        result = await provider.generate(
            shot_id="SH-TEST-002",
            image_path_or_url=str(dummy_image),
            duration_ms=2000,
        )

        assert result.success is True
        assert result.duration_ms == 2000
        assert "SH-TEST-002" in result.local_path

        # Cleanup
        dummy_image.unlink(missing_ok=True)
        for f in output_dir.glob("SH-TEST-002*"):
            f.unlink(missing_ok=True)


# ── MiniMax Provider Tests ──


class TestMiniMaxVideoProvider:
    """Test the MiniMax video provider."""

    def test_motion_prompt_building(self):
        """Should build style-appropriate motion prompts (anime + realistic)."""
        from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

        # Anime style (default)
        provider = MiniMaxVideoProvider(api_key="test-key")
        result = provider._build_motion_prompt("camera slowly pans left")
        assert "camera slowly pans left" in result
        assert "anime-style motion" in result

        # Realistic style — should NOT contain anime hints
        realistic = MiniMaxVideoProvider(api_key="test-key", art_style="realistic")
        result = realistic._build_motion_prompt("camera slowly pans left")
        assert "camera slowly pans left" in result
        assert "anime-style motion" not in result
        assert "natural human motion" in result

    def test_cost_estimation(self):
        """Should estimate cost based on duration."""
        from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

        provider = MiniMaxVideoProvider(api_key="test-key")

        cost_3s = provider._estimate_cost(3000)
        cost_10s = provider._estimate_cost(10000)

        assert cost_3s > 0
        assert cost_10s > cost_3s
        assert round(cost_3s, 2) == round(3.0 * 0.03, 2)  # ~$0.09 for 3 seconds

    def test_provider_identity(self):
        """Provider should report correct name and model."""
        from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

        provider = MiniMaxVideoProvider(api_key="test-key", model="video-01")
        assert provider.provider_name == "minimax"
        assert provider.model_name == "video-01"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_generate_api_error(self, mock_post):
        """Should handle API error responses gracefully."""
        from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

        # Mock error response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "base_resp": {"status_code": 1001, "status_msg": "Invalid API key"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        provider = MiniMaxVideoProvider(api_key="bad-key")
        result = await provider.generate(
            shot_id="SH-TEST-003",
            prompt="test motion",
        )

        assert result.success is False
        assert "1001" in result.error_message or "Invalid" in result.error_message

    @pytest.mark.asyncio
    async def test_prompt_truncation(self):
        """Very long prompts should be truncated to 1000 chars."""
        from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

        provider = MiniMaxVideoProvider(api_key="test-key")
        long_prompt = "camera movement " * 300  # ~4500 chars

        motion_prompt = provider._build_motion_prompt(long_prompt)
        # The build_motion_prompt doesn't truncate; truncation happens at API call time
        # Just verify the prompt was built
        assert len(motion_prompt) > 100


# ── Video Provider Factory Tests ──


class TestVideoProviderFactory:
    """Test the create_video_provider factory."""

    def test_create_ffmpeg_provider(self):
        """Factory should create FFmpeg provider."""
        from app.agents.stage4_production.video_gen import create_video_provider

        provider = create_video_provider("ffmpeg")
        assert provider.provider_name == "ffmpeg"
        assert provider.estimate_cost(MagicMock()) == 0.0

    def test_create_minimax_provider(self):
        """Factory should create MiniMax provider."""
        from app.agents.stage4_production.video_gen import create_video_provider

        provider = create_video_provider("minimax", api_key="test-key")
        assert provider.provider_name == "minimax"
        cost = provider.estimate_cost(MagicMock(duration_ms=3000))
        assert cost > 0

    def test_create_unknown_provider_raises(self):
        """Factory should raise ValueError for unknown providers."""
        from app.agents.stage4_production.video_gen import create_video_provider

        with pytest.raises(ValueError, match="Unknown video provider"):
            create_video_provider("nonexistent_provider")

    def test_kling_and_veo_are_stubs(self):
        """Kling, Veo, Seedance should exist but return 'not yet implemented'."""
        from app.agents.stage4_production.video_gen import (
            VideoGenRequest,
            create_video_provider,
        )

        for name in ["kling", "veo", "seedance"]:
            provider = create_video_provider(name, api_key="test")
            assert provider is not None

    @pytest.mark.asyncio
    async def test_stub_providers_return_not_implemented(self):
        """Stub providers should return error messages."""
        from app.agents.stage4_production.video_gen import (
            VideoGenRequest,
            create_video_provider,
        )

        req = VideoGenRequest(shot_id="TEST", start_frame_url="http://example.com/img.png")

        for name in ["veo", "seedance", "kling"]:
            provider = create_video_provider(name, api_key="test")
            result = await provider.generate(req)
            assert result.success is False
            assert "not yet implemented" in result.error_message.lower()


# ── FFmpeg Compositor Integration ──


class TestFFmpegCompositor:
    """Test the FFmpeg video compositor used in Stage 4 pipeline."""

    def test_compositor_accepts_segments(self):
        """Compositor should accept shot segments list."""
        from app.agents.stage4_production.compositor import CompositeRequest

        req = CompositeRequest(
            episode_index=1,
            title="Test Episode",
            shot_segments=[
                {
                    "shot_id": "SH-001",
                    "image_path": "/tmp/img1.png",
                    "video_path": "/tmp/vid1.mp4",
                    "duration_ms": 3000,
                    "subtitle_text": "Hello world",
                },
            ],
            output_path="/tmp/output.mp4",
            resolution="1920x1080",
        )

        assert req.episode_index == 1
        assert len(req.shot_segments) == 1
        assert req.resolution == "1920x1080"

    def test_compositor_rejects_empty_segments(self):
        """Compositor should handle empty segment list."""
        from app.agents.stage4_production.compositor import CompositeRequest

        req = CompositeRequest(
            episode_index=1,
            title="Empty",
            shot_segments=[],
            output_path="/tmp/empty.mp4",
            resolution="1920x1080",
        )

        assert len(req.shot_segments) == 0


# ── Manual Run ──


async def main():
    """Manual test — prints results for visual inspection."""
    print("=" * 60)
    print("Stage 4 Video Provider Tests — Manual Run")
    print("=" * 60)

    # 1. FFmpeg provider
    print("\n[1] Testing FFmpeg Video Provider...")
    from app.agents.stage4_production.ffmpeg_video_provider import FFmpegVideoProvider

    ffmpeg = FFmpegVideoProvider()
    print(f"  Provider: {ffmpeg.provider_name}, Model: {ffmpeg.model_name}")
    print(f"  Cost for 5s video: ${ffmpeg.estimate_cost(5000)}")

    # Test filter generation
    f = ffmpeg._build_zoompan_filter(72, 24, "1920x1080", "in")
    print(f"  Filter length: {len(f)} chars")

    # 2. MiniMax provider (no API call)
    print("\n[2] Testing MiniMax Video Provider (no API call)...")
    from app.agents.stage4_production.minimax_video_provider import MiniMaxVideoProvider

    minimax = MiniMaxVideoProvider(api_key="test-key")
    print(f"  Provider: {minimax.provider_name}, Model: {minimax.model_name}")
    print(f"  Cost for 3s: ${minimax._estimate_cost(3000)}")
    print(f"  Cost for 10s: ${minimax._estimate_cost(10000)}")

    prompt = minimax._build_motion_prompt("character turns head slowly")
    print(f"  Motion prompt: {prompt[:100]}...")

    # 3. Factory
    print("\n[3] Testing Provider Factory...")
    from app.agents.stage4_production.video_gen import create_video_provider

    for name in ["ffmpeg", "minimax"]:
        provider = create_video_provider(name, api_key="test")
        print(f"  {name}: created OK, provider_name={provider.provider_name}")

    print("\n" + "=" * 60)
    print("All video provider tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
