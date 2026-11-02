#!/usr/bin/env python3
"""
generate_smart_narration.py — Synthesize Smart Narration for china-market-crash-v3.

Uses kokoro-smart-tts-skill:
- Documentary multi-voice blend: am_michael:0.60,am_adam:0.40
- Calibrated speeds to align with visual transitions (0.0s, 17.65s, 33.25s, 50.025s, 66.0s)
- Generates s1.wav, s2.wav, s3.wav, s4.wav and master narration-full.wav
- Updates timeline.json
"""

import json
import math
import wave
from pathlib import Path
import numpy as np

# Load smart skill components
REPO_ROOT = Path(__file__).resolve().parents[3]
SMART_SKILL = REPO_ROOT / ".claude" / "skills" / "kokoro-smart-tts-skill" / "scripts"
import sys
if str(SMART_SKILL) not in sys.path:
    sys.path.insert(0, str(SMART_SKILL))

from preprocessor import preprocess_for_kokoro
from voice_advisor import parse_voice_weights, blend_voice_tensors
from kokoro import KPipeline

AUDIO_DIR = Path(__file__).resolve().parent
TARGET_SR = 24000
TOTAL_DURATION = 66.0
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)

SCENES = [
    {
        "id": "s1",
        "title": "The Euphoria & The Hidden Wire",
        "text": "It was supposed to be easy money. In early 2026, millions of everyday people across China—teachers, cab drivers, students—watched their trading apps light up green on the morning commute. The rally felt unstoppable. But behind the hype lay a quiet time bomb: almost everyone was buying on borrowed money.",
        "start_sec": 0.0,
        "max_window_sec": 17.65,
        "speed": 1.27
    },
    {
        "id": "s2",
        "title": "The Trap Snaps",
        "text": "Then, the market blinked. Just an ordinary two-percent dip. But when you trade with triple leverage, a tiny tremor isn't a dip—it's an execution order. Before traders could even unlock their screens, brokerage algorithms took control, dumping collateral into freefall.",
        "start_sec": 17.65,
        "max_window_sec": 15.60,
        "speed": 1.25
    },
    {
        "id": "s3",
        "title": "The Human Stampede",
        "text": "On Wall Street, big banks absorb the shock. But ninety percent of China's market is retail. It's a crowded theater with only one exit door. When automated margin calls hit thirty million phones at the exact same second, panic went viral. Everyone smashed sell—into an empty room.",
        "start_sec": 33.25,
        "max_window_sec": 16.775,
        "speed": 1.25
    },
    {
        "id": "s4",
        "title": "The Broken Spell",
        "text": "Beijing threw hundreds of billions into the fire. State funds bought index funds. Regulators banned short selling. But when a bubble built on borrowed faith bursts, you can't print confidence. Two trillion dollars didn't just vanish—the illusion broke.",
        "start_sec": 50.025,
        "max_window_sec": 15.975,
        "speed": 1.20
    }
]

VOICE_SPEC = "am_michael:0.60,am_adam:0.40"

def write_wav(path: Path, pcm: np.ndarray, sr: int = TARGET_SR):
    pcm_clipped = np.int16(np.clip(pcm * 32767.0, -32768, 32767))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(pcm_clipped.tobytes())

def main():
    print("=" * 65)
    print(f"Synthesizing Smart Narration for china-market-crash-v3")
    print(f"Voice Blend: {VOICE_SPEC} (Documentary Thriller)")
    print("=" * 65)

    pipe = KPipeline(lang_code="a")
    weights = parse_voice_weights(VOICE_SPEC)
    blend_tensor = blend_voice_tensors(pipe, weights)

    master_track = np.zeros(TOTAL_SAMPLES, dtype=np.float32)
    timeline_records = []

    for sc in SCENES:
        sid = sc["id"]
        raw_text = sc["text"]
        spd = sc["speed"]
        start_sec = sc["start_sec"]

        # Preprocess text
        norm_text, _ = preprocess_for_kokoro(raw_text, preset="documentary")
        print(f"\n[{sid.upper()}] Synthesizing at speed {spd}...")

        chunks = []
        for res in pipe(norm_text, voice=blend_tensor, speed=spd):
            chunks.append(res.audio.numpy())

        if not chunks:
            raise RuntimeError(f"No audio produced for {sid}")

        clip_audio = np.concatenate(chunks)
        dur = len(clip_audio) / float(TARGET_SR)
        end_sec = start_sec + dur

        # Fade edges (4ms) to eliminate zero-crossing artifacts
        fade_len = int(TARGET_SR * 0.004)
        if len(clip_audio) > 2 * fade_len:
            clip_audio[:fade_len] *= np.linspace(0.0, 1.0, fade_len)
            clip_audio[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)

        # Write individual scene WAV
        clip_path = AUDIO_DIR / f"{sid}.wav"
        write_wav(clip_path, clip_audio, TARGET_SR)
        print(f"   Saved {clip_path.name}: {dur:.3f}s (window: {start_sec:.2f}s -> {start_sec + sc['max_window_sec']:.2f}s)")

        # Place onto master track at exact scene start frame
        start_idx = int(start_sec * TARGET_SR)
        end_idx = min(start_idx + len(clip_audio), TOTAL_SAMPLES)
        length_to_copy = end_idx - start_idx
        master_track[start_idx:end_idx] = clip_audio[:length_to_copy]

        timeline_records.append({
            "id": sid,
            "title": sc["title"],
            "text": norm_text,
            "clip_path": f"audio/{sid}.wav",
            "duration_sec": round(dur, 3),
            "start_time_sec": round(start_sec, 3),
            "end_time_sec": round(end_sec, 3)
        })

    # Peak limit master narration track at -1.5 dBFS
    peak = np.max(np.abs(master_track))
    if peak > 0.841:
        master_track = master_track / peak * 0.841

    master_path = AUDIO_DIR / "narration-full.wav"
    write_wav(master_path, master_track, TARGET_SR)
    print(f"\nSaved master track: {master_path} (66.0s)")

    # Update timeline.json
    timeline_data = {
        "project": "china-market-crash-v3",
        "voice": VOICE_SPEC,
        "preset": "documentary",
        "total_duration_sec": TOTAL_DURATION,
        "target_fps": 30,
        "total_frames": int(TOTAL_DURATION * 30),
        "scenes": timeline_records
    }
    timeline_file = AUDIO_DIR / "timeline.json"
    with open(timeline_file, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2)
    print(f"Updated {timeline_file}")

if __name__ == "__main__":
    main()
