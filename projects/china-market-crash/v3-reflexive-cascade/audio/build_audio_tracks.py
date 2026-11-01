#!/usr/bin/env python3
"""
build_audio_tracks.py for china-market-crash-v3

Generates:
1. audio/bgm.wav: Dim, themed, continuous minimalist suspense music bed (~ -24 dBFS).
2. audio/sfx-track.wav: Tactile micro-SFX foley mapped to every visual beat (no transition whooshes).
"""

import math
from pathlib import Path
import numpy as np
import soundfile as sf

AUDIO_DIR = Path(__file__).resolve().parent
SFX_RAW = AUDIO_DIR / "sfx_raw"

TARGET_SR = 24000
TOTAL_DURATION = 66.0
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)

def generate_ambient_music_bed(duration_sec: float, sr: int) -> np.ndarray:
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    bed = np.zeros(total_samples, dtype=np.float32)

    # Minor suspense progression: Dm -> Bb -> Gm -> A
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

    # Deep sub-bass pulse on 55 Hz (A1)
    sub = 0.35 * np.sin(2 * np.pi * 55.0 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * t))
    bed += sub

    # Global fade in (1.0s) and fade out (2.5s)
    fade_in = int(1.0 * sr)
    fade_out = int(2.5 * sr)
    bed[:fade_in] *= np.linspace(0, 1, fade_in)
    bed[-fade_out:] *= np.linspace(1, 0, fade_out)

    # Scale to ~ -24 dBFS
    bed_peak = np.max(np.abs(bed))
    if bed_peak > 0:
        bed = bed / bed_peak * 0.065

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
    print("1. Generating dim themed background music bed (audio/bgm.wav)...")
    bgm = generate_ambient_music_bed(TOTAL_DURATION, TARGET_SR)
    bgm_file = AUDIO_DIR / "bgm.wav"
    sf.write(str(bgm_file), bgm, TARGET_SR, subtype="PCM_16")
    bgm_db = 20 * math.log10(np.max(np.abs(bgm)))
    print(f"   Saved bgm.wav (duration {TOTAL_DURATION:.1f}s, peak {bgm_db:.1f} dBFS)")

    print("2. Generating micro-foley SFX track (audio/sfx-track.wav)...")
    sfx_track = np.zeros(TOTAL_SAMPLES, dtype=np.float32)

    # Fine-tuned micro-cues without transition whooshes
    cues = [
        # Scene 1: Euphoria & Borrowed Money
        (0.2,   "toggle_micro.wav",        0.30),
        (1.0,   "fit_bell_small_bell.wav", 0.35),
        (3.8,   "toggle_micro.wav",        0.25),
        (4.4,   "toggle_micro.wav",        0.25),
        (5.0,   "toggle_micro.wav",        0.25),
        (7.5,   "shimmer_m5.wav",          0.30),
        (11.5,  "toggle_latch.wav",        0.40),
        (12.0,  "typing_key_thock.wav",    0.35),
        (14.8,  "glitch_data.wav",         0.35),

        # Scene 2: The Trap Snaps
        (18.0,  "glitch_mid.wav",          0.45),
        (20.8,  "toggle_micro.wav",        0.30),
        (21.5,  "downlifter_sub_sink.wav", 0.50),
        (25.0,  "fit_bell_small_bell.wav", 0.35),
        (25.6,  "fit_bell_small_bell.wav", 0.35),
        (26.2,  "glitch_data.wav",         0.40),
        (29.0,  "glitch_crush.wav",        0.55),
        (29.8,  "cut_hit_sub.wav",         0.65),

        # Scene 3: The Human Stampede
        (33.8,  "toggle_latch.wav",        0.45),
        (35.5,  "glitch_data.wav",         0.40),
        (37.0,  "downlifter_sub_sink.wav", 0.55),
        (40.5,  "glitch_crush.wav",        0.60),
        (41.2,  "downlifter_sub_sink.wav", 0.55),
        (45.2,  "typing_key_thock.wav",    0.40),
        (46.0,  "glitch_mid.wav",          0.45),

        # Scene 4: The Broken Spell
        (50.6,  "logo_sting_soft_bloom.wav", 0.45),
        (53.8,  "toggle_latch.wav",        0.40),
        (54.8,  "glitch_crush.wav",        0.55),
        (57.5,  "cut_hit_sub.wav",         0.60),
        (58.2,  "typing_key_thock.wav",    0.35),
        (61.8,  "logo_sting_soft_bloom.wav", 0.45),
    ]

    for at_sec, filename, gain in cues:
        sfx_path = SFX_RAW / filename
        if not sfx_path.exists():
            continue
        data = read_resample_wav(sfx_path, TARGET_SR) * gain
        start_idx = int(at_sec * TARGET_SR)
        end_idx = min(start_idx + len(data), TOTAL_SAMPLES)
        length_to_add = end_idx - start_idx
        if length_to_add > 0:
            sfx_track[start_idx:end_idx] += data[:length_to_add]

    # Limiter at -6 dBFS
    peak = np.max(np.abs(sfx_track))
    if peak > 0.50:
        sfx_track = sfx_track / peak * 0.50

    sfx_file = AUDIO_DIR / "sfx-track.wav"
    sf.write(str(sfx_file), sfx_track, TARGET_SR, subtype="PCM_16")
    sfx_db = 20 * math.log10(np.max(np.abs(sfx_track)))
    print(f"   Saved sfx-track.wav (duration {TOTAL_DURATION:.1f}s, peak {sfx_db:.1f} dBFS)")
    print("Audio track synthesis complete.")

if __name__ == "__main__":
    main()

