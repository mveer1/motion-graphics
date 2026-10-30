# Motion Lab: Architecture & Technical Pipeline

> A reproducible, low-memory production pipeline for technical & scientific explainer videos on Apple Silicon macOS.

---

## 1. System Design

```
                     ┌──────────────────────────┐
                     │    narration.json        │
                     │  (Text script per scene) │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │   Kokoro TTS (PyTorch)   │
                     │ (24kHz Mono WAV per scene)│
                     └────────────┬─────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       ┌─────────────────────┐         ┌─────────────────────┐
       │   audio/scene-N.wav │         │  Audio Duration     │
       │   Exact time stamps │         │  Measurement        │
       └──────────┬──────────┘         └──────────┬──────────┘
                  │                               │
                  │                               ▼
                  │                    ┌─────────────────────┐
                  │                    │  HyperFrames Compo  │
                  │                    │ (HTML / SVG / GSAP) │
                  │                    │ Paused timeline     │
                  │                    └──────────┬──────────┘
                  │                               │
                  │                               ▼
                  │                    ┌─────────────────────┐
                  │                    │ HyperFrames Render  │
                  │                    │ (Headless Chrome)   │
                  │                    │ H.264 MP4 Visuals   │
                  │                    └──────────┬──────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │          FFmpeg          │
                     │ Direct Muxing & Assembly │
                     │  (-c:v copy -c:a aac)    │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │   Final Explainer Video  │
                     │   1280x720 / 30fps MP4   │
                     └──────────────────────────┘
```

---

## 2. Core Subsystems

### A. Narration & Speech Synthesis
- **Engine:** Kokoro TTS v0.9.4 (`hexgrad/Kokoro-82M`)
- **Language / Voice:** American English (`lang="a"`, voice `am_adam`)
- **Phonemizer:** `misaki` with `en_core_web_sm` model
- **Output Spec:** 24,000 Hz, 16-bit PCM Mono WAV
- **Pacing Buffer:** 0.5s silence gap (`pause.wav`) inserted between scene cuts to preserve speech naturalness without truncation.

### B. Visuals & Motion Graphics
- **Engine:** HyperFrames CLI v0.8.216 (`hyperframes render`)
- **Backend:** Headless Chromium + ANGLE Metal hardware GPU rendering
- **Animation Framework:** GSAP 3 with paused timelines synced to explicit timeline timestamps (`window.__timelines['root']`)
- **Design Paradigm:**
  - Dark background (`#080c14`)
  - Semantic color palette (Input `#58a6ff`, Processing `#e3b341`, Target `#3fb950`, Loss `#f85149`)
  - Procedural SVGs for mathematical diagrams, neural networks, and curves
  - Deterministic rendering (seeded PRNG instead of `Math.random()`)

### C. Audio-Video Assembly
- **Engine:** FFmpeg 9.0.2 (Apple Silicon native)
- **Assembly Strategy:** Decoupled rendering with single-pass stream copy (`-c:v copy -c:a aac`)
- **Speed:** Video render takes ~25s; audio muxing takes <0.3s.

---

## 3. Hardware & Memory Constraints (8 GB RAM)

1. **Sequential Execution:** Never execute multiple renders or model synthesis concurrently.
2. **Low-Memory Profile:** HyperFrames is invoked with `--low-memory-mode`, pinning capture to 1 worker and screenshot mode to prevent memory pressure spikes.
3. **Draft vs Delivery:** 720p/30fps during development; 1080p for final export.

