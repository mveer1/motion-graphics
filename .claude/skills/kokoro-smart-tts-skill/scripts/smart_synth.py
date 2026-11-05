#!/usr/bin/env /opt/homebrew/opt/python@3.12/bin/python3.12
"""
smart_synth.py — Production Smart Synthesizer for Kokoro TTS.

Combines:
1. Intelligent text preprocessing (preprocessor.py).
2. Persona selection and multi-voice tensor blending (voice_advisor.py).
3. Context-aware acoustic breath pause insertion.
4. Smooth anti-pop crossfading and digital peak limiting.
5. Exact millisecond timeline marker generation for animation sync.

Usage:
  python3.12 smart_synth.py --text "Your text" --out out.wav --preset documentary
  python3.12 smart_synth.py --text "Your text" --out out.wav --voice "am_michael:0.7,am_adam:0.3" --speed 1.05
"""

import argparse
import json
import math
import os
import sys
import wave
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
import torch

# Ensure local skill directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from preprocessor import preprocess_for_kokoro
from voice_advisor import (
    SIGNATURE_RECIPES,
    parse_voice_weights,
    blend_voice_tensors,
    recommend_voice
)

# Preset definitions
PRESETS = {
    "conversational": {
        "voice": "af_bella:0.75,af_sarah:0.25",
        "speed": 1.03,
        "sentence_pause": 0.28,
        "clause_pause": 0.16,
        "paragraph_pause": 0.50,
        "lang": "a",
        "description": "Natural conversational cadence with warm empathy and analytical clarity."
    },
    "documentary": {
        "voice": "am_michael:0.70,am_adam:0.30",
        "speed": 0.96,
        "sentence_pause": 0.38,
        "clause_pause": 0.20,
        "paragraph_pause": 0.65,
        "lang": "a",
        "description": "Deliberate, cinematic resonance with technical precision. Suited for economics and crisis explainers."
    },
    "storytelling": {
        "voice": "bm_fable:0.65,bm_george:0.35",
        "speed": 0.98,
        "sentence_pause": 0.42,
        "clause_pause": 0.22,
        "paragraph_pause": 0.75,
        "lang": "b",
        "description": "Dramatic British enunciation with deep theatrical pauses and emotional tension."
    },
    "energetic": {
        "voice": "am_adam:0.65,am_echo:0.35",
        "speed": 1.15,
        "sentence_pause": 0.20,
        "clause_pause": 0.12,
        "paragraph_pause": 0.40,
        "lang": "a",
        "description": "High-velocity punchy delivery with tight pauses for short-form mobile reels."
    },
    "technical-explainer": {
        "voice": "am_adam:0.80,am_michael:0.20",
        "speed": 1.12,
        "sentence_pause": 0.30,
        "clause_pause": 0.18,
        "paragraph_pause": 0.50,
        "lang": "a",
        "description": "Workspace standard for motion graphics diagrams and systems architecture."
    }
}


def apply_edge_fades(audio: np.ndarray, sr: int = 24000, fade_ms: float = 4.0) -> np.ndarray:
    """Apply micro fade-in and fade-out to prevent zero-crossing clicks."""
    fade_len = int(sr * (fade_ms / 1000.0))
    if len(audio) < 2 * fade_len:
        return audio
    faded = audio.copy()
    in_ramp = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
    out_ramp = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
    faded[:fade_len] *= in_ramp
    faded[-fade_len:] *= out_ramp
    return faded


