#!/usr/bin/env python3
"""
Generate ambient synthesizer bed (bgm.wav) and tactile foley track (sfx-track.wav)
for benchmark-neural-network-v3.
"""

import math
import subprocess
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AUDIO_DIR.parent
EARSHOT_BIN = PROJECT_DIR.parent.parent / ".venv" / "bin" / "earshot"
TARGET_SR = 24000
TOTAL_DURATION = 24.75
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)


def generate_ambient_modular_bgm(duration_sec: float, sr: int) -> np.ndarray:
    """
    Generates a minimalist modular synthesizer bed (ambient drone + warm analog chords).
    Subtle, deep, elegant, eliminating dead air.
    """
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    bed = np.zeros(total_samples, dtype=np.float32)

    # 4 Harmonic progression chords: A minor -> F major -> C major -> G major (resolving)
    chord_roots = [
        [55.0, 110.0, 164.81, 220.0, 261.63],     # A1, A2, E3, A3, C4
        [43.65, 87.31, 130.81, 174.61, 261.63],   # F1, F2, C3, F3, C4
        [65.41, 130.81, 164.81, 196.0, 261.63],   # C2, C3, E3, G3, C4
        [49.0, 98.0, 146.83, 196.0, 293.66],      # G1, G2, D3, G3, D4
    ]
    chord_len = duration_sec / 4.0

    for idx, freqs in enumerate(chord_roots):
        c_start = idx * chord_len
        c_end = min((idx + 1) * chord_len + 2.0, duration_sec)
        i_start = int(c_start * sr)
        i_end = int(c_end * sr)
        n = i_end - i_start
        if n <= 0:
            continue

        c_t = np.linspace(0, c_end - c_start, n, endpoint=False)
        sig = np.zeros(n, dtype=np.float32)

        for f in freqs:
            # Fundamental + warm analog tube saturation
            h1 = np.sin(2 * np.pi * f * c_t)
            h2 = 0.28 * np.sin(2 * np.pi * (f * 2) * c_t)
            h3 = 0.12 * np.sin(2 * np.pi * (f * 3) * c_t)
            # Gentle analog chorus detune
            detune = 0.18 * np.sin(2 * np.pi * (f * 1.003) * c_t)
            # Slow LFO filter pulse
            lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.4 * c_t + idx)
            sig += (h1 + h2 + h3 + detune) * lfo

        sig /= len(freqs)

        # Crossfade envelope
        fade_len = int(1.2 * sr)
        env = np.ones(n, dtype=np.float32)
        if n > fade_len:
            env[:fade_len] = np.linspace(0, 1, fade_len)
            env[-fade_len:] = np.linspace(1, 0, fade_len)
        sig *= env
        bed[i_start:i_end] += sig

    # Global master volume scaling for background bed (~-24 dBFS)
    # Master fade in/out
    head_fade = int(0.6 * sr)
    tail_fade = int(2.0 * sr)
    bed[:head_fade] *= np.linspace(0, 1, head_fade)
    bed[-tail_fade:] *= np.linspace(1, 0, tail_fade)

    # Peak normalization to ~ -14 dBFS peak / -24 dBFS integrated
    peak = np.max(np.abs(bed))
    if peak > 0:
        bed = bed / peak * 0.20

    return bed.astype(np.float32)


def render_earshot_cue(cue_id: str, temp_dir: Path) -> np.ndarray:
    """Renders a cue using earshot sfx and returns audio array at TARGET_SR."""
    out_file = temp_dir / (cue_id.replace("/", "_") + ".wav")
    if not out_file.exists():
        subprocess.run([str(EARSHOT_BIN), "sfx", "render", cue_id, "-o", str(out_file)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    data, sr = sf.read(str(out_file))
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    if sr != TARGET_SR:
        # Resample via simple linear interpolation
        new_len = int(len(data) * TARGET_SR / sr)
        data = np.interp(np.linspace(0, len(data), new_len), np.arange(len(data)), data)
    return data.astype(np.float32)


def generate_foley_track() -> np.ndarray:
    """Mixes tactile micro-foley sound effects according to storyboard cues."""
    foley = np.zeros(TOTAL_SAMPLES, dtype=np.float32)

    with tempfile.TemporaryDirectory() as td:
        tpath = Path(td)

        # Cues schedule: (time_sec, cue_id, gain)
        cues = [
            # Scene 1: Input excitation & forward signal
            (0.1, "click/soft", 0.45),
            (1.2, "click/soft", 0.60),
            (1.8, "ui_pop/blip", 0.55),
            (3.2, "swipe/glide", 0.45),
            (4.8, "fit/bell/small_bell", 0.50),

            # Scene 2: Hidden layer expansion & activation
            (6.6, "click/thock", 0.55),
            (8.0, "typing_key/thock", 0.60),
            (9.8, "logo_sting/soft_bloom", 0.45),
            (11.5, "swipe/glide", 0.45),

            # Scene 3: Loss calculation & backpropagation wave
            (13.1, "click/snap", 0.55),
            (14.5, "cut_hit/punch", 0.65),
            (16.2, "whoosh_fast/crisp", 0.55),
            (18.0, "toggle/latch", 0.60),
            (18.8, "toggle/micro", 0.50),

            # Scene 4: Loss basin gradient descent & convergence
            (20.2, "swipe/glide", 0.45),
            (21.0, "fit/tick/domino", 0.50),
            # Rapid micro ticks for epoch counter (22.2 to 23.5)
            (22.2, "hover_tick/air", 0.35),
            (22.4, "hover_tick/air", 0.35),
            (22.6, "hover_tick/air", 0.35),
            (22.8, "hover_tick/air", 0.35),
            (23.0, "hover_tick/air", 0.35),
            (23.2, "hover_tick/air", 0.35),
            (24.0, "shimmer/m5", 0.70),
        ]

        for at_sec, cue_id, gain in cues:
            data = render_earshot_cue(cue_id, tpath)
            start_idx = int(at_sec * TARGET_SR)
            end_idx = min(start_idx + len(data), TOTAL_SAMPLES)
            chunk_len = end_idx - start_idx
            if chunk_len > 0:
                foley[start_idx:end_idx] += (data[:chunk_len] * gain)

    # Master ceiling
    peak = np.max(np.abs(foley))
    if peak > 0.85:
        foley = foley / peak * 0.85

    return foley.astype(np.float32)


def main():
    print(f"Generating audio bed and SFX for {PROJECT_DIR.name} ({TOTAL_DURATION}s @ {TARGET_SR}Hz)...")

    # 1. BGM bed
    bgm = generate_ambient_modular_bgm(TOTAL_DURATION, TARGET_SR)
    bgm_path = AUDIO_DIR / "bgm.wav"
    sf.write(str(bgm_path), bgm, TARGET_SR, subtype="PCM_16")
    print(f"  ✓ Wrote ambient synthesizer bed: {bgm_path}")

    # 2. SFX track
    sfx = generate_foley_track()
    sfx_path = AUDIO_DIR / "sfx-track.wav"
    sf.write(str(sfx_path), sfx, TARGET_SR, subtype="PCM_16")
    print(f"  ✓ Wrote choreographed SFX track: {sfx_path}")


if __name__ == "__main__":
    main()
