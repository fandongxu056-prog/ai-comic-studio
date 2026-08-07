"""Stage 4 v2 — Qwen Wanx images + Hunyuan Video 1.5 + Edge-TTS + FFmpeg.

Architecture:
  1. QwenImageProvider → 18 keyframe images (anime style, consistent prompts)
  2. HunyuanVideoProvider → 3-4 shot videos (image-to-video, ~5s each)
  3. Edge-TTS → dialogue audio
  4. FFmpeg → composite video + audio

API Keys (test only):
  Qwen:  sk-ws-H.ERRIPXH...
  Video: sk-WM7sbvi...
"""

import asyncio
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.stage4_production.qwen_image_provider import QwenImageProvider

QWEN_KEY = "sk-ws-H.ERRIPXH.4Yib.MEYCIQCCs3CUUSD3sCs9TpDBn-8L4QbhZ03_fuKRVAL5rCwHqAIhAKSFO-h3O3dYlo6pEmv92J1qADce3xAx_v01d4aimoF8"
VIDEO_KEY = "sk-WM7sbviW1l5fTFOLtI56fmlg8ICNqfmMk5B79lCTrtKq68N1"

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
GEN = os.path.join(BASE, "generated")
AUDIO = os.path.join(GEN, "audio")
TEMP = os.path.join(GEN, "temp_v2")
OUTPUT = os.path.join(GEN, "episode_001_v2.mp4")
os.makedirs(AUDIO, exist_ok=True)
os.makedirs(TEMP, exist_ok=True)

# ── 18 Shots (same as before) ──
SHOTS = [
    {"id":"SH-E001-S001-001","dur":5.0,"prompt":"long shot through rain window, dark open tech office at night, single blue monitor glow, man in gray hoodie at desk, Shanghai skyline in storm, cold blue lighting","neg":"warm, daylight, realistic face","sz":"1280*720"},
    {"id":"SH-E001-S001-002","dur":4.0,"prompt":"close up, hands nervously typing keyboard, cold coffee mug with dried stains, blue progress bar at 99%, burn scar on right forearm in blue glow","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S001-003","dur":4.0,"prompt":"medium close up, 28-year-old Chinese man, single eyelid narrow eyes, pale skin dark circles, messy black hair, face half blue monitor light half orange alert, shocked expression, gray hoodie, burn scar on forearm","neg":"realistic face, photograph, 3D","sz":"1280*720"},
    {"id":"SH-E001-S001-004","dur":2.5,"prompt":"extreme close up, shattered coffee mug on dark floor, broken shards reflecting distorted face, spilled coffee with orange light, dutch angle","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S001-005","dur":5.0,"prompt":"medium shot, man standing gripping desk, round glasses reflecting screen text, gray hoodie sleeves pushed up, burn scar clearly visible on right arm, tense body language, dark office","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S001-006","dur":8.0,"prompt":"high angle over-shoulder, man frozen at keyboard, orange warning on dark blue screen, rain pounding window, tense frozen moment","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S002-001","dur":4.0,"prompt":"extreme long shot low angle, modern glass skyscraper in gray fog, tiny figure in black jacket looking up, overcast Shanghai morning, cold gray","neg":"warm, realistic","sz":"1280*720"},
    {"id":"SH-E001-S002-002","dur":5.0,"prompt":"medium shot, man in black jacket walking through luxury marble lobby, symmetrical empty space, security guard glancing up, paranoid atmosphere","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S002-003","dur":3.0,"prompt":"medium close up inside mirrored elevator, man looking up surprised, elevator doors closing, hand with silver ring reaching in, cold white LED, tight space","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S002-004","dur":6.0,"prompt":"over-shoulder shot, navy blue suited shoulder foreground with silver ring, man in black jacket pressed against elevator wall, slight low angle, two reflections overlapping in mirror","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S002-005","dur":5.0,"prompt":"medium close up low angle, 30-year-old Chinese man square jaw, deep-set calm eyes, slicked dark brown hair, navy suit white shirt no tie, military posture, silver ring on left hand, cold intimidating presence, elevator","neg":"realistic face, photograph, 3D","sz":"1280*720"},
    {"id":"SH-E001-S002-006","dur":6.0,"prompt":"medium shot from elevator looking out, minimalist cold office corridor, one door slightly ajar leaking warm yellow light, man seen from behind frozen","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S003-001","dur":6.0,"prompt":"medium shot, small dark apartment, wet street reflecting orange light through window, entire wall covered in handwritten notes with red string, man in gray t-shirt on floor with laptop, exhausted, burn scar visible, single desk lamp","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S003-002","dur":7.0,"prompt":"close up over shoulder, man staring at laptop showing code, dark navy interface with orange alert text, shocked expression in screen reflection, dark apartment","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S003-003","dur":4.0,"prompt":"medium shot POV from behind monitor, man standing up knocking over chair, red alert box casting red light on face, panic in eyes, gray t-shirt, dark apartment","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S003-004","dur":5.0,"prompt":"medium full shot, man in gray t-shirt turning slowly, looking through frosted glass door into dark corridor, black silhouette visible behind glass, silver ring reflecting cold light, wall of notes, terrifying stillness","neg":"realistic, warm, photograph","sz":"1280*720"},
    {"id":"SH-E001-S003-005","dur":4.0,"prompt":"extreme close up of terrified eye, pupil dilated, dark glass door with silver light point growing in pupil, sweat on brow, split composition with silhouette raising hand","neg":"realistic, photograph","sz":"1280*720"},
    {"id":"SH-E001-S003-006","dur":4.0,"prompt":"pure black screen, barely visible silhouette, single silver ring gleam as only light, minimal dark atmospheric","neg":"realistic, photograph, bright","sz":"1280*720"},
]


