#!/usr/bin/env python3
"""
generate_bed_and_sfx.py for chai-masala-v2 explainer.
Synthesizes:
1. A warm, organic, acoustic & marimba ambient bed (Cmaj -> Gmaj -> Am -> Fmaj) at 24kHz mono -> audio/bgm.wav.
2. Tactile culinary micro-sound foley (mortar crack, water simmer, milk pour, kulhad clink) -> audio/sfx-track.wav.
"""

import math
import numpy as np
import soundfile as sf
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent
TARGET_SR = 24000
TOTAL_DURATION = 57.00
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)

def generate_warm_culinary_bgm(duration_sec: float, sr: int) -> np.ndarray:
    """
    Generates a warm, organic acoustic/marimba chord bed (C -> G -> Am -> F).
    """
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    bed = np.zeros(total_samples, dtype=np.float32)

    # Chords (Cmaj -> Gmaj -> Am -> Fmaj)
    # Warm rich fundamental + harmonics resembling acoustic wooden marimba & guitar
    chords = [
        [130.81, 164.81, 196.00, 261.63], # C3, E3, G3, C4
        [146.83, 196.00, 246.94, 293.66], # D3, G3, B3, D4
        [110.00, 164.81, 220.00, 261.63], # A2, E3, A3, C4
        [174.61, 220.00, 261.63, 349.23], # F3, A3, C4, F4
    ]
    chord_len_sec = duration_sec / 4.0

    for chord_idx, freqs in enumerate(chords):
        chord_start = chord_idx * chord_len_sec
        chord_end = min((chord_idx + 1) * chord_len_sec + 2.5, duration_sec)
        c_start_idx = int(chord_start * sr)
        c_end_idx = int(chord_end * sr)
        c_len = c_end_idx - c_start_idx
        if c_len <= 0:
            continue

        c_t = np.linspace(0, chord_end - chord_start, c_len, endpoint=False)
        chord_sig = np.zeros(c_len, dtype=np.float32)

        for freq in freqs:
            # Fundamental + soft warm wooden overtones
            h1 = np.sin(2 * np.pi * freq * c_t)
            h2 = 0.35 * np.sin(2 * np.pi * (freq * 2) * c_t)
            h3 = 0.15 * np.sin(2 * np.pi * (freq * 3) * c_t)
            h4 = 0.05 * np.sin(2 * np.pi * (freq * 4) * c_t)
            sub = 0.20 * np.sin(2 * np.pi * (freq * 0.5) * c_t)
            tone = h1 + h2 + h3 + h4 + sub

            # Slow organic marimba tremolo
            tremolo = 1.0 + 0.12 * np.sin(2 * np.pi * 3.5 * c_t)
            chord_sig += (tone * tremolo)

        chord_sig /= len(freqs)

        # Crossfade envelope
        fade_in_len = int(1.8 * sr)
        fade_out_len = int(2.2 * sr)
        env = np.ones(c_len, dtype=np.float32)
        if c_len > fade_in_len:
            env[:fade_in_len] = np.linspace(0, 1, fade_in_len)
        if c_len > fade_out_len:
            env[-fade_out_len:] = np.linspace(1, 0, fade_out_len)

        bed[c_start_idx:c_end_idx] += chord_sig * env

    # Normalize to -24 dBFS
    max_val = np.max(np.abs(bed))
    if max_val > 0:
        bed = (bed / max_val) * 0.12
    return bed

