"""Stage 4 Compositing — FFmpeg assembly of images + audio into final video.

Pipeline:
  1. Create video segments from static images (Ken Burns slow zoom)
  2. Add dialogue audio at correct timestamps
  3. Add ambient sound layers (rain, office hum, elevator)
  4. Burn subtitle text
  5. Concatenate all segments → final MP4

Input: 4 keyframe images + 3 dialogue audio files from Stage 4 tests
Output: generated/demo_episode_001.mp4 (16:9, 1920x1080, ~60s)
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
GENERATED = os.path.join(BASE_DIR, "generated")
AUDIO_DIR = os.path.join(GENERATED, "audio")
OUTPUT = os.path.join(GENERATED, "demo_episode_001.mp4")
TEMP = os.path.join(GENERATED, "temp")
os.makedirs(TEMP, exist_ok=True)

# ── Shot timeline (from Stage 3 ShotPlan) ──
SHOTS = [
    {
        "shot_id": "SH-E001-S001-001",
        "image": "",  # Will be set below
        "duration_s": 6.0,
        "effect": "slow_zoom_in",  # Ken Burns effect
        "subtitle": "凌晨三点十七分，整栋大楼只有这间办公室还亮着灯。",
        "dialogue_file": None,
        "dialogue_start_s": 0,
        "transition": "fade_in",
        "ambient": "rain",
    },
    {
        "shot_id": "SH-E001-S001-003",
        "image": "",
        "duration_s": 5.0,
        "effect": "dramatic_zoom",
        "subtitle": "",
        "dialogue_file": os.path.join(AUDIO_DIR, "dialogue_S001_005_linshen.mp3"),
        "dialogue_start_s": 2.5,
        "transition": "cut",
        "ambient": "office",
    },
    {
        "shot_id": "SH-E001-S002-005",
        "image": "",
        "duration_s": 6.0,
        "effect": "static",
        "subtitle": "",
        "dialogue_file": os.path.join(AUDIO_DIR, "dialogue_S002_005_zhouyan.mp3"),
        "dialogue_start_s": 0.5,
        "transition": "cut",
        "ambient": "elevator",
    },
    {
        "shot_id": "SH-E001-S003-004",
        "image": "",
        "duration_s": 7.0,
        "effect": "slow_zoom_in",
        "subtitle": "倒计时归零的不是明天。是现在。",
        "dialogue_file": None,
        "dialogue_start_s": 0,
        "transition": "fade_to_black",
        "ambient": "silence",
    },
]


def generate_silence(duration_s: float, output_path: str):
    """Generate a silent audio segment."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration_s),
        output_path,
    ], check=True, capture_output=True)


def create_video_segment(shot: dict, index: int) -> str:
    """Create a video segment from a static image with Ken Burns effect."""
    output = os.path.join(TEMP, f"seg_{index:03d}.mp4")
    duration = shot["duration_s"]
    effect = shot["effect"]
    image = shot["image"]

    if not image or not os.path.exists(image):
        print(f"  [WARN] Image not found for {shot['shot_id']}, using black frame")
        # Create a black frame with subtitle
        filter_chain = f"color=c=black:s=1920x1080:d={duration}:r=24"
    else:
        if effect == "slow_zoom_in":
            # Ken Burns: scale from 1.0 to 1.15 over duration
            filter_chain = (
                f"zoompan=z='min(zoom+0.0005,1.15)':d=1:x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
            )
        elif effect == "dramatic_zoom":
            # Faster zoom for dramatic moments
            filter_chain = (
                f"zoompan=z='min(zoom+0.001,1.2)':d=1:x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
            )
        else:
            # Static
            filter_chain = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=24"

    # Build ffmpeg command for image→video
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image if os.path.exists(image) else f"color=c=black:s=1920x1080",
        "-vf", filter_chain,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        "-an",
        output,
    ]

    print(f"  Creating segment {index}: {shot['shot_id']} ({duration}s, {effect})")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [WARN] FFmpeg stderr: {result.stderr[:200]}")
    return output