async def generate_images():
    """Phase 1: Generate all 18 images via Qwen Wanx."""
    print("=" * 60)
    print("Phase 1/4: Qwen Wanx Image Generation (18 shots)")
    print("=" * 60)

    provider = QwenImageProvider(api_key=QWEN_KEY)
    results = {}
    total_start = time.time()

    scene_names = {1: "Office", 2: "Financial Center", 3: "Apartment"}
    prev_scene = 0

    for i, shot in enumerate(SHOTS, 1):
        scene = 1 if i <= 6 else (2 if i <= 12 else 3)
        if scene != prev_scene:
            print(f"\n-- Scene {scene}: {scene_names[scene]} --")
            prev_scene = scene

        print(f"[{i:2d}/18] {shot['id']}...", end=" ", flush=True)
        result = await provider.generate(
            shot_id=shot["id"],
            prompt=shot["prompt"],
            negative_prompt=shot.get("neg", ""),
            size=shot["sz"],
        )
        results[shot["id"]] = result

        if result.success:
            shot["image_url"] = result.image_url
            shot["image_ok"] = True
            print(f"OK ({result.generation_time_ms}ms)")
            # Download immediately
            try:
                path = os.path.join(GEN, f"{shot['id']}.jpg")
                urllib.request.urlretrieve(result.image_url, path)
            except: pass
        else:
            shot["image_ok"] = False
            print(f"FAIL: {result.error_message[:80]}")

        await asyncio.sleep(0.5)

    await provider.close()
    success = sum(1 for r in results.values() if r.success)
    print(f"\nImages: {success}/18 in {time.time()-total_start:.0f}s")
    return results


async def generate_videos(shots_to_animate: list[int]):
    """Phase 2: Generate video segments for selected shots via Hunyuan Video 1.5.

    Only animate 4-5 key shots (video takes ~60s each).
    Static shots get Ken Burns effect instead.
    """
    print("\n" + "=" * 60)
    print(f"Phase 2/4: Hunyuan Video 1.5 ({len(shots_to_animate)} shots)")
    print("=" * 60)

    import httpx

    async with httpx.AsyncClient(
        base_url="https://tokenhub.tencentmaas.com",
        headers={"Authorization": f"Bearer {VIDEO_KEY}"},
        timeout=300.0,
    ) as client:

        for idx in shots_to_animate:
            shot = SHOTS[idx]
            if not shot.get("image_ok"):
                print(f"  [{shot['id']}] SKIP — no image")
                continue

            # Build video prompt from shot data
            video_prompt = f"日漫动画风格, {shot['prompt'][:200]}, slow cinematic camera movement, 5 second clip, consistent anime style"

            print(f"  [{shot['id']}] Submitting video...")
            # Submit
            submit = await client.post("/v1/api/video/submit", json={
                "model": "hy-video-1.5",
                "prompt": video_prompt,
            })
            submit.raise_for_status()
            job = submit.json()
            job_id = job.get("id", "")

            if not job_id:
                print(f"    FAIL: no job_id")
                continue

            # Poll
            for poll in range(30):
                await asyncio.sleep(5)
                q = await client.post("/v1/api/video/query", json={
                    "model": "hy-video-1.5", "id": job_id,
                })
                q.raise_for_status()
                qd = q.json()
                status = qd.get("status", "?")

                if status == "completed":
                    url = qd.get("data", {}).get("url", "")
                    shot["video_url"] = url
                    print(f"    OK (poll {poll+1})")
                    # Download
                    try:
                        path = os.path.join(GEN, f"{shot['id']}_video.mp4")
                        urllib.request.urlretrieve(url, path)
                        shot["video_ok"] = True
                    except:
                        shot["video_ok"] = False
                    break
                elif status == "failed":
                    print(f"    FAILED")
                    break

                if poll % 4 == 0:
                    print(f"    polling... ({poll+1}/30)")