def generate_foley_track(duration_sec: float, sr: int) -> np.ndarray:
    """
    Synthesizes tactile culinary micro-sounds placed along the timeline.
    """
    total_samples = int(duration_sec * sr)
    foley = np.zeros(total_samples, dtype=np.float32)

    def add_sound(sound: np.ndarray, time_sec: float, gain: float = 1.0):
        start_idx = int(time_sec * sr)
        end_idx = min(start_idx + len(sound), total_samples)
        sound_len = end_idx - start_idx
        if sound_len > 0:
            foley[start_idx:end_idx] += sound[:sound_len] * gain

    # 1. Mortar & pestle crack
    def mortar_crack():
        dur = 0.18
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        noise = np.random.uniform(-1, 1, n)
        thud = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 28)
        crack = noise * np.exp(-t * 45)
        return (thud * 0.6 + crack * 0.4).astype(np.float32)

    # 2. Essential oil droplet chime
    def oil_chime():
        dur = 0.45
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        tone = (np.sin(2 * np.pi * 1320 * t) + 0.5 * np.sin(2 * np.pi * 1760 * t)) * np.exp(-t * 12)
        return tone.astype(np.float32)

    # 3. Water simmer bubbling
    def water_bubble():
        dur = 1.2
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        w = np.sin(2 * np.pi * (320 + 80 * np.sin(2 * np.pi * 6 * t)) * t) * np.exp(-t * 3.5)
        return w.astype(np.float32)

    # 4. Milk pour cascade
    def milk_pour():
        dur = 1.5
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        noise = np.random.normal(0, 0.3, n)
        env = np.sin(np.pi * t / dur)
        return (noise * env * 0.5).astype(np.float32)

    # 5. Casein binding shield click
    def casein_shield():
        dur = 0.25
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        return (np.sin(2 * np.pi * 880 * t) * np.exp(-t * 22)).astype(np.float32)

    # 6. Foam rise simmer
    def foam_simmer():
        dur = 2.0
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        b = np.sin(2 * np.pi * (240 + 120 * np.sin(2 * np.pi * 4 * t)) * t) * (1 - np.exp(-t * 2)) * np.exp(-t * 1.5)
        return b.astype(np.float32)

    # 7. Terracotta kulhad clink
    def kulhad_clink():
        dur = 0.35
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        c = (np.sin(2 * np.pi * 1046 * t) + 0.4 * np.sin(2 * np.pi * 2093 * t)) * np.exp(-t * 18)
        return c.astype(np.float32)

    # Add cues mapped to measured timestamps:
    # Scene 1: 0.0 - 15.3s (Crush spices)
    add_sound(mortar_crack(), 3.8, 0.7)
    add_sound(mortar_crack(), 4.6, 0.6)
    add_sound(oil_chime(), 7.2, 0.4)
    add_sound(oil_chime(), 11.2, 0.4)

    # Scene 2: 15.8 - 27.65s (Water decoction)
    add_sound(water_bubble(), 16.5, 0.4)
    add_sound(water_bubble(), 21.0, 0.35)

    # Scene 3: 28.15 - 41.75s (Milk & Casein shield)
    add_sound(milk_pour(), 28.5, 0.5)
    add_sound(casein_shield(), 33.5, 0.4)
    add_sound(casein_shield(), 37.0, 0.4)

    # Scene 4: 42.25 - 54.25s (Double boil & Pour)
    add_sound(foam_simmer(), 43.0, 0.45)
    add_sound(foam_simmer(), 47.5, 0.45)
    add_sound(kulhad_clink(), 50.8, 0.6)

    # Normalize
    max_val = np.max(np.abs(foley))
    if max_val > 0:
        foley = (foley / max_val) * 0.22
    return foley

def main():
    np.random.seed(42) # Deterministic PRNG
    print("Generating warm culinary BGM bed...")
    bgm = generate_warm_culinary_bgm(TOTAL_DURATION, TARGET_SR)
    sf.write(str(AUDIO_DIR / "bgm.wav"), bgm, TARGET_SR, subtype="PCM_16")
    print(f"Wrote {AUDIO_DIR / 'bgm.wav'} ({TOTAL_DURATION}s)")

    print("Generating tactile culinary foley track...")
    sfx = generate_foley_track(TOTAL_DURATION, TARGET_SR)
    sf.write(str(AUDIO_DIR / "sfx-track.wav"), sfx, TARGET_SR, subtype="PCM_16")
    print(f"Wrote {AUDIO_DIR / 'sfx-track.wav'} ({TOTAL_DURATION}s)")

if __name__ == "__main__":
    main()