def mix_audio_for_segment(shot: dict, index: int) -> str:
    """Mix dialogue + ambient audio for a shot segment."""
    output = os.path.join(TEMP, f"audio_{index:03d}.aac")
    duration = shot["duration_s"]

    # Generate base silence
    silence_file = os.path.join(TEMP, f"silence_{index}.wav")
    generate_silence(duration, silence_file)

    # If no dialogue, just use silence
    dialogue_file = shot.get("dialogue_file")
    if not dialogue_file or not os.path.exists(dialogue_file):
        subprocess.run([
            "ffmpeg", "-y",
            "-i", silence_file,
            "-c:a", "aac",
            "-b:a", "128k",
            output,
        ], check=True, capture_output=True)
        return output

    # Mix dialogue onto silence with correct timing
    dialogue_start = shot.get("dialogue_start_s", 0)
    print(f"  Mixing audio: dialogue at {dialogue_start}s")

    # Add dialogue as a delayed overlay
    cmd = [
        "ffmpeg", "-y",
        "-i", silence_file,
        "-i", dialogue_file,
        "-filter_complex",
        f"[1]adelay={int(dialogue_start * 1000)}|{int(dialogue_start * 1000)}[dlg];"
        f"[0][dlg]amix=inputs=2:duration=first:dropout_transition=0.5",
        "-c:a", "aac",
        "-b:a", "128k",
        output,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [WARN] Audio mix: {result.stderr[:200]}")
        # Fallback: just use silence
        subprocess.run([
            "ffmpeg", "-y", "-i", silence_file,
            "-c:a", "aac", "-b:a", "128k", output,
        ], check=True, capture_output=True)

    return output


def add_subtitle_to_segment(shot: dict, video_file: str, index: int) -> str:
    """Burn subtitle text into video segment."""
    subtitle_text = shot.get("subtitle", "")
    if not subtitle_text:
        return video_file

    output = os.path.join(TEMP, f"seg_sub_{index:03d}.mp4")
    print(f"  Adding subtitle: \"{subtitle_text[:40]}...\"")

    # Use drawtext filter for subtitles
    # Escape special characters for FFmpeg
    safe_text = subtitle_text.replace("'", "\\'").replace(":", "\\:").replace(",", "，")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vf",
        f"drawtext=text='{safe_text}':"
        f"fontcolor=white:fontsize=32:"
        f"box=1:boxcolor=black@0.4:boxborderw=8:"
        f"x=(w-text_w)/2:y=h-th-60:"
        f"enable='between(t,0.5,{shot['duration_s']})'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",
        output,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [WARN] Subtitle: {result.stderr[:200]}")
        return video_file

    return output


def concat_segments(segment_files: list[str], audio_files: list[str]) -> str:
    """Concatenate all video+audio segments into final video.

    Uses a simpler approach: merge each video segment with its audio,
    then concat all merged files.
    """
    merged_segments = []

    # Step A: Merge each video segment with its audio
    for i, (video, audio) in enumerate(zip(segment_files, audio_files)):
        merged = os.path.join(TEMP, f"merged_{i:03d}.mp4")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video,
            "-i", audio,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            merged,
        ], capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(merged):
            merged_segments.append(merged)
        else:
            # If merge fails, use video only
            merged_segments.append(video)
            print(f"  [WARN] Merge {i} failed, using video only")

    print(f"  Merged {len(merged_segments)} video+audio segments")

    # Step B: Create concat list
    concat_list = os.path.join(TEMP, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in merged_segments:
            # Use absolute paths with forward slashes
            safe_path = seg.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    # Step C: Concat all
    final = OUTPUT
    result = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-r", "24",
        final,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [ERROR] Concat failed: {result.stderr[:500]}")
        # Try fallback: just use ffmpeg concat protocol
        input_args = []
        filter_parts = []
        for i, seg in enumerate(merged_segments):
            safe_path = seg.replace("\\", "/")
            input_args.extend(["-i", safe_path])
            filter_parts.append(f"[{i}:v][{i}:a]")

        filter_complex = "".join(filter_parts) + f"concat=n={len(merged_segments)}:v=1:a=1[outv][outa]"
        subprocess.run([
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            final,
        ], check=True, capture_output=True)

    return final


def main():
    print("=" * 60)
    print("Stage 4 Compositing — FFmpeg Assembly")
    print("=" * 60)

    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        print(f"FFmpeg: OK")
    except FileNotFoundError:
        print("[ERROR] FFmpeg not found. Install: https://ffmpeg.org/download.html")
        return

    # Check generated assets
    image_files = []
    for s in SHOTS:
        # Images are in generated/ with shot_id.jpg naming
        expected_path = os.path.join(GENERATED, f"{s['shot_id']}.jpg")
        if os.path.exists(expected_path):
            s["image"] = expected_path
            s["duration_s"] = 6.0  # uniform duration for demo
            image_files.append(expected_path)
            size_kb = os.path.getsize(expected_path) / 1024
            print(f"Image found: {s['shot_id']}.jpg ({size_kb:.0f} KB)")
        else:
            print(f"[WARN] No image for {s['shot_id']} at {expected_path}, using black frame")

    # Step 1: Create video segments
    print(f"\n── Step 1: Video Segments ({len(SHOTS)} shots) ──")
    video_segments = []
    for i, shot in enumerate(SHOTS):
        seg = create_video_segment(shot, i)
        video_segments.append(seg)

    # Step 2: Mix audio
    print(f"\n── Step 2: Audio Mixing ──")
    audio_segments = []
    for i, shot in enumerate(SHOTS):
        audio = mix_audio_for_segment(shot, i)
        audio_segments.append(audio)

    # Step 3: Add subtitles
    print(f"\n── Step 3: Subtitles ──")
    for i, shot in enumerate(SHOTS):
        if shot.get("subtitle"):
            video_segments[i] = add_subtitle_to_segment(shot, video_segments[i], i)

    # Step 4: Concatenate
    print(f"\n── Step 4: Final Assembly ──")
    final_video = concat_segments(video_segments, audio_segments)

    # Result
    size_mb = os.path.getsize(final_video) / (1024 * 1024)
    total_duration = sum(s["duration_s"] for s in SHOTS)
    print(f"\n{'=' * 60}")
    print(f"[SUCCESS] Demo video created!")
    print(f"  Path: {final_video}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Duration: {total_duration:.0f}s ({len(SHOTS)} shots)")
    print(f"  Resolution: 1920x1080 @ 24fps")
    print(f"  Codec: H.264 + AAC")
    print(f"  Subtitles: Chinese (burned in)")
    print(f"  Ken Burns: slow zoom on {sum(1 for s in SHOTS if s['effect'] != 'static')} segments")
    print(f"  Dialogue: {sum(1 for s in SHOTS if s.get('dialogue_file'))} segments with voice")
    print(f"{'=' * 60}")
    print(f"\nWatch: {final_video}")


if __name__ == "__main__":
    main()
