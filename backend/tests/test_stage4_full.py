"""Stage 4 Full Production — All 18 shots from Stage 3 storyboard.

Generates:
  1. All 18 keyframe images via Hunyuan (sequential, ~3s each)
  2. All dialogue audio via Edge-TTS (parallel)
  3. Composited demo video via FFmpeg
  4. Production report with cost summary
"""

import asyncio
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.stage4_production.hunyuan_provider import HunyuanImageProvider

API_KEY = "sk-M2YxSYpG5gvTGhZBN6CWizPvJmzAVbSYDwJl0gq4GRCjAKcL"

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
GENERATED = os.path.join(BASE_DIR, "generated")
AUDIO_DIR = os.path.join(GENERATED, "audio")
OUTPUT = os.path.join(GENERATED, "episode_001_full.mp4")
TEMP = os.path.join(GENERATED, "temp")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TEMP, exist_ok=True)

# ── ALL 18 SHOTS from Stage 3 ShotPlan ──
SHOTS = [
    # SCENE 1: 先知科技办公室 — 深夜暴雨
    {
        "shot_id": "SH-E001-S001-001", "scene": 1, "duration_s": 5.0,
        "effect": "slow_zoom_in", "ambient": "rain",
        "subtitle": "凌晨三点十七分，整栋大楼只有这间办公室还亮着灯。",
        "prompt": "日漫动画风格, long shot through rain-streaked window, open plan tech office at night, rows of dark empty desks, single blue monitor glow at far end, Shanghai skyline blurred in storm, man in gray hoodie silhouetted at desk, slouching posture, cinematic low-key lighting with cold blue cast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph, warm lighting, daylight",
        "seed": 7961, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S001-002", "scene": 1, "duration_s": 4.0,
        "effect": "static", "ambient": "office",
        "subtitle": "",
        "prompt": "日漫动画风格, close up shot from behind monitor, man's fingers nervously tapping keyboard spacebar, cold coffee mug with dried stains pushed aside, blue progress bar at 99% on screen, burn scar visible on right forearm in screen's blue glow, shallow depth of field, cinematic low-key lighting with cold blue cast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 15872, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S001-003", "scene": 1, "duration_s": 4.0,
        "effect": "dramatic_zoom", "ambient": "office",
        "subtitle": "",
        "prompt": "日漫动画风格, medium close up of 28-year-old Chinese man, single eyelid narrow eyes, pale skin with dark circles under eyes, short messy black hair, face half-lit by blue monitor glow and half by orange alert from below, expression shifting from focused to shocked, pupils dilating, slouching posture, gray hoodie, burn scar on right forearm catching orange light, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph, deformed face, extra limbs",
        "seed": 23783, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S001-004", "scene": 1, "duration_s": 2.5,
        "effect": "static", "ambient": "silence",
        "subtitle": "",
        "prompt": "日漫动画风格, extreme close up of shattered ceramic coffee mug on dark floor, broken shards reflecting a man's distorted face, spilled coffee with orange alert light reflection, dramatic dutch angle 3 degrees, shallow depth of field, cinematic low-key blue+orange dual lighting, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 31694, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S001-005", "scene": 1, "duration_s": 5.0,
        "effect": "static", "ambient": "office",
        "subtitle": "",
        "prompt": "日漫动画风格, medium shot of Chinese man standing at desk, both hands gripping desk edge, leaning forward, round glasses reflecting screen text, gray hoodie sleeves pushed up, distinct 8cm burn scar on right forearm clearly visible, tense body language, office background dark and empty, cinematic low-key blue cast lighting, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 39505,
        "dialogue": {"text": "……这不可能。", "voice": "zh-CN-YunxiNeural", "rate": "-10%", "start_s": 2.5},
    },
    {
        "shot_id": "SH-E001-S001-006", "scene": 1, "duration_s": 8.0,
        "effect": "slow_zoom_in", "ambient": "thunder",
        "subtitle": "",
        "prompt": "日漫动画风格, high angle over-shoulder shot, Chinese man frozen at keyboard, hands hovering above keys, new evidence alert on screen, orange warning dominating dark blue interface, rain pounding on window in background, tense frozen moment, cinematic low-key blue+orange dual lighting, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 47416, "dialogue": None,
    },

    # SCENE 2: 外滩金融中心 — 清晨雾霾
    {
        "shot_id": "SH-E001-S002-001", "scene": 2, "duration_s": 4.0,
        "effect": "slow_zoom_in", "ambient": "city",
        "subtitle": "",
        "prompt": "日漫动画风格, extreme long shot low angle, modern glass skyscraper disappearing into gray fog, one small figure in black jacket standing across street looking up at 52nd floor, overcast morning Shanghai, cold gray tones, giant building dwarfing tiny human, cinematic low-key lighting with cold blue cast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph, warm lighting",
        "seed": 55327, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S002-002", "scene": 2, "duration_s": 5.0,
        "effect": "static", "ambient": "city",
        "subtitle": "",
        "prompt": "日漫动画风格, medium shot tracking, Chinese man in black jacket walking through luxury marble lobby, symmetrical composition, security guard at front desk glancing up at him, subtle paranoid atmosphere, empty lobby except two people, morning gray light through glass walls, cinematic low-key cold blue cast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 63238, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S002-003", "scene": 2, "duration_s": 3.0,
        "effect": "static", "ambient": "elevator",
        "subtitle": "",
        "prompt": "日漫动画风格, medium close up inside mirrored elevator, Chinese man in black jacket looking up surprised, elevator doors about to close, a hand with silver ring reaching in to stop them, cold white LED light, tight confined space, reflection of man multiplied in mirror walls, cinematic low-key cold blue cast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 71149, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S002-004", "scene": 2, "duration_s": 6.0,
        "effect": "static", "ambient": "elevator",
        "subtitle": "",
        "prompt": "日漫动画风格, over-shoulder shot inside elevator, foreground navy blue suited shoulder with silver ring on left hand, background Chinese man in black jacket pressed against elevator wall looking up, slight low angle emphasizing height difference, two men's reflections overlapping in mirrored elevator wall, tight confined space, cold white LED, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 79060,
        "dialogue": {"text": "你提前来踩点了？", "voice": "zh-CN-YunjianNeural", "rate": "+0%", "start_s": 1.0},
    },
    {
        "shot_id": "SH-E001-S002-005", "scene": 2, "duration_s": 5.0,
        "effect": "dramatic_zoom", "ambient": "elevator",
        "subtitle": "",
        "prompt": "日漫动画风格, medium close up low angle, 30-year-old Chinese man with square jaw, deep-set double eyelid eyes with unnervingly calm gaze, slicked back dark brown hair, light wheat skin, navy blue tailored suit white shirt no tie, military-straight posture, left hand with plain silver ring pressing against mirrored elevator wall near camera creating bokeh, cold white LED light, intimidating presence, confined elevator space, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph, deformed face",
        "seed": 86971,
        "dialogue": {"text": "我在那儿工作。周衍。你呢？是来杀人，还是来被杀？", "voice": "zh-CN-YunjianNeural", "rate": "+0%", "start_s": 0.5},
    },
    {
        "shot_id": "SH-E001-S002-006", "scene": 2, "duration_s": 6.0,
        "effect": "slow_zoom_in", "ambient": "elevator",
        "subtitle": "",
        "prompt": "日漫动画风格, medium shot from inside elevator looking out to 52nd floor corridor, minimalist cold office hallway, one door at far end slightly ajar leaking warm yellow light into cold corridor, exact composition matching earlier system simulation, Chinese man seen from behind frozen in elevator doorway, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 94882, "dialogue": None,
    },

    # SCENE 3: 林深家 — 深夜雨后
    {
        "shot_id": "SH-E001-S003-001", "scene": 3, "duration_s": 6.0,
        "effect": "pan_right", "ambient": "night",
        "subtitle": "",
        "prompt": "日漫动画风格, medium shot panning right across small dark apartment, wet street reflecting orange lamp light through window, entire wall covered in handwritten notes with red string connections like detective board, Chinese man in gray t-shirt sitting on floor with laptop on knees, exhausted expression, burn scar visible on right forearm, single desk lamp as only light source, cinematic low-key cold blue cast with warm orange accent from window, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 102793, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S003-002", "scene": 3, "duration_s": 7.0,
        "effect": "slow_zoom_in", "ambient": "night",
        "subtitle": "",
        "prompt": "日漫动画风格, close up over shoulder shot, Chinese man staring at laptop screen showing code, dark navy blue interface with orange alert text, line reading ZHOUYAN PROTOCOL highlighted, date stamp showing three months ago, man's reflection visible in screen showing shocked expression, dark apartment background, cyberpunk-lite HUD design, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 110704, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S003-003", "scene": 3, "duration_s": 4.0,
        "effect": "static", "ambient": "night",
        "subtitle": "",
        "prompt": "日漫动画风格, medium shot POV from behind monitor, Chinese man standing up abruptly knocking over chair, red alert box on screen casting red light on his face replacing blue glow, text on screen, panic in his eyes, gray t-shirt showing burn scar, dark apartment, dramatic red vs dark contrast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 118615, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S003-004", "scene": 3, "duration_s": 5.0,
        "effect": "slow_zoom_in", "ambient": "silence",
        "subtitle": "",
        "prompt": "日漫动画风格, medium full shot, small dark apartment, Chinese man in gray t-shirt turning around slowly, looking through frosted glass door into dark corridor, wet street outside window, a black silhouette of a man visible behind the glass door, single point of cold white light reflecting from a silver ring on his left hand, terrifying stillness, wall covered in handwritten notes and red string, cinematic low-key lighting with cold blue cast, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph, warm lighting",
        "seed": 126526, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S003-005", "scene": 3, "duration_s": 4.0,
        "effect": "dramatic_zoom", "ambient": "silence",
        "subtitle": "",
        "prompt": "日漫动画风格, extreme close up of a man's terrified eye, pupil dilated, reflection of dark glass door with silver light point growing larger in the pupil, sweat on brow, split composition with right side showing silhouette of man with silver ring raising hand toward door handle, maximum tension, flat color illustration, clean line art, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 134437, "dialogue": None,
    },
    {
        "shot_id": "SH-E001-S003-006", "scene": 3, "duration_s": 4.0,
        "effect": "fade_to_black", "ambient": "silence",
        "subtitle": "倒计时归零的不是明天。是现在。",
        "prompt": "日漫动画风格, pure black screen, faint silhouette barely visible, silver ring gleam as only light source, minimal composition, dark atmospheric, flat color illustration, anime art style",
        "negative": "realistic, photorealistic, 3D, photograph",
        "seed": 142348, "dialogue": None,
    },
]


