---
name: video-assembler
description: Render automation, memory management on Apple Silicon, FFmpeg stream multiplexing, and automated QA.
---

# Video Assembler Skill

This skill governs the compilation, encoding, and validation of motion graphics compositions.

## Quick References & Tools

- **Automated QA Script:** Run [`scripts/run-qa-gates.sh`](./scripts/run-qa-gates.sh) on any rendered MP4 to verify streams, loudness, and dark gaps.
- **Render Profiles & Memory:** Read [`references/render-profiles.md`](./references/render-profiles.md) for quality presets and Apple Silicon M2 flags.
- **Assembly Script:** Check [`examples/build-video.sh`](./examples/build-video.sh) for a reference 3-step pipeline.

---

## 1. Apple Silicon Memory Rules (8 GB RAM)

1. **Low-Memory Pinning:** Always pass `--low-memory-mode` to `hyperframes render`. This pins Chrome worker instances to 1 and forces screenshot capture mode.
2. **Never Parallelize Renders:** Running multiple headless Chrome rendering instances simultaneously on an 8 GB M2 host will trigger memory thrashing.
3. **Pre-flight Lint:** Always run `hyperframes lint index.html` before rendering to catch non-deterministic code, overlapping tweens, or missing DOM elements.

---

## 2. Render & Assembly Pipeline

```bash
# 1. Render Visual Track (Silent)
hyperframes render . \
  --fps 30 \
  --quality looks \
  --low-memory-mode \
  --output ../renders/visuals.mp4

# 2. Multiplex with Stream Copy (Sub-second assembly)
ffmpeg -y \
  -i ../renders/visuals.mp4 \
  -i ../audio/narration-full.wav \
  -c:v copy \
  -c:a aac -b:a 192k \
  -shortest \
  ../renders/final.mp4
```

---

## 3. Automated Quality Gate

Run automated checks on every build before declaring it complete:

- **EBU R128 Loudness:**
  `ffmpeg -i final.mp4 -af ebur128 -f null -` (Target: -21.2 LUFS ± 2 LU).
- **Black Gap Audit:**
  `ffmpeg -i final.mp4 -vf "blackdetect=d=0.3:pix_th=0.05" -f null -` (Ensure no accidental dark holds).
- **Stream Verification:**
  `ffprobe -v error -show_entries stream=codec_name,width,height,duration final.mp4`.
