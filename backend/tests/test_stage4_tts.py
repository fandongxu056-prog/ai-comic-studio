"""Stage 4 TTS Test — generate dialogue audio via Edge-TTS (free).

Character voice mapping:
- 林深 (CHAR-0001): zh-CN-YunxiNeural — young male, slightly nervous delivery
- 周衍 (CHAR-0002): zh-CN-YunjianNeural — older male, calm and cold delivery
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "generated", "audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Dialogue from Stage 3 shot plan
DIALOGUES = [
    {
        "shot_id": "SH-E001-S001-005",
        "character_id": "CHAR-0001",
        "character_name": "林深",
        "text": "……这不可能。",
        "voice": "zh-CN-YunxiNeural",
        "rate": "-10%",  # slightly slower — shocked
        "file": "dialogue_S001_005_linshen.mp3",
    },
    {
        "shot_id": "SH-E001-S002-004",
        "character_id": "CHAR-0002",
        "character_name": "周衍",
        "text": "你提前来踩点了？",
        "voice": "zh-CN-YunjianNeural",
        "rate": "+0%",  # calm, measured
        "file": "dialogue_S002_004_zhouyan.mp3",
    },
    {
        "shot_id": "SH-E001-S002-005",
        "character_id": "CHAR-0002",
        "character_name": "周衍",
        "text": "我在那儿工作。周衍。你呢？是来杀人，还是来被杀？",
        "voice": "zh-CN-YunjianNeural",
        "rate": "+0%",  # perfectly calm — terrifying because it's so flat
        "file": "dialogue_S002_005_zhouyan.mp3",
    },
]


async def generate_tts():
    import edge_tts

    print("=" * 60)
    print("Stage 4 TTS Test — Edge-TTS (Free)")
    print("=" * 60)

    for i, dlg in enumerate(DIALOGUES, 1):
        output_path = os.path.join(OUTPUT_DIR, dlg["file"])
        print(f"\n[{i}/{len(DIALOGUES)}] {dlg['shot_id']}")
        print(f"  Character: {dlg['character_name']} ({dlg['voice']})")
        print(f"  Text: \"{dlg['text']}\"")
        print(f"  Rate: {dlg['rate']}")

        communicate = edge_tts.Communicate(
            text=dlg["text"],
            voice=dlg["voice"],
            rate=dlg["rate"],
        )
        await communicate.save(output_path)

        size = os.path.getsize(output_path)
        print(f"  [OK] Saved: {output_path} ({size} bytes)")

    print(f"\n[SUCCESS] TTS generation complete!")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Total files: {len(DIALOGUES)}")


if __name__ == "__main__":
    asyncio.run(generate_tts())