async def generate_all_images(provider: HunyuanImageProvider):
    """Generate all 18 keyframe images sequentially (Hunyuan limit: 1 concurrent)."""
    print("=" * 60)
    print("Phase 1/4: Image Generation (18 shots, ~60s)")
    print("=" * 60)

    results = {}
    total_success = 0
    total_start = time.time()

    for i, shot in enumerate(SHOTS, 1):
        sid = shot["shot_id"]
        scene = shot["scene"]

        # Scene header
        if i == 1 or SHOTS[i - 2]["scene"] != scene:
            scene_names = {1: "先知科技办公室", 2: "外滩金融中心", 3: "林深家"}
            print(f"\n-- Scene {scene}: {scene_names.get(scene, '')} --")

        print(f"[{i:2d}/18] {sid}...", end=" ", flush=True)

        result = await provider.generate(
            shot_id=sid,
            prompt=shot["prompt"],
            negative_prompt=shot.get("negative", ""),
            seed=shot["seed"],
        )

        results[sid] = result
        if result.success:
            total_success += 1
            print(f"OK ({result.generation_time_ms}ms)")
            # Download immediately
            import urllib.request
            path = os.path.join(GENERATED, f"{sid}.jpg")
            try:
                urllib.request.urlretrieve(result.image_url, path)
            except Exception:
                pass
        else:
            print(f"FAIL: {result.error_message[:80]}")

        # Rate limiting
        if i < len(SHOTS):
            await asyncio.sleep(1)

    elapsed = time.time() - total_start
    print(f"\nImage Generation Complete: {total_success}/18 in {elapsed:.0f}s")
    return results


