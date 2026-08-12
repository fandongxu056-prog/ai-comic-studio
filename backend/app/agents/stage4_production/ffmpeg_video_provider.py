"""FFmpeg Video Provider — local Ken Burns effect (image-to-video).

Free, no API key required. Converts still keyframe images into video segments
using FFmpeg's zoompan filter for the classic "Ken Burns" pan-and-zoom effect.

Use this as:
1. A fallback when cloud video APIs are unavailable
2. A cost-free preview/draft mode
3. Quick testing without API calls

Quality is lower than AI video generation, but it works instantly and costs nothing.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional


class FFmpegVideoResult:
    """Result from FFmpeg video generation."""

    def __init__(
        self,
        shot_id: str,
        success: bool,
        video_url: str = "",
        local_path: str = "",
        duration_ms: int = 0,
        generation_time_ms: int = 0,
        error_message: str = "",
    ):
        self.shot_id = shot_id
        self.success = success
        self.video_url = video_url
        self.local_path = local_path
        self.duration_ms = duration_ms
        self.generation_time_ms = generation_time_ms
        self.error_message = error_message


class FFmpegVideoProvider:
    """Generate video from images using FFmpeg Ken Burns effect.

    Features:
    - Pan and zoom animation on still images
    - Configurable zoom direction (in/out/random)
    - Auto-downloads image from URL if local path not available
    - Zero API cost
    - Works offline

    Requirements:
    - ffmpeg must be installed and on PATH
    """

    def __init__(self, output_dir: str = "./generated/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        shot_id: str,
        image_path_or_url: str = "",
        duration_ms: int = 3000,
        fps: int = 24,
        resolution: str = "1920x1080",
        zoom_direction: str = "in",  # in | out | random
    ) -> FFmpegVideoResult:
        """Generate a Ken Burns video from a still image.

        Args:
            shot_id: Shot identifier.
            image_path_or_url: Local path or HTTP URL of the keyframe image.
            duration_ms: Video duration in milliseconds.
            fps: Frames per second.
            resolution: Output resolution "WxH".
            zoom_direction: Zoom effect direction.

        Returns:
            FFmpegVideoResult with local video path on success.
        """
        start_time = time.time()
        output_path = self.output_dir / f"{shot_id}.mp4"

        # Resolve image to local path
        local_image = await self._resolve_image(image_path_or_url, shot_id)

        if not local_image or not os.path.exists(local_image):
            return FFmpegVideoResult(
                shot_id=shot_id,
                success=False,
                error_message=f"Image not found: {image_path_or_url}",
            )

        duration_sec = max(duration_ms / 1000.0, 0.5)
        total_frames = int(duration_sec * fps)

        try:
            # Build FFmpeg command with zoompan filter
            zoom_filter = self._build_zoompan_filter(total_frames, fps, resolution, zoom_direction)

            cmd = [
                "ffmpeg",
                "-loop", "1",                    # Loop the single input image
                "-i", local_image,
                "-filter_complex", zoom_filter,
                "-t", str(duration_sec),
                "-c:v", "libx264",
                "-preset", "ultrafast",           # Speed over compression
                "-crf", "23",                     # Reasonable quality
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-y",                             # Overwrite output
                str(output_path),
            ]

            print(f"  [FFmpegVideo] Generating {shot_id}... ({duration_sec}s, {total_frames}frames)")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            if result.returncode != 0:
                stderr_tail = result.stderr[-300:] if result.stderr else "no stderr"
                return FFmpegVideoResult(
                    shot_id=shot_id,
                    success=False,
                    error_message=f"FFmpeg failed (exit {result.returncode}): {stderr_tail}",
                    generation_time_ms=elapsed_ms,
                )

            file_size = os.path.getsize(output_path) if output_path.exists() else 0

            print(f"  [FFmpegVideo] {shot_id} OK ({elapsed_ms}ms, {file_size}B)")

            return FFmpegVideoResult(
                shot_id=shot_id,
                success=True,
                local_path=str(output_path),
                video_url=f"file://{output_path}",
                duration_ms=duration_ms,
                generation_time_ms=elapsed_ms,
            )

        except subprocess.TimeoutExpired:
            return FFmpegVideoResult(
                shot_id=shot_id,
                success=False,
                error_message="FFmpeg timed out after 60s",
            )
        except FileNotFoundError:
            return FFmpegVideoResult(
                shot_id=shot_id,
                success=False,
                error_message="ffmpeg not found on PATH — install FFmpeg first",
            )
        except Exception as e:
            return FFmpegVideoResult(
                shot_id=shot_id,
                success=False,
                error_message=str(e),
            )

    def _build_zoompan_filter(
        self,
        total_frames: int,
        fps: int,
        resolution: str,
        direction: str,
    ) -> str:
        """Build FFmpeg zoompan filter for Ken Burns effect.

        Creates a smooth zoom animation:
        - zoom in:  start at 1.0x, end at 1.3x
        - zoom out: start at 1.3x, end at 1.0x
        - random:   random choice between in/out

        The filter chain:
        1. scale: resize to target resolution
        2. zoompan: apply smooth zoom + pan
        3. format: convert to yuv420p for compatibility
        """
        # Parse resolution
        try:
            w, h = map(int, resolution.split("x"))
        except ValueError:
            w, h = 1920, 1080

        # Zoom range
        if direction == "out":
            zoom_start, zoom_end = 1.3, 1.0
        elif direction == "random":
            import random
            if random.random() > 0.5:
                zoom_start, zoom_end = 1.0, 1.25
            else:
                zoom_start, zoom_end = 1.25, 1.0
        else:  # "in" (default)
            zoom_start, zoom_end = 1.0, 1.3

        # zoompan parameters
        # z = zoom factor per frame
        zoom_per_frame = (zoom_end - zoom_start) / total_frames if total_frames > 1 else 0

        # Smooth pan: slight horizontal movement
        x_pan = "iw/2 - (iw/zoom/2)"  # Keep centered
        y_pan = "ih/2 - (ih/zoom/2)"

        # Build the filter string
        # zoompan=d=1: incrementally changes zoom each frame
        filter_str = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan="
            f"z='if(eq(n,0),{zoom_start},zoom+{zoom_per_frame})':"
            f"x='{x_pan}':"
            f"y='{y_pan}':"
            f"d=1:"
            f"s={w}x{h}:"
            f"fps={fps},"
            f"format=yuv420p"
        )

        return filter_str

    async def _resolve_image(self, path_or_url: str, shot_id: str) -> Optional[str]:
        """Resolve an image URL or path to a local file.

        If it's a URL, download it first. If it's a local path, verify it exists.
        """
        if not path_or_url:
            return None

        # Already a local path
        if os.path.exists(path_or_url):
            return path_or_url

        # Download from URL
        if path_or_url.startswith(("http://", "https://")):
            import urllib.request

            download_dir = self.output_dir / "frames"
            download_dir.mkdir(parents=True, exist_ok=True)
            local_path = download_dir / f"{shot_id}_frame.png"

            try:
                print(f"  [FFmpegVideo] Downloading frame for {shot_id}...")
                urllib.request.urlretrieve(path_or_url, str(local_path))
                if local_path.exists():
                    return str(local_path)
            except Exception as e:
                print(f"  [FFmpegVideo] Download failed: {e}")

        return None

    @property
    def provider_name(self) -> str:
        return "ffmpeg"

    @property
    def model_name(self) -> str:
        return "ken_burns"

    def estimate_cost(self, duration_ms: int = 3000) -> float:
        """FFmpeg is free — always returns 0."""
        return 0.0

    async def close(self):
        """No cleanup needed for FFmpeg provider."""
        pass
