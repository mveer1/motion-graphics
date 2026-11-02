# HyperFrames Render Profiles on Apple Silicon (M2 / 8 GB RAM)

HyperFrames uses headless Chrome and FFmpeg under the hood. On Apple Silicon machines with 8 GB Unified Memory, choosing the right profile prevents out-of-memory errors and optimizes render speed.

---

## 1. Quality Presets

| Quality Preset | CRF / Profile | Target Use | Render Speed (30s composition) | Memory Footprint |
|---|---|---|---|---|
| `--quality draft` | CRF 28 / Fast | Rapid iteration, timing checks | ~15 – 20s | Low (<1.2 GB) |
| `--quality looks` | CRF 16 (Default) | Standard development review | ~25 – 35s | Medium (<1.5 GB) |
| `--quality delivery` | High bitrate | Final publication / master export | ~40 – 60s | Medium-High (<1.8 GB) |

---

## 2. Critical Flags for 8 GB RAM

- `--low-memory-mode`:
  **MANDATORY.** Pins Chrome worker instances to `1` and forces screenshot capture mode. Omitting this flag on 8 GB RAM can cause Chrome to spin up 4-8 parallel workers, exhausting swap space.
- `--fps 30`:
  Standard 30 fps produces smooth motion graphics with 50% fewer frames to capture than 60 fps.
- `--format mp4`:
  Standard H.264 MP4 output compatible with all editing tools and web players.

---

## 3. Two-Pass Assembly Strategy

Rather than having Chrome handle audio encoding during capture (which can lead to desynchronization on slow frames):
1. **Pass 1:** Render silent video track via HyperFrames (`renders/visuals.mp4`).
2. **Pass 2:** Multiplex high-fidelity AAC audio from the master WAV via FFmpeg stream copy (`-c:v copy -c:a aac -b:a 192k`).
   - Time elapsed for Pass 2: **< 0.3 seconds**.
   - Guarantee: Perfect, zero-drift synchronization.