async def generate_all_tts():
    """Generate TTS for all dialogue segments."""
    print("\n" + "=" * 60)
    print("Phase 2/4: TTS Generation")
    print("=" * 60)

    import edge_tts

    dialogues = [s for s in SHOTS if s.get("dialogue")]
    print(f"Dialogue segments: {len(dialogues)}")

    for i, shot in enumerate(dialogues, 1):
        dlg = shot["dialogue"]
        output_path = os.path.join(AUDIO_DIR, f"{shot['shot_id']}.mp3")
        shot["audio_file"] = output_path

        print(f"[{i}/{len(dialogues)}] {shot['shot_id']}: \"{dlg['text'][:30]}...\"")
        communicate = edge_tts.Communicate(
            text=dlg["text"],
            voice=dlg["voice"],
            rate=dlg.get("rate", "+0%"),
        )
        await communicate.save(output_path)
        size = os.path.getsize(output_path)
        print(f"  [OK] {size} bytes")

    print(f"TTS Complete: {len(dialogues)} files")


def composite_video():
    """Composite all 18 shots into final video using FFmpeg."""
    print("\n" + "=" * 60)
    print("Phase 3/4: Video Compositing")
    print("=" * 60)

    # Step 1: Create video segments from images
    segment_files = []
    for i, shot in enumerate(SHOTS):
        image_path = os.path.join(GENERATED, f"{shot['shot_id']}.jpg")
        seg_path = os.path.join(TEMP, f"seg_{i:03d}.mp4")

        if not os.path.exists(image_path):
            print(f"  [SKIP] {shot['shot_id']} — no image file")
            continue

        duration = shot["duration_s"]
        effect = shot.get("effect", "static")

        if effect in ("slow_zoom_in", "pan_right"):
            vf = f"zoompan=z='min(zoom+0.0004,1.12)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
        elif effect == "dramatic_zoom":
            vf = f"zoompan=z='min(zoom+0.0008,1.18)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
        else:
            vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=24"

        subtitle = shot.get("subtitle", "")
        if subtitle:
            safe = subtitle.replace("'", "\\'").replace(":", "\\:")
            vf += f",drawtext=text='{safe}':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.4:boxborderw=6:x=(w-text_w)/2:y=h-th-50:enable='between(t,0.5,{duration})'"

        result = subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", vf, "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
            "-pix_fmt", "yuv420p", "-r", "24", "-an", seg_path,
        ], capture_output=True, text=True)

        if result.returncode == 0:
            segment_files.append(seg_path)
            print(f"  [{i+1:2d}/18] {shot['shot_id']} ({duration}s) OK")
        else:
            print(f"  [{i+1:2d}/18] {shot['shot_id']} FAIL: {result.stderr[:100]}")

    print(f"\nVideo segments: {len(segment_files)}/18")

    # Step 2: Create audio track
    audio_track = os.path.join(TEMP, "audio_full.aac")
    silence_file = os.path.join(TEMP, "silence.wav")
    total_duration = sum(s["duration_s"] for s in SHOTS)

    # Generate base silence
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(total_duration),
        silence_file,
    ], check=True, capture_output=True)

    # Build filter complex for mixing all dialogue tracks
    filter_inputs = ["-i", silence_file]
    filter_labels = ["[0:a]"]
    mix_inputs = ["[0a]"]
    dialogue_count = 0

    # Calculate cumulative start times for each shot
    cumulative_time = 0.0
    shot_start_times = {}
    for shot in SHOTS:
        shot_start_times[shot["shot_id"]] = cumulative_time
        cumulative_time += shot["duration_s"]

    for shot in SHOTS:
        audio_file = shot.get("audio_file")
        if audio_file and os.path.exists(audio_file):
            dialogue_count += 1
            filter_inputs.extend(["-i", audio_file])
            label = f"[{dialogue_count}:a]"
            filter_labels.append(label)
            delay_ms = int((shot_start_times[shot["shot_id"]] + shot["dialogue"]["start_s"]) * 1000)
            mix_inputs.append(f"[{dialogue_count}d]")
            filter_labels.append(f"{label}adelay={delay_ms}|{delay_ms}[{dialogue_count}d]")

    mix_expr = "".join(mix_inputs) + f"amix=inputs={1 + dialogue_count}:duration=first:dropout_transition=0.3"

    audio_cmd = [
        "ffmpeg", "-y",
        *filter_inputs,
        "-filter_complex", ";".join(filter_labels) + ";" + mix_expr,
        "-c:a", "aac", "-b:a", "128k",
        audio_track,
    ]

    result = subprocess.run(audio_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Audio track: OK ({dialogue_count} dialogues mixed)")
    else:
        print(f"Audio track: using silence only ({dialogue_count} dialogues)")
        subprocess.run([
            "ffmpeg", "-y", "-i", silence_file,
            "-c:a", "aac", "-b:a", "128k", audio_track,
        ], check=True, capture_output=True)

    # Step 3: Concat all video segments
    concat_list = os.path.join(TEMP, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in segment_files:
            f.write(f"file '{seg.replace(chr(92), '/')}'\n")

    video_only = os.path.join(TEMP, "video_only.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", "24", "-an",
        video_only,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Concat fallback: {result.stderr[:200]}")
        # Fallback approach
        inputs = []
        filters = []
        for j, seg in enumerate(segment_files):
            inputs.extend(["-i", seg])
            filters.append(f"[{j}:v]")
        fc = "".join(filters) + f"concat=n={len(segment_files)}:v=1[outv]"
        subprocess.run([
            "ffmpeg", "-y", *inputs,
            "-filter_complex", fc, "-map", "[outv]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            video_only,
        ], check=True, capture_output=True)

    # Step 4: Mix video + audio → final
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_only,
        "-i", audio_track,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", OUTPUT,
    ], check=True, capture_output=True)

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"\n[SUCCESS] Episode 1 generated!")
    print(f"  Path: {OUTPUT}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Duration: {total_duration:.0f}s")
    print(f"  Shots: {len(segment_files)}/18 with images")
    print(f"  Dialogue: {dialogue_count} segments with voice")


async def main():
    total_start = time.time()

    # Phase 1: Images
    provider = HunyuanImageProvider(api_key=API_KEY)
    image_results = await generate_all_images(provider)
    await provider.close()

    # Phase 2: TTS
    await generate_all_tts()

    # Phase 3 & 4: Composite
    composite_video()

    # Phase 5: Report
    total_elapsed = time.time() - total_start
    success_count = sum(1 for r in image_results.values() if r.success)
    print(f"\n{'=' * 60}")
    print(f"PRODUCTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total time: {total_elapsed:.0f}s")
    print(f"Images: {success_count}/18 generated")
    print(f"TTS: {sum(1 for s in SHOTS if s.get('audio_file') and os.path.exists(s['audio_file']))} files")
    print(f"Output: {OUTPUT}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
