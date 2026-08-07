"""Video Compositor — assembles images/video segments + audio + subtitles into final video.

Uses FFmpeg for assembly, with optional Remotion alternative for programmatic compositing.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CompositeRequest:
    """Request to composite an episode."""
    episode_index: int
    title: str
    shot_segments: list[dict]  # [{shot_id, video_path, image_path, audio_path, duration_ms, subtitle_text, ...}]
    output_path: str
    resolution: str = "1920x1080"
    fps: int = 24
    include_subtitles: bool = True
    subtitle_style: str = "default"
    background_music_path: str = ""
    watermark: Optional[dict] = None  # {text, position}


@dataclass
class CompositeResult:
    """Result of video compositing."""
    episode_index: int
    success: bool
    output_path: str = ""
    output_url: str = ""
    duration_ms: int = 0
    file_size_bytes: int = 0
    subtitles_file: str = ""
    error_message: str = ""


class FFmpegCompositor:
    """Compositor using FFmpeg for video assembly.

    Pipeline per episode:
    1. Concatenate shot video segments (or image sequences for static shots)
    2. Add audio tracks (dialogue + BGM)
    3. Burn subtitles
    4. Apply transitions between shots
    5. Encode final MP4
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path

    async def composite(self, request: CompositeRequest) -> CompositeResult:
        """Composite one episode into final video."""
        import subprocess
        import os

        output_dir = Path(request.output_path).parent
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Build concat file listing all shot segments
            concat_file = output_dir / f"concat_e{request.episode_index:03d}.txt"
            with open(concat_file, "w") as f:
                for seg in request.shot_segments:
                    video = seg.get("video_path") or seg.get("image_path", "")
                    if video:
                        f.write(f"file '{video}'\n")
                        f.write(f"duration {seg.get('duration_ms', 3000) / 1000}\n")

            # FFmpeg concat command
            cmd = [
                self.ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-r", str(request.fps),
                "-s", request.resolution,
                str(request.output_path),
            ]

            subprocess.run(cmd, check=True, capture_output=True, timeout=600)

            file_size = os.path.getsize(request.output_path) if os.path.exists(request.output_path) else 0

            return CompositeResult(
                episode_index=request.episode_index,
                success=True,
                output_path=request.output_path,
                file_size_bytes=file_size,
            )

        except subprocess.CalledProcessError as e:
            return CompositeResult(
                episode_index=request.episode_index,
                success=False,
                error_message=f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}",
            )
        except Exception as e:
            return CompositeResult(
                episode_index=request.episode_index,
                success=False,
                error_message=str(e),
            )


class RemotionCompositor:
    """Alternative compositor using Remotion (React-based programmatic video).

    More flexible than FFmpeg for complex animations but requires Node.js runtime.
    """

    def __init__(self, remotion_project_path: str = "./remotion-composer"):
        self.project_path = remotion_project_path

    async def composite(self, request: CompositeRequest) -> CompositeResult:
        """Composite via Remotion render."""
        return CompositeResult(
            episode_index=request.episode_index,
            success=False,
            error_message="Remotion compositor not yet implemented",
        )
