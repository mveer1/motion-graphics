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

### Audio findings from the three newest films (2026-11-03)

Measured on `out/*-portrait.mp4` with ffmpeg `ebur128` and `earshot critique --fast`. Not listened to.

| Film | ffmpeg LUFS | earshot LUFS | Final moment vs body | Earshot verdict |
|---|---|---|---|---|
| cloud-physical-infrastructure-india | −16.8 | −13.8 | −19.1 LU (major) | close |
| fridge-hack-europe | −16.9 | −13.9 | −4.2 LU (major) | close |
| south-korea-data-center-fire | −17.0 | −14.0 | −0.2 LU (ok) | launch-grade |

- **Loudness numbers differ by 3.0 LU between the two meters.** The mixes are mono AAC (`ffprobe`: 1 channel). The ffmpeg gate counts one channel; earshot's web range (−16 to −9 LUFS) compares like stereo. A mono file played from both phone speakers measures about 3 LU louder than the gate says, which matches the gap. This is an inference; confirm by measuring a stereo downmix. Keep the −16 ± 2 gate on ffmpeg and do not mix the two numbers in one report.
- **Land the ending.** Korea ends with a thud at 95.7 s on a bed that is still present and a 2.0 s ring-out. Cloud's last sound is a quiet chime (gain 0.35) at 64.2 s and its bed `level` envelope ramps from 0.45 at 66 s to 0 at 70 s (earshot measured a 3.1 s fade-out), so the last moment is 19 LU under the body, with about 4.5 s of near-silence after the narration. Fridge's last visual event (86.0 s) lands 4.2 LU under the body; its closing thud (89.7 s) and the returning hum come after it. Rule: put the heaviest soft landing (low thud plus a short ring) on the last visual event, do not ramp the bed to zero over the last 4 s (hold it, then cut or ring out), and keep the tail after the last word to 2–3 s.
- **Cues that have no sound.** Cloud: 5 of 47 visual events had no onset within 100 ms (3.7, 23.1, 32.1, 57.2, 60.3 s). Generate the SFX cue list from the composition's event times, not by hand against the storyboard.
- **Levels, for reference.** All three use the same normalisation: SFX peak 0.16 (measured −15.6 to −15.9 dBFS, about 13 dB under the voice peak) and bed about 15 dB under the voice loudness before the mux. Earshot raised no level or balance issue on any of them (its findings were the ending, mono, mids and, on cloud, sub-bass). Keep it.
- **Optional, minor, all three:** mono mix (earshot suggests stereo bed with panned SFX); 1–3 kHz "honky" share on cloud and fridge (−8.6 dB against a −10.5 dB limit), which a 2 dB cut on the loudest layer would fix.
- **Tail length.** Final MP4 is 2.4–3.9 s longer than the narration in each film (70 vs 66.15 s, 98 vs 94.98 s, 92 vs 89.6 s). Treat that as the designed outro, and give it motion and a sound (see above).
