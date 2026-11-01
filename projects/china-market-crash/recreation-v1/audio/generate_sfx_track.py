#!/usr/bin/env python3
"""
generate_sfx_track.py
Synthesizes targeted micro-sound effects via earshot and choreographs
a balanced, calibrated SFX bed aligned to HyperFrames keyframes.
"""

import os
import subprocess
import wave
import numpy as np
import soundfile as sf
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent
SFX_RAW = AUDIO_DIR / "sfx_raw"
SFX_RAW.mkdir(parents=True, exist_ok=True)

TARGET_SR = 24000
TOTAL_DURATION = 42.55
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)

# Defined cue points: (sound_id, timestamp_sec, gain_linear)
CUES = [
    ("whoosh_fast/crisp", 0.2, 0.40),
    ("cut_hit/sub", 3.8, 0.75),
    ("glitch/mid", 4.0, 0.45),
    ("swipe/glide", 9.8, 0.45),
    ("downlifter/sub_sink", 14.2, 0.50),
    ("toggle/latch", 15.0, 0.60),
    ("whoosh_fast/tight", 20.1, 0.45),
    ("typing_key/thock", 21.8, 0.35),
    ("typing_key/thock", 22.4, 0.35),
    ("typing_key/thock", 23.0, 0.35),
    ("glitch/crush", 24.5, 0.50),
    ("glitch/data", 27.0, 0.40),
    ("swipe/velvet", 31.8, 0.45),
    ("logo_sting/soft_bloom", 34.8, 0.50),
    ("shimmer/m5", 38.2, 0.45),
]

def render_cue(sound_id: str, out_path: Path):
    if out_path.exists():
        return
    repo_root = AUDIO_DIR.parent.parent.parent
    earshot_bin = repo_root / ".venv" / "bin" / "earshot"
    cmd = [
        str(earshot_bin),
        "sfx", "render",
        sound_id,
        "-o", str(out_path),
        "--sr", "48000"
    ]
    subprocess.run(cmd, check=True)

def read_resample_wav(path: Path, target_sr: int) -> np.ndarray:
    data, src_sr = sf.read(str(path))
    if data.ndim > 1:
        data = data.mean(axis=1)

    if src_sr != target_sr:
        num_target_samples = int(len(data) * target_sr / src_sr)
        data = np.interp(
            np.linspace(0, len(data), num_target_samples, endpoint=False),
            np.arange(len(data)),
            data
        )
    return data.astype(np.float32)

def main():
    print(f"🎵 Generating calibrated SFX track ({TOTAL_DURATION}s @ {TARGET_SR}Hz)...")
    master_track = np.zeros(TOTAL_SAMPLES, dtype=np.float32)

    for sound_id, start_sec, gain in CUES:
        safe_name = sound_id.replace("/", "_") + ".wav"
        raw_path = SFX_RAW / safe_name
        render_cue(sound_id, raw_path)
        samples = read_resample_wav(raw_path, TARGET_SR) * gain

        start_idx = int(start_sec * TARGET_SR)
        end_idx = min(start_idx + len(samples), TOTAL_SAMPLES)
        length_to_add = end_idx - start_idx
        if length_to_add > 0:
            master_track[start_idx:end_idx] += samples[:length_to_add]
            print(f"  • Placed '{sound_id}' at {start_sec:05.2f}s (gain: {gain:.2f})")

    # Soft peak limiter to prevent clipping
    peak = np.max(np.abs(master_track))
    if peak > 0.95:
        master_track = master_track * (0.95 / peak)
        print(f"  ⚡ Applied limiter: scaled by {(0.95/peak):.2f}")

    pcm_out = np.int16(np.clip(master_track * 32767.0, -32768, 32767))
    out_file = AUDIO_DIR / "sfx-track.wav"
    with wave.open(str(out_file), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_SR)
        w.writeframes(pcm_out.tobytes())

    print(f"✅ Generated master SFX track: {out_file} ({len(pcm_out)/TARGET_SR:.2f}s)")

if __name__ == "__main__":
    main()