def synthesize_smart(
    text: str,
    out_path: str,
    preset: str = "conversational",
    voice: Optional[str] = None,
    speed: Optional[float] = None,
    sentence_pause: Optional[float] = None,
    lang: Optional[str] = None,
    custom_phonetics: Optional[Dict[str, str]] = None,
    raw_baseline: bool = False,
    pipe: Any = None
) -> Dict[str, Any]:
    """
    Synthesize audio using Kokoro with intelligent preprocessing and voice blending.

    Pass `pipe` (a KPipeline for the same language) to reuse a loaded model across calls.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)

    preset_cfg = PRESETS.get(preset, PRESETS["conversational"])
    active_voice_spec = voice or preset_cfg["voice"]
    active_speed = speed if speed is not None else preset_cfg["speed"]
    active_sent_pause = sentence_pause if sentence_pause is not None else preset_cfg["sentence_pause"]
    active_clause_pause = preset_cfg["clause_pause"]
    active_lang = lang or preset_cfg["lang"]

    if pipe is None:
        from kokoro import KPipeline
        pipe = KPipeline(lang_code=active_lang)

    # 1. Resolve Voice / Blend
    voice_weights = parse_voice_weights(active_voice_spec)
    blended_voice = blend_voice_tensors(pipe, voice_weights)

    sample_rate = 24000
    assembled_pcm = []
    timeline_markers = []
    current_time_sec = 0.0

    if raw_baseline:
        # Baseline raw synthesis without preprocessing
        raw_chunks = []
        for res in pipe(text, voice=blended_voice, speed=active_speed):
            raw_chunks.append(res.audio.numpy())
        if not raw_chunks:
            raise RuntimeError("Baseline Kokoro pipeline produced no audio.")
        combined_raw = np.concatenate(raw_chunks)
        assembled_pcm.append(combined_raw)
        total_duration = len(combined_raw) / float(sample_rate)
        timeline_markers.append({
            "text": text,
            "start_time_sec": 0.0,
            "end_time_sec": round(total_duration, 3),
            "type": "raw_full"
        })
    else:
        # Smart synthesis with preprocessing and breath groups
        norm_text, segments = preprocess_for_kokoro(
            text,
            preset=preset,
            custom_phonetics=custom_phonetics
        )

        for seg_idx, seg in enumerate(segments):
            seg_text = seg["text"].strip()
            if not seg_text:
                continue

            # Synthesize segment
            seg_chunks = []
            for res in pipe(seg_text, voice=blended_voice, speed=active_speed):
                seg_chunks.append(res.audio.numpy())

            if not seg_chunks:
                continue

            seg_audio = np.concatenate(seg_chunks)
            seg_audio = apply_edge_fades(seg_audio, sr=sample_rate, fade_ms=4.0)

            seg_dur = len(seg_audio) / float(sample_rate)
            start_t = current_time_sec
            end_t = start_t + seg_dur

            assembled_pcm.append(seg_audio)
            timeline_markers.append({
                "segment_index": seg_idx,
                "text": seg_text,
                "type": seg["type"],
                "start_time_sec": round(start_t, 3),
                "end_time_sec": round(end_t, 3),
                "duration_sec": round(seg_dur, 3)
            })
            current_time_sec = end_t

            # Add context-aware acoustic pause
            pause_sec = seg["pause_after"]
            if seg["type"] == "sentence":
                pause_sec = active_sent_pause
            elif seg["type"] == "clause":
                pause_sec = active_clause_pause

            if pause_sec > 0 and seg_idx < len(segments) - 1:
                pause_samples = int(pause_sec * sample_rate)
                assembled_pcm.append(np.zeros(pause_samples, dtype=np.float32))
                current_time_sec += pause_sec

    # Combine all parts
    full_audio = np.concatenate(assembled_pcm) if assembled_pcm else np.zeros(0, dtype=np.float32)

    # Master: soft peak limiter at -1.0 dBFS (0.891)
    peak = np.max(np.abs(full_audio)) if len(full_audio) > 0 else 0.0
    if peak > 0.891:
        full_audio = full_audio / peak * 0.891

    # Convert to 16-bit PCM
    pcm_16 = np.int16(np.clip(full_audio * 32767.0, -32768, 32767))

    # Write WAV
    with wave.open(out_path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_16.tobytes())

    total_duration = len(pcm_16) / float(sample_rate)
    word_count = len(text.split())
    wps = round(word_count / total_duration, 2) if total_duration > 0 else 0.0

    result = {
        "ok": True,
        "out_path": out_path,
        "preset": preset,
        "voice": active_voice_spec,
        "speed": active_speed,
        "word_count": word_count,
        "duration_sec": round(total_duration, 3),
        "cadence_wps": wps,
        "peak_dbfs": round(20 * math.log10(peak) if peak > 0 else -100.0, 2),
        "markers": timeline_markers
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Smart Kokoro TTS Synthesizer")
    parser.add_argument("--text", help="Raw input text to synthesize")
    parser.add_argument("--text-file", help="Path to input text file")
    parser.add_argument("--out", required=True, help="Output WAV file path")
    parser.add_argument("--preset", default="conversational", choices=list(PRESETS.keys()),
                        help="Prosody preset (conversational, documentary, storytelling, energetic, technical-explainer)")
    parser.add_argument("--voice", help="Voice ID or blend formula (e.g. 'am_michael:0.7,am_adam:0.3')")
    parser.add_argument("--speed", type=float, help="Playback speed multiplier")
    parser.add_argument("--sentence-pause", type=float, help="Seconds of silence between sentences")
    parser.add_argument("--lang", default=None, help="Language code (a=en-us, b=en-gb)")
    parser.add_argument("--phonetics-json", help="Path to custom word-to-IPA dictionary")
    parser.add_argument("--raw-baseline", action="store_true", help="Synthesize without smart preprocessing (for testing)")
    parser.add_argument("--json-meta", help="Path to save detailed timing JSON metadata")

    args = parser.parse_args()

    input_text = args.text
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            input_text = f.read()

    if not input_text:
        print("Error: Provide --text or --text-file", file=sys.stderr)
        sys.exit(1)

    custom_phonetics = None
    if args.phonetics_json and os.path.exists(args.phonetics_json):
        with open(args.phonetics_json, "r", encoding="utf-8") as f:
            custom_phonetics = json.load(f)

    res = synthesize_smart(
        text=input_text,
        out_path=args.out,
        preset=args.preset,
        voice=args.voice,
        speed=args.speed,
        sentence_pause=args.sentence_pause,
        lang=args.lang,
        custom_phonetics=custom_phonetics,
        raw_baseline=args.raw_baseline
    )

    if args.json_meta:
        with open(args.json_meta, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
