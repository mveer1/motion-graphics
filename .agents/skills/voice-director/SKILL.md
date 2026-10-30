---
name: voice-director
description: Voice synthesis, narration pacing, audio measurement, and acoustic tuning using Kokoro TTS and FFmpeg.
---

# Voice Director Skill

This skill governs speech generation, voice persona selection, audio timing, and loudness mastering for educational explainers.

## Quick References & Tools

- **Single-Step Synthesis Tool:** Use [`scripts/synth-and-measure.py`](./scripts/synth-and-measure.py) to generate audio and return exact duration in JSON.
- **Voice Catalog:** Read [`references/voices.md`](./references/voices.md) to pick the best voice (`am_adam`, `af_bella`, `am_michael`, `af_sarah`, `bm_george`, `bf_emma`).
- **Phonetics Dictionary:** Check [`references/phonetics.md`](./references/phonetics.md) for technical pronunciation respellings (ReLU, epoch, LaTeX, SQL).
- **Narration Schema:** See [`examples/narration-sample.json`](./examples/narration-sample.json) for multi-scene script structure.

---

## 1. Operating Instructions

1. **Invoke Verified Wrapper:**
   Always use the Kokoro 0.9.x generator-compatible script at `src/pipeline/tts.py` (or `synth-and-measure.py`).
2. **Audio Specifications:**
   - Sample rate: 24,000 Hz
   - Format: 16-bit PCM Mono WAV
   - Default pacing: `speed: 0.95`
3. **Pacing Buffer:**
   Always concatenate a `0.5s` silence buffer (`pause.wav`) between scenes to ensure natural cadence and prevent speech clipping during transitions.
4. **Duration First:**
   Never write GSAP animation keyframes before synthesizing and measuring narration clip durations.
