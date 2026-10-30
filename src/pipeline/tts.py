#!/usr/bin/env /opt/homebrew/opt/python@3.12/bin/python3.12
"""
Kokoro TTS wrapper — compatible with kokoro 0.9.x generator API.
Yields KPipeline.Result chunks; we concatenate all .audio tensors.
Usage:
  python3.12 tts.py --text "Hello." --out out.wav [--voice am_adam] [--speed 1.0] [--lang a]
"""
import argparse, os, sys, wave, json, traceback
import numpy as np


def synth(text: str, out_path: str, voice: str = "am_adam", speed: float = 1.0, lang: str = "a"):
    from kokoro import KPipeline

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
    try:
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
        print(json.dumps({"out": out_path, "chars": len(text),
                          "samples": len(pcm), "duration_s": round(duration, 3), "ok": True}))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Kokoro TTS -> wav (kokoro 0.9.x)")
    ap.add_argument("--text",  required=True)
    ap.add_argument("--out",   required=True)
    ap.add_argument("--voice", default="am_adam")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--lang",  default="a")
    a = ap.parse_args()
    synth(a.text, a.out, a.voice, a.speed, a.lang)
