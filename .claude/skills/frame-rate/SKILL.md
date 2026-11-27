---
name: frame-rate
description: Lift a 30 fps film to 60 fps or higher (90, 120) and make its motion smoother. Use when asked for 60 fps, 120 fps, a higher frame rate, smoother or more fluid motion, frame interpolation, judder or stutter on drifts and pans, strobing on fast moves, motion blur, or "convert this film to 60". Picks the path (a studio project is re-rendered natively; any other finished film is interpolated per gap from evidence measured on the film itself), audits authored motion for what still strobes at the new rate, and verifies the result. Tool scripts/frame-rate.py.
version: 0.1.0
---

# Frame rate: 30 to 60 fps and higher

A 30 fps film shows one picture every 33 ms. Going to 60 fps means filling every gap with a new picture. **Where the pictures come from decides the quality**, so choose the path first.

| The film | Path | Why |
| --- | --- | --- |
| A studio project (`project.json`, a GSAP timeline in `src/index.html`) | **native**: set `fps: 60` and render again | HyperFrames samples the timeline at any rate, so every new frame is real. No interpolation artefacts are possible. |
| A finished file with no re-renderable source (legacy explainer, archived render, a plate on a host without Blender, an external clip) | **convert**: measured interpolation | The only option. The tool picks a method per gap and records why. |
| A target above 60 (90, 120) | native 60, then `convert` 60 → 120 | Studio projects render at 24, 25, 30 or 60 (`specs/video-spec.json`). Lifting 60 to 120 halves every gap. YouTube, Instagram and TikTok deliver at most 60. |

Never deliver an interpolated studio film when a native render is possible. Interpolation is the fallback, not the upgrade.

## Native path (studio projects)

1. `python scripts/frame-rate.py audit <slug> [--fps 60]` writes `qa/frame-rate/audit-60fps.json` and reports:
   - **video layers still at 30 fps** (Blender plates, ingested clips). Each of their frames would show twice, which is judder inside the layer. Plates re-render at the project rate because their stamp holds the fps: `visual-director.py render <slug>` on a host with Blender.
   - **authored moves that still strobe at 60**: peak travel per frame from `qa/motion/tweens.json`, using the real GSAP ease derivative. Refresh that file with `studio.py script <slug> --probe` (browser, render lock).
   - **short linear moves** (a velocity jump at both ends), **stepped motion** (stays stepped: it is time-based and that is the look), **fps lookups** in the composition, and whether page motion blur is on.
2. Fix the leads in the composition (see [references/smooth-motion.md](references/smooth-motion.md)). Never fix them in `_studio/`.
3. `python scripts/frame-rate.py audit <slug> --apply` sets `project.json` `fps` and regenerates the entry files (`studio.py formats`).
4. Gate as usual: `studio.py validate <slug>`, then `frame-review.py <slug> --fonts google`. Then, on the render host only, `studio.py build <slug>`. The fingerprint includes the fps, so the old renders move to `renders/history/` on their own. Twice the frames means about twice the capture time. That is fine: render time is not a constraint.

## Convert path (any finished film)

```bash
python scripts/frame-rate.py doctor                                  # ffmpeg + minterpolate present?
python scripts/frame-rate.py analyse <film.mp4|slug> --fps 60        # probe + plan (analysis lock)
python scripts/frame-rate.py convert <film.mp4|slug> --fps 60        # follows the plan (render lock), then verifies
python scripts/frame-rate.py sheet <film-60fps.mp4> --plan <plan>    # LOOK at the review moments
python scripts/frame-rate.py verify <film-60fps.mp4> --source <film.mp4>
```

A slug resolves to the project's current `renders/<fmt>/final.mp4` (else `out/<slug>-<fmt>.mp4`, else the newest archived render). Its output goes to `renders/<fmt>/hfr/final-60fps.mp4`, with the plan in `qa/frame-rate/`. A file input writes next to itself. Nothing overwrites `out/`: copy the file there yourself, and only after looking at the sheet.

### How each gap is filled

Every pair of source frames gets one method, chosen from the **leave-one-out probe**. The probe drops every other frame of this film, rebuilds each dropped frame with every method, and scores each rebuild against the real frame (mean error plus a quarter of the worst-block error, because tears are local).

| Kind (label) | Method | Rule |
| --- | --- | --- |
| hold (pair changes ≤ 0.02 of 255) | copy | identical frames; anything else adds noise |
| cut (isolated change, structure breaks) | copy | never mix two shots; a flash frame is two cuts |
| stepped (one change, short hold, at least 3 times in 1 s) | copy | on twos, boil and flicker are a chosen look |
| dissolve or fade (blend explains ≥ 75% of the change) | blend | exact for a linear mix; no motion to compensate |
| motion | blend, or mci when it beats blend by 10% | smoothed over 5 pairs so the method does not flicker |
| motion where repetition predicts best | copy, when it beats both by 10% | flicker, boil over drift, effectively 15 fps layers |

`--method blend|mci|copy` forces one method on measured pairs (holds, cuts and stepped stay copied). `--fast` skips the MCI probe, leaving only blend and copy. Evidence, calibration and limits: [references/gap-filling.md](references/gap-filling.md).

### Look before you deliver

`verify` checks the frame count, duration, audio and size, and measures **distinct frames per second**. A duplicate-padded "60 fps" film reads about 30. In `sheet`, look for:

- **mci frames:** blocks breaking up on edges, and text or thin lines warping.
- **blend frames:** a visible double image on large, high-contrast moves.

If MCI tears, run `convert --method blend` (a ghost for 16 ms is milder than a tear). The plan cannot override one stretch at a time yet.

## Rules

- One heavy job at a time: the probe takes the analysis lock and conversion the render lock, by themselves. Never wrap them in a second lock, and never run two at once.
- Keep the source rate family: 29.97 → 59.94 (`--exact` keeps a literal 60).
- Audio is copied untouched. Duration is identical to the frame.
- Not supported: alpha (WebM VP9 alpha plates come out opaque), HDR or 10-bit (output is 8-bit yuv420p), odd frame sizes. A VFR input is made constant at its average rate first.
- Status is experimental. The thresholds are starting values calibrated on four films and a synthetic ground-truth scene, all on Windows. Say so when you report a conversion, and name the review moments you looked at.
