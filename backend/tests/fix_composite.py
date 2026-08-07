"""Fix: re-run just the compositing step with corrected FFmpeg audio mixing."""
import os, subprocess

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
GEN = os.path.join(BASE, "generated")
AUDIO = os.path.join(GEN, "audio")
TEMP = os.path.join(GEN, "temp_v2")
OUTPUT = os.path.join(GEN, "episode_001_v2.mp4")
os.makedirs(TEMP, exist_ok=True)

SHOTS = [
    {"id":"SH-E001-S001-001","dur":5.0},
    {"id":"SH-E001-S001-002","dur":4.0},
    {"id":"SH-E001-S001-003","dur":4.0},
    {"id":"SH-E001-S001-004","dur":2.5},
    {"id":"SH-E001-S001-005","dur":5.0,"audio":"audio/SH-E001-S001-005.mp3"},
    {"id":"SH-E001-S001-006","dur":8.0},
    {"id":"SH-E001-S002-001","dur":4.0},
    {"id":"SH-E001-S002-002","dur":5.0},
    {"id":"SH-E001-S002-003","dur":3.0},
    {"id":"SH-E001-S002-004","dur":6.0,"audio":"audio/SH-E001-S002-004.mp3"},
    {"id":"SH-E001-S002-005","dur":5.0,"audio":"audio/SH-E001-S002-005.mp3"},
    {"id":"SH-E001-S002-006","dur":6.0},
    {"id":"SH-E001-S003-001","dur":6.0},
    {"id":"SH-E001-S003-002","dur":7.0},
    {"id":"SH-E001-S003-003","dur":4.0},
    {"id":"SH-E001-S003-004","dur":5.0},
    {"id":"SH-E001-S003-005","dur":4.0},
    {"id":"SH-E001-S003-006","dur":4.0},
]

print("Phase 4 (fixed): Compositing 18 segments + audio")

# Step 1: Create video segments (use generated video files where available)
seg_files = []
total_dur = 0.0
shot_times = {}

for i, shot in enumerate(SHOTS):
    sid = shot["id"]
    dur = shot["dur"]
    shot_times[sid] = total_dur
    total_dur += dur

    # Check for I2V video file first
    video_file = os.path.join(GEN, f"{sid}_video.mp4")
    img_file = os.path.join(GEN, f"{sid}.jpg")

    if os.path.exists(video_file):
        seg_files.append(video_file)
        print(f"  [{i+1:2d}] {sid} VIDEO ({dur}s) — real animation")
    elif os.path.exists(img_file):
        seg = os.path.join(TEMP, f"seg_{i:03d}.mp4")
        vf = "zoompan=z='min(zoom+0.0005,1.12)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img_file, "-vf", vf, "-t", str(dur),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p",
            "-r", "24", "-an", seg], check=True, capture_output=True)
        seg_files.append(seg)
        print(f"  [{i+1:2d}] {sid} image ({dur}s)")
    else:
        print(f"  [{i+1:2d}] {sid} SKIP — no file")

# Step 2: Concat all video segments
concat_list = os.path.join(TEMP, "concat.txt")
with open(concat_list, "w") as f:
    for s in seg_files:
        f.write(f"file '{s.replace(chr(92), '/')}'\n")

video_only = os.path.join(TEMP, "video_only.mp4")
print(f"\nConcatenating {len(seg_files)} segments...")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
    "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
    "-r", "24", "-an", video_only], check=True, capture_output=True)
print("Video concat: OK")

# Step 3: Create audio — simpler approach
# First create a long silence file, then overlay each dialogue at the right time
silence = os.path.join(TEMP, "silence.wav")
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
    "-t", str(total_dur), silence], check=True, capture_output=True)

# Build filter complex for overlaying dialogues
# Approach: generate each dialogue as delayed audio, then amix all together
inputs = ["-i", silence]
filters = []
mix_labels = ["[0:a]"]
dlg_count = 0

for shot in SHOTS:
    af = shot.get("audio")
    if af:
        af_path = os.path.join(GEN, af)
        if os.path.exists(af_path):
            dlg_count += 1
            inputs.extend(["-i", af_path])
            delay_ms = int(shot_times[shot["id"]] * 1000)
            label = f"[{dlg_count}:a]"
            delayed = f"[dlg{dlg_count}]"
            filters.append(f"{label}adelay={delay_ms}|{delay_ms}{delayed}")
            mix_labels.append(delayed)
            print(f"  Dialogue {dlg_count}: {shot['id']} at {delay_ms}ms")

if dlg_count > 0:
    filter_complex = ";".join(filters) + ";" + "".join(mix_labels) + f"amix=inputs={1+dlg_count}:duration=first:dropout_transition=0.3"
    print(f"\nMixing audio with filter...")
else:
    filter_complex = "anull"
    print("No dialogue to mix")

audio_out = os.path.join(TEMP, "audio.aac")
cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-c:a", "aac", "-b:a", "128k", audio_out]
print(f"  FFmpeg cmd: {' '.join(cmd[:6])}...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"  Audio mix FAILED: {result.stderr[:300]}")
    # Fallback: just silence
    subprocess.run(["ffmpeg", "-y", "-i", silence, "-c:a", "aac", "-b:a", "128k", audio_out],
        check=True, capture_output=True)
    print("  Using silence fallback")
else:
    print("Audio mix: OK")

# Step 4: Combine video + audio
print("\nFinal assembly...")
subprocess.run(["ffmpeg", "-y", "-i", video_only, "-i", audio_out,
    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", OUTPUT],
    check=True, capture_output=True)

size = os.path.getsize(OUTPUT) / (1024*1024)
print(f"\n[SUCCESS] {OUTPUT}")
print(f"  {total_dur:.0f}s | {size:.1f}MB | {len(seg_files)} segments | {dlg_count} dialogues")