async def generate_tts():
    """Phase 3: Generate dialogue audio."""
    print("\n" + "=" * 60)
    print("Phase 3/4: Edge-TTS Audio")
    print("=" * 60)

    import edge_tts

    dialogues = [
        {"id": "SH-E001-S001-005", "text": "……这不可能。", "voice": "zh-CN-YunxiNeural", "rate": "-10%"},
        {"id": "SH-E001-S002-004", "text": "你提前来踩点了？", "voice": "zh-CN-YunjianNeural", "rate": "+0%"},
        {"id": "SH-E001-S002-005", "text": "我在那儿工作。周衍。你呢？是来杀人，还是来被杀？", "voice": "zh-CN-YunjianNeural", "rate": "+0%"},
    ]

    for dlg in dialogues:
        path = os.path.join(AUDIO, f"{dlg['id']}.mp3")
        print(f"  {dlg['id']}: \"{dlg['text'][:30]}...\"")
        c = edge_tts.Communicate(text=dlg["text"], voice=dlg["voice"], rate=dlg["rate"])
        await c.save(path)
        # Store reference in shot
        for s in SHOTS:
            if s["id"] == dlg["id"]:
                s["audio_file"] = path

    print(f"  Done: {len(dialogues)} files")


def composite_video():
    """Phase 4: Composite everything into final MP4."""
    print("\n" + "=" * 60)
    print("Phase 4/4: FFmpeg Compositing")
    print("=" * 60)

    total_dur = 0.0
    seg_files = []
    audio_inputs = ["-i", os.path.join(TEMP, "silence.wav")]
    filter_labels = ["[0:a]"]
    mix_inputs = ["[0a]"]
    audio_count = 0

    # Generate silence base
    total = sum(s["dur"] for s in SHOTS)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(total), os.path.join(TEMP, "silence.wav")],
        check=True, capture_output=True)

    for i, shot in enumerate(SHOTS):
        seg = os.path.join(TEMP, f"seg_{i:03d}.mp4")
        img = os.path.join(GEN, f"{shot['id']}.jpg")
        dur = shot["dur"]
        shot_start = total_dur
        total_dur += dur

        if not os.path.exists(img):
            print(f"  [{i+1:2d}] {shot['id']} SKIP (no image)")
            continue

        # Check if we have a video for this shot
        video_file = os.path.join(GEN, f"{shot['id']}_video.mp4")
        if os.path.exists(video_file):
            # Use the actual video!
            seg = video_file
            print(f"  [{i+1:2d}] {shot['id']} VIDEO ({dur}s)")
            seg_files.append(seg)
        else:
            # Ken Burns from static image
            vf = f"zoompan=z='min(zoom+0.0005,1.12)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf, "-t", str(dur),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p",
                "-r", "24", "-an", seg], check=True, capture_output=True)
            seg_files.append(seg)
            print(f"  [{i+1:2d}] {shot['id']} still ({dur}s)")

        # Add dialogue audio at correct timing
        af = shot.get("audio_file")
        if af and os.path.exists(af):
            audio_count += 1
            audio_inputs.extend(["-i", af])
            idx = audio_count
            delay_ms = int(shot_start * 1000)
            filter_labels.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[d{idx}]")
            mix_inputs.append(f"[d{idx}]")

    # Concat video
    concat = os.path.join(TEMP, "concat.txt")
    with open(concat, "w") as f:
        for s in seg_files:
            f.write(f"file '{s.replace(chr(92), '/')}'\n")

    video_only = os.path.join(TEMP, "video_only.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-r", "24", "-an", video_only], check=True, capture_output=True)

    # Mix audio
    audio_out = os.path.join(TEMP, "audio.aac")
    if audio_count > 0:
        mix = "".join(filter_labels) + ";" + "".join(mix_inputs) + f"amix=inputs={1+audio_count}:duration=first:dropout_transition=0.3"
        subprocess.run(["ffmpeg", "-y", *audio_inputs, "-filter_complex", mix,
            "-c:a", "aac", "-b:a", "128k", audio_out], check=True, capture_output=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-i", os.path.join(TEMP, "silence.wav"),
            "-c:a", "aac", "-b:a", "128k", audio_out], check=True, capture_output=True)

    # Final mix
    subprocess.run(["ffmpeg", "-y", "-i", video_only, "-i", audio_out,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", OUTPUT],
        check=True, capture_output=True)

    size_mb = os.path.getsize(OUTPUT) / (1024*1024)
    print(f"\n[SUCCESS] {OUTPUT}")
    print(f"  {total_dur:.0f}s | {size_mb:.1f}MB | {len(seg_files)} segments")


async def main():
    t0 = time.time()

    # Phase 1: Images (all 18)
    await generate_images()

    # Phase 2: Video (4 key shots — the ones with most motion potential)
    video_shots = [2, 10, 15, 16]  # reaction, elevator confrontation, red alert, cliffhanger
    await generate_videos(video_shots)

    # Phase 3: TTS
    await generate_tts()

    # Phase 4: Composite
    composite_video()

    print(f"\nTotal: {time.time()-t0:.0f}s")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
