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

1. **Low-Memory Pinning:** Always pass `--low-memory-mode` to `hyperframes render`. This pins Chrome worker instances to 1 and forces screenshot capture mode to avoid RAM exhaustion.
2. **Never Parallelize Renders:** Running multiple headless Chrome rendering instances simultaneously on an 8 GB M2 host will trigger memory thrashing.
3. **Render Time is NOT a Concern:** The low-memory mode safeguard is strictly about process concurrency and RAM stability. **Render duration (whether 30 seconds or 3 minutes) does NOT matter.** Agents must never reduce animation frequency, simplify timelines, or freeze visuals to make renders faster. The framework must not be lazy.
4. **Pre-flight Lint:** Always run `hyperframes lint index.html` before rendering to catch non-deterministic code, overlapping tweens, or missing DOM elements.

---

## 2. Render & Assembly Pipeline

```bash
# 1. Render Visual Track (Silent, Non-Interactive Stdin Redirect)
hyperframes render . \
  --fps 30 \
  --quality looks \
  --low-memory-mode \
  --output ../renders/visuals.mp4 < /dev/null

# 2. Multi-Track Multiplexing with Ducked SFX and Dim Themed Background Music Bed
# Inputs: 0:visuals.mp4, 1:narration-full.wav, 2:sfx-track.wav, 3:bgm.wav
ffmpeg -y \
  -i ../renders/visuals.mp4 \
  -i ../audio/narration-full.wav \
  -i ../audio/sfx-track.wav \
  -i ../audio/bgm.wav \
  -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[3:a]volume=0.25,afade=t=in:st=0:d=0.5,afade=t=out:st=28.5:d=1.5[a_bgm];[a_voice][a_sfx][a_bgm]amix=inputs=3:duration=first:dropout_transition=2[aout]" \
  -map 0:v -map "[aout]" \
  -c:v copy \
  -c:a aac -b:a 192k \
  -shortest \
  ../renders/final.mp4

# Fallback 2-Track Multiplexing (Narration + SFX only)
ffmpeg -y \
  -i ../renders/visuals.mp4 \
  -i ../audio/narration-full.wav \
  -i ../audio/sfx-track.wav \
  -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[a_voice][a_sfx]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
  -map 0:v -map "[aout]" \
  -c:v copy \
  -c:a aac -b:a 192k \
  -shortest \
  ../renders/final.mp4
```

---

## 3. Automated Quality Gate

Run automated checks on every build before declaring it complete:

- **EBU R128 Loudness:**
  `ffmpeg -i final.mp4 -af ebur128 -f null -` (Target: -21.2 LUFS ± 2 LU for legacy, -16 LUFS for studio projects).
- **Black Gap Audit:**
  `ffmpeg -i final.mp4 -vf "blackdetect=d=0.3:pix_th=0.05" -f null -` (Ensure no accidental dark holds).
- **Stream Verification:**
  `ffprobe -v error -show_entries stream=codec_name,width,height,duration final.mp4`.
