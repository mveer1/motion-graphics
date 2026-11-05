#!/usr/bin/env /opt/homebrew/opt/python@3.12/bin/python3.12
"""
Kokoro TTS wrapper — compatible with kokoro 0.9.x generator API.
Defaults to smart prosody preprocessing and multi-voice blending via kokoro-smart-tts-skill.
Fallbacks cleanly to raw Kokoro synthesis when --raw is specified.

Usage:
  python3.12 tts.py --text "Hello." --out out.wav [--voice am_adam] [--speed 1.0] [--lang a] [--preset technical-explainer] [--raw]
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
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SMART_SKILL_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "kokoro-smart-tts-skill" / "scripts"


def synth(
    text: str,
    out_path: str,
    voice: str = "am_adam",
    speed: float = 1.0,
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
            # Maintain backward-compatible JSON output contract
            print(json.dumps({
                "out": out_path,
                "chars": len(text),
                "duration_s": res["duration_sec"],
                "wps": res["cadence_wps"],
                "preset": res["preset"],
                "voice": res["voice"],
                "ok": True
            }))
            return

        # Fallback / Raw Mode
        from kokoro import KPipeline
        pipe = KPipeline(lang_code=lang)
        chunks = []

        # kokoro 0.9.x: __call__ returns a generator of KPipeline.Result
        for result in pipe(text, voice=voice, speed=speed):
            audio = result.audio          # torch.Tensor, float32, shape (N,)
            arr = audio.numpy()           # numpy float32
            chunks.append(arr)

        if not chunks:
            raise RuntimeError("KPipeline yielded no audio chunks")

        combined = np.concatenate(chunks)                              # float32
        pcm = np.int16(np.clip(combined * 32767.0, -32768, 32767))    # int16

        with wave.open(out_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm.tobytes())

        duration = len(pcm) / 24000.0
        print(json.dumps({
            "out": out_path,
            "chars": len(text),
            "samples": len(pcm),
            "duration_s": round(duration, 3),
            "ok": True
        }))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Kokoro TTS -> wav (with Smart Prosody & Multi-Voice support)")
    ap.add_argument("--text",   required=True, help="Text to synthesize")
    ap.add_argument("--out",    required=True, help="Output WAV path")
    ap.add_argument("--voice",  default="am_adam", help="Voice ID or blend formula (e.g. 'am_michael:0.7,am_adam:0.3')")
    ap.add_argument("--speed",  type=float, default=1.0, help="Speech speed multiplier")
    ap.add_argument("--lang",   default="a", help="Language code (a=en-us, b=en-gb)")
    ap.add_argument("--preset", default="technical-explainer",
                    help="Smart prosody preset (conversational, documentary, storytelling, energetic, technical-explainer)")
    ap.add_argument("--raw",    action="store_true", help="Disable smart preprocessing and use raw baseline synthesis")
    a = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pipeline.hostlock import heavy_lock  # Kokoro is a heavy job: one at a time on 8 GB, shared with renders

    with heavy_lock("tts"):
        synth(a.text, a.out, a.voice, a.speed, a.lang, preset=a.preset, smart=not a.raw)
