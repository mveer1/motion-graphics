#!/usr/bin/env /opt/homebrew/opt/python@3.12/bin/python3.12
"""
synth-and-measure.py — Voice Director Speech Synthesizer & Timing Measurement.

Powered by kokoro-smart-tts-skill:
- Automatically normalizes numbers, currencies ($2.4T), multipliers (3x), percentages.
- Supports multi-voice blending (e.g. 'am_michael:0.7,am_adam:0.3').
- Inserts calibrated acoustic breath pauses to prevent robotic run-ons.
- Outputs exact duration and cadence metrics in JSON for GSAP timeline synchronization.

Usage:
  python3.12 synth-and-measure.py --text "Your text" --out clip.wav [--voice am_adam] [--speed 1.0] [--preset technical-explainer] [--raw]
"""
import argparse
import json
import os
import sys
import traceback
import wave
from pathlib import Path

import numpy as np

# Locate kokoro-smart-tts-skill scripts
SMART_SKILL_SCRIPTS = Path(__file__).resolve().parents[2] / "kokoro-smart-tts-skill" / "scripts"


def run(
    text: str,
    out_path: str,
    voice: str = "am_adam",
    speed: float = 0.95,
    lang: str = "a",
    preset: str = "technical-explainer",
    smart: bool = True
):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
    try:
        if smart and SMART_SKILL_SCRIPTS.exists():
            if str(SMART_SKILL_SCRIPTS) not in sys.path:
                sys.path.insert(0, str(SMART_SKILL_SCRIPTS))
            from smart_synth import synthesize_smart

            res = synthesize_smart(
                text=text,
                out_path=out_path,
                preset=preset,
                voice=voice,
                speed=speed,
                lang=lang,
                raw_baseline=False
            )

            # Return exact expected JSON schema for voice-director
            print(json.dumps({
                "ok": True,
                "path": out_path,
                "chars": len(text),
                "words": res["word_count"],
                "duration_seconds": res["duration_sec"],
                "cadence_wps": res["cadence_wps"],
                "sample_rate": 24000,
                "voice": res["voice"],
                "speed": res["speed"],
                "preset": res["preset"]
            }, indent=2))
            return

        # Fallback raw synthesis
        from kokoro import KPipeline
        pipe = KPipeline(lang_code=lang)
        chunks = []

        for res in pipe(text, voice=voice, speed=speed):
            chunks.append(res.audio.numpy())

        if not chunks:
            print(json.dumps({"ok": False, "error": "No audio produced"}), file=sys.stderr)
            sys.exit(1)

        combined = np.concatenate(chunks)
        pcm = np.int16(np.clip(combined * 32767.0, -32768, 32767))

        with wave.open(out_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm.tobytes())

        dur = len(pcm) / 24000.0
        print(json.dumps({
            "ok": True,
            "path": out_path,
            "chars": len(text),
            "duration_seconds": round(dur, 3),
            "sample_rate": 24000,
            "voice": voice,
            "speed": speed
        }, indent=2))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Voice Director Kokoro Synthesis with Smart Prosody")
    p.add_argument("--text", required=True, help="Text to synthesize")
    p.add_argument("--out", required=True, help="Output WAV path")
    p.add_argument("--voice", default="am_adam", help="Voice ID or blend (e.g. 'am_michael:0.7,am_adam:0.3')")
    p.add_argument("--speed", type=float, default=0.95, help="Speed multiplier")
    p.add_argument("--lang", default="a", help="Language code (a=en-us, b=en-gb)")
    p.add_argument("--preset", default="technical-explainer",
                   help="Prosody preset (conversational, documentary, storytelling, energetic, technical-explainer)")
    p.add_argument("--raw", action="store_true", help="Disable smart preprocessing and use raw synthesis")
    args = p.parse_args()
    run(args.text, args.out, args.voice, args.speed, args.lang, preset=args.preset, smart=not args.raw)
