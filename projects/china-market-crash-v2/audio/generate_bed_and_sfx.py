#!/usr/bin/env python3
"""
generate_bed_and_sfx.py
Synthesizes:
1. A dim, warm, hypnotic ambient thriller pad for China Market Crash v2.
2. Carefully choreographed tactile micro-SFX cues mapped to GSAP moments.
3. Mixes them into projects/china-market-crash-v2/audio/sfx-track.wav at 24kHz mono.
"""

import math
import subprocess
import wave
import numpy as np
import soundfile as sf
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent
SFX_RAW = AUDIO_DIR / "sfx_raw"
SFX_RAW.mkdir(parents=True, exist_ok=True)

TARGET_SR = 24000
TOTAL_DURATION = 66.0
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)

def generate_ambient_music_bed(duration_sec: float, sr: int) -> np.ndarray:
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    bed = np.zeros(total_samples, dtype=np.float32)

    # Slow, tense minor progression: Dm -> Bb -> Gm -> A
    chord_duration = duration_sec / 4.0
    chords = [
        [146.83, 174.61, 220.00, 293.66],  # Dm
        [116.54, 174.61, 233.08, 293.66],  # Bb
        [98.00,  146.83, 196.00, 293.66],  # Gm
        [110.00, 164.81, 220.00, 277.18]   # A
    ]

    for chord_idx, freqs in enumerate(chords):
        chord_start = chord_idx * chord_duration
        chord_end = min((chord_idx + 1) * chord_duration + 2.5, duration_sec)
        c_start_idx = int(chord_start * sr)
        c_end_idx = int(chord_end * sr)
        c_len = c_end_idx - c_start_idx
        if c_len <= 0:
            continue

        c_t = np.linspace(0, chord_end - chord_start, c_len, endpoint=False)
        chord_sig = np.zeros(c_len, dtype=np.float32)

        for freq in freqs:
            tone = (
                0.55 * np.sin(2 * np.pi * freq * c_t) +
                0.25 * np.sin(2 * np.pi * (freq * 1.003) * c_t) +
                0.20 * np.sin(2 * np.pi * (freq * 0.997) * c_t) +
                0.12 * np.sin(2 * np.pi * (freq * 2.0) * c_t)
            )
            chord_sig += tone

        attack_len = int(2.0 * sr)
        release_len = int(2.5 * sr)
        env = np.ones(c_len, dtype=np.float32)
        if c_len > attack_len:
            env[:attack_len] = np.linspace(0, 1, attack_len)
        if c_len > release_len:
            env[-release_len:] = np.linspace(1, 0, release_len)

        # Hypnotic LFO modulation
        lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.2 * c_t)
        chord_sig = chord_sig * env * lfo
        bed[c_start_idx:c_end_idx] += chord_sig

    # Deep sub-bass drone on 55 Hz (A1) / 73.4 Hz (D2)
    sub = 0.35 * np.sin(2 * np.pi * 55.0 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * t))
    bed += sub

    # Global fade in (1.5s) and fade out (3.0s)
    fade_in = int(1.5 * sr)
    fade_out = int(3.0 * sr)
    bed[:fade_in] *= np.linspace(0, 1, fade_in)
    bed[-fade_out:] *= np.linspace(1, 0, fade_out)

    bed_peak = np.max(np.abs(bed))
    if bed_peak > 0:
        bed = bed / bed_peak * 0.075  # Soft background pad ~ -22.5 dBFS

    return bed

def read_resample_wav(path: Path, target_sr: int) -> np.ndarray:
    data, src_sr = sf.read(str(path))
    if data.ndim > 1:
        data = data.mean(axis=1)
    if src_sr != target_sr:
        num_target_samples = int(len(data) * target_sr / src_sr)
        orig_indices = np.linspace(0, len(data) - 1, len(data))
        target_indices = np.linspace(0, len(data) - 1, num_target_samples)
        data = np.interp(target_indices, orig_indices, data).astype(np.float32)
    return data

def main():
    print("Generating cinematic ambient music bed...")
    bed = generate_ambient_music_bed(TOTAL_DURATION, TARGET_SR)

    # Cues list: (timestamp_sec, sfx_file, gain)
    cues = [
        (0.2,   "toggle_micro.wav",        0.35),
        (1.2,   "fit_bell_small_bell.wav", 0.40),
        (11.5,  "toggle_latch.wav",        0.45),
        (17.65, "cut_hit_sub.wav",         0.70),
        (18.0,  "downlifter_sub_sink.wav", 0.55),
        (23.0,  "glitch_data.wav",         0.45),
        (23.8,  "glitch_mid.wav",          0.40),
        (33.25, "downlifter_sub_sink.wav", 0.65),
        (34.0,  "typing_key_thock.wav",    0.35),
        (34.3,  "typing_key_light.wav",    0.30),
        (34.6,  "typing_key_thock.wav",    0.35),
        (35.0,  "typing_key_light.wav",    0.30),
        (50.02, "glitch_crush.wav",        0.65),
        (50.5,  "cut_hit_sub.wav",         0.60),
        (51.8,  "logo_sting_soft_bloom.wav", 0.50),
    ]

    sfx_track = np.copy(bed)

    for at_sec, filename, gain in cues:
        sfx_path = SFX_RAW / filename
        if not sfx_path.exists():
            print(f"Warning: {filename} not found in sfx_raw, skipping.")
            continue
        data = read_resample_wav(sfx_path, TARGET_SR) * gain
        start_idx = int(at_sec * TARGET_SR)
        end_idx = min(start_idx + len(data), TOTAL_SAMPLES)
        length_to_add = end_idx - start_idx
        if length_to_add > 0:
            sfx_track[start_idx:end_idx] += data[:length_to_add]

    # Peak limiter at -3 dBFS to prevent clipping
    peak = np.max(np.abs(sfx_track))
    if peak > 0.70:
        sfx_track = sfx_track / peak * 0.70

    out_file = AUDIO_DIR / "sfx-track.wav"
    sf.write(str(out_file), sfx_track, TARGET_SR, subtype="PCM_16")
    print(f"Rendered SFX track to {out_file} ({TOTAL_DURATION:.2f}s, peak {20 * math.log10(np.max(np.abs(sfx_track))):.2f} dBFS)")

if __name__ == "__main__":
    main()

