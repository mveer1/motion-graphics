#!/usr/bin/env /opt/homebrew/opt/python@3.12/bin/python3.12
"""
Helper script to synthesize speech and measure exact duration in one step.
Usage:
  python3.12 synth-and-measure.py --text "Your text" --out clip.wav [--voice am_adam] [--speed 0.95]
"""
import argparse, json, os, sys, wave
import numpy as np


def run(text: str, out_path: str, voice: str = "am_adam", speed: float = 0.95, lang: str = "a"):
    from kokoro import KPipeline

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
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


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice", default="am_adam")
    p.add_argument("--speed", type=float, default=0.95)
    p.add_argument("--lang", default="a")
    args = p.parse_args()
    run(args.text, args.out, args.voice, args.speed, args.lang)

