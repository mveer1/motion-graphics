---
name: voice-director
description: Voice synthesis, narration pacing, audio measurement, and acoustic tuning using Kokoro TTS with integrated Smart Prosody and multi-voice blending.
---

# Voice Director Skill

This skill governs speech generation, voice persona selection, audio timing, and loudness mastering for educational explainers. It is now powered by the **Smart Prosody Engine** (`kokoro-smart-tts-skill`), eliminating robotic run-on sentences, mangled symbols, and flat single-voice artificiality.

---

## Quick References & Tools

- **Single-Step Synthesis Tool:** Use [`scripts/synth-and-measure.py`](./scripts/synth-and-measure.py) to generate speech with smart preprocessing and return exact duration and cadence JSON.
- **Master Pipeline Wrapper:** [`src/pipeline/tts.py`](file:///Users/mahavir/Downloads/Repo/motion graphics/src/pipeline/tts.py) (automatically applies smart preprocessing by default).
- **Voice Catalog & Blending Guide:** Read [`references/voices.md`](./references/voices.md) to pick single personas or signature blends (`am_michael:0.7,am_adam:0.3`, `af_bella:0.75,af_sarah:0.25`).
- **Phonetics Dictionary & IPA:** Check [`references/phonetics.md`](./references/phonetics.md) for technical pronunciation respellings and Markdown IPA syntax `[Word](/phonemes/)`.
- **Narration Schema:** See [`examples/narration-sample.json`](./examples/narration-sample.json) for multi-scene script structure.

---

## 1. Operating Instructions

1. **Invoke Smart Synthesis Wrapper:**
   Synthesize narration using `synth-and-measure.py` or `src/pipeline/tts.py`. Smart preprocessing is enabled by default to expand numbers/currencies, enhance punctuation, and insert breath pauses.
2. **Audio Specifications:**
   - Sample rate: 24,000 Hz
   - Format: 16-bit PCM Mono WAV
   - Default pacing: `speed: 1.12x–1.15x` (technical), `0.96x` (documentary), `1.03x` (conversational).
3. **Calibrated Prosody Presets:**
   - **`documentary`**: For finance crashes, crises, and historical thrillers (`am_michael:0.70,am_adam:0.30`).
   - **`conversational`**: For tutorials and approachable educational overviews (`af_bella:0.75,af_sarah:0.25`).
   - **`storytelling`**: For lore, narrative arcs, and audiobooks (`bm_fable:0.65,bm_george:0.35`).
   - **`energetic`**: For TikTok, 9:16 vertical reels, and YouTube Shorts (`am_adam:0.65,am_echo:0.35`).
   - **`technical-explainer`** *(Default)*: For systems, diagrams, and compiler explainers (`am_adam:0.80,am_michael:0.20`).
4. **Pacing Buffer:**
   Always concatenate a `0.5s` silence buffer (`pause.wav`) between scenes to prevent speech clipping across visual scene transitions.
5. **Duration First (GSAP Invariant):**
   **Never** hardcode GSAP animation keyframes before synthesizing and measuring narration clip durations via `synth-and-measure.py`.
6. **Conversational Simplification Rule (Reels / Shorts):**
   When targeting mobile reels (9:16), ground technical abstractions into human scenarios (e.g., *"borrowing 3x cash and getting wiped out by a margin call"* instead of *"systemic multi-tiered deleveraging cascade"*).
7. **Word Budgeting:**
   Always budget word counts to match target scene durations:
   - Deliberate documentary (`am_michael` / `documentary`): $\le 24$–$27$ words per 10-second scene.
   - Neutral technical (`am_adam` / `technical-explainer`): $\le 30$–$33$ words per 10-second scene.
   - High-energy reel (`energetic`): $\le 32$–$35$ words per 10-second scene.
