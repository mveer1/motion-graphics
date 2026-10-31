#!/usr/bin/env python3
"""
generate_bed_and_sfx.py
Synthesizes:
1. A dim, warm, hypnotic ambient documentary music bed (minor key synth pad).
2. Subtle, quiet micro-cues (tactile clicks, soft thuds, gentle chimes - ZERO WHOOSHES).
3. Mixes them into projects/china-market-crash-2026/audio/sfx-track.wav at 24kHz mono.
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
TOTAL_DURATION = 43.08
TOTAL_SAMPLES = int(TOTAL_DURATION * TARGET_SR)

def generate_ambient_music_bed(duration_sec: float, sr: int) -> np.ndarray:
    """
    Generates a gentle, cinematic ambient documentary music bed.
    Chord progression: Dm -> Fmaj -> Gm -> Am (repeating slowly with slow crossfades).
    Warm harmonic synth pad with soft lowpass filtering and subtle tremolo.
    """
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    bed = np.zeros(total_samples, dtype=np.float32)

    # Chords (frequencies in Hz)
    # Dm: D3 (146.83), F3 (174.61), A3 (220.00), D4 (293.66)
    # F:  F3 (174.61), A3 (220.00), C4 (261.63), F4 (349.23)
    # Gm: G3 (196.00), Bb3 (233.08), D4 (293.66), G4 (392.00)
    # Am: A3 (220.00), C4 (261.63), E4 (329.63), A4 (440.00)
    chord_duration = 10.77  # 4 chords over ~43s
    chords = [
        [146.83, 174.61, 220.00, 293.66],
        [174.61, 220.00, 261.63, 349.23],
        [196.00, 233.08, 293.66, 392.00],
        [220.00, 261.63, 329.63, 440.00]
    ]

    for chord_idx, freqs in enumerate(chords):
        chord_start = chord_idx * chord_duration
        chord_end = min((chord_idx + 1) * chord_duration + 2.0, duration_sec) # 2s crossfade
        c_start_idx = int(chord_start * sr)
        c_end_idx = int(chord_end * sr)
        c_len = c_end_idx - c_start_idx
        if c_len <= 0:
            continue

        c_t = np.linspace(0, chord_end - chord_start, c_len, endpoint=False)
        chord_sig = np.zeros(c_len, dtype=np.float32)

        for freq in freqs:
            # Fundamental + soft second harmonic + detuned choir
            tone = (
                0.60 * np.sin(2 * np.pi * freq * c_t) +
                0.25 * np.sin(2 * np.pi * (freq * 1.002) * c_t) +
                0.20 * np.sin(2 * np.pi * (freq * 0.998) * c_t) +
                0.15 * np.sin(2 * np.pi * (freq * 2.0) * c_t)
            )
            chord_sig += tone

        # Envelope: smooth 1.5s attack, sustain, 2.0s release
        attack_len = int(1.5 * sr)
        release_len = int(2.0 * sr)
        env = np.ones(c_len, dtype=np.float32)
        if c_len > attack_len:
            env[:attack_len] = np.linspace(0, 1, attack_len)
        if c_len > release_len:
            env[-release_len:] = np.linspace(1, 0, release_len)

        # Slow hypnotic breathing modulation (0.25 Hz)
        lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * c_t)
        chord_sig = chord_sig * env * lfo

        bed[c_start_idx:c_end_idx] += chord_sig

    # Gentle sub-bass pulse on 73.4 Hz (D2)
    sub = 0.35 * np.sin(2 * np.pi * 73.416 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.2 * t))
    bed += sub

    # Global fade in (1.0s) and fade out (2.0s)
    fade_in = int(1.0 * sr)
    fade_out = int(2.0 * sr)
    bed[:fade_in] *= np.linspace(0, 1, fade_in)
    bed[-fade_out:] *= np.linspace(1, 0, fade_out)

    # Normalize to a dim, background level: target around -24 dBFS peak (0.06 linear)
    bed_peak = np.max(np.abs(bed))
    if bed_peak > 0:
        bed = bed / bed_peak * 0.08  # Soft, dim level (about -22 dBFS)

    return bed

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
    print(f"🎵 Synthesizing dim background music bed & subtle foley cues ({TOTAL_DURATION}s @ {TARGET_SR}Hz)...")
    
    # 1. Generate ambient music bed
    music_bed = generate_ambient_music_bed(TOTAL_DURATION, TARGET_SR)

    # 2. Add subtle, tactile micro-cues (NO TRANSITION WHOOSHES!)
    # (cue_id, timestamp_sec, gain_linear)
    MICRO_CUES = [
        ("cut_hit/sub", 4.2, 0.22),           # Gentle low thump when -20% threshold crossed
        ("toggle/micro", 15.0, 0.20),         # Subtle tactile click when margin trigger flips
        ("typing_key/light", 22.0, 0.14),     # Gentle keyboard tap 1
        ("typing_key/light", 22.5, 0.14),     # Gentle keyboard tap 2
        ("typing_key/light", 23.0, 0.14),     # Gentle keyboard tap 3
        ("fit/bell/small_bell", 38.0, 0.20),  # Very soft gentle chime at resolution
    ]

    sfx_layer = np.zeros(TOTAL_SAMPLES, dtype=np.float32)
    for sound_id, start_sec, gain in MICRO_CUES:
        safe_name = sound_id.replace("/", "_") + ".wav"
        raw_path = SFX_RAW / safe_name
        render_cue(sound_id, raw_path)
        samples = read_resample_wav(raw_path, TARGET_SR) * gain

        start_idx = int(start_sec * TARGET_SR)
        end_idx = min(start_idx + len(samples), TOTAL_SAMPLES)
        length_to_add = end_idx - start_idx
        if length_to_add > 0:
            sfx_layer[start_idx:end_idx] += samples[:length_to_add]
            print(f"  • Placed subtle cue '{sound_id}' at {start_sec:05.2f}s (gain: {gain:.2f})")

    # Combine dim ambient music bed + subtle micro cues
    master_track = music_bed + sfx_layer

    # Prevent clipping
    peak = np.max(np.abs(master_track))
    if peak > 0.85:
        master_track = master_track * (0.85 / peak)

    pcm_out = np.int16(np.clip(master_track * 32767.0, -32768, 32767))
    out_file = AUDIO_DIR / "sfx-track.wav"
    with wave.open(str(out_file), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_SR)
        w.writeframes(pcm_out.tobytes())

    print(f"✅ Generated master background & SFX track: {out_file} ({len(pcm_out)/TARGET_SR:.2f}s)")

if __name__ == "__main__":
    main()

