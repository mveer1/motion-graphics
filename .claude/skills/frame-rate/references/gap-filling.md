# Filling the gaps: evidence and calibration (convert path)

How `scripts/frame-rate.py` decides what goes between two source frames, the measurements behind each threshold, and the known limits. Every measurement was taken on 2026-11-25 on the Windows host (FFmpeg 9.0.2), not on the M2. Re-measure before you trust a threshold on a new kind of film.

## The three ways to make an in-between frame

| Method | What it does | Exact for | Fails as |
| --- | --- | --- | --- |
| copy | repeats frame *i* until frame *i+1* is due | holds, cuts, stepped motion | 30 fps judder on everything that moves |
| blend | `(1 - φ)·a + φ·b` on the YUV planes (φ = phase, 0.5 at 30 → 60) | dissolves, fades, sub-pixel drift | a faint double image on large moves (reads as a little blur) |
| mci | FFmpeg `minterpolate` (`mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none`): blocks moved along estimated vectors | rigid moves of textured content | tears and warps on non-rigid motion, transparency, particles, text over text |

Frames that land on a source time (every even output frame at 30 → 60) are always the source frame itself, never a resynthesised one.

## The probe: judge each method on the film itself

No method is right everywhere, so the planner tests them on this content. It drops every odd frame, rebuilds it from its neighbours with each method, and compares each rebuild with the real frame at 192 px (long side). MCI runs at 640 px. The reference frames go through the same 640 → 192 scaling, so no method is judged against a sharper truth.

- Score = mean |error| + 0.25 × the 98th-percentile 8×8-block error. A tear is local and the mean alone hides it.
- Scores are smoothed over 5 pairs inside a shot, so the method does not flicker frame to frame.
- MCI must beat blend by 10%, and copy must beat the best synthesis by 10%. A failed MCI frame looks worse than a ghost, and on a tie smoothness wins.
- The probe interpolates across twice the real gap (15 → 30 for a 30 fps film), so it is conservative about MCI.

## What the measurements showed

**1. minterpolate alignment.** Output frame *k* sits at *k*/target (an offset of 0 fits best: 0.37 error vs 0.85-0.91 at ±1 frame). It stops 2 frames short of the end (117 of 119 for a 60-frame clip at 30 → 60), so the last pair falls back to blend. Even its pass-through frames are not bit-exact (min PSNR 25.9 dB), which is why integer-phase frames come from the source.

**2. A biased probe is worse than none.** The first probe compared 360 px MCI output with a directly scaled reference. The rescale alone cost 0.366, exactly the "MCI error" on frames it did not interpolate, so MCI looked worse than blend. Lesson: score every method through the same pipeline.

**3. No single method wins** (corrected probe, mean held-out error on 0-255 luma, by how much the frame changes across the doubled gap):

| Change across the gap | sample-engine-mix: copy / blend / mci | pillar-of-fire: copy / blend / mci |
| --- | --- | --- |
| 0.5-2 | 0.51 / 0.38 / 0.38 | 0.46 / 0.38 / 0.38 |
| 2-5 | 1.11 / 0.63 / 0.61 | 1.20 / 1.08 / 0.97 |
| 5-12 | 3.80 / **0.78** / 0.99 | 3.93 / 2.88 / **2.19** |
| 12+ | 13.29 / **1.57** / 2.32 | 8.90 / 10.62 / **7.71** |
| copy wins outright | 15% of frames | 25-34% of frames (on-twos figures) |

`sample-engine-mix`'s large changes are dissolves, where blend is exact. `pillar-of-fire`'s are moving figures and lamps, where MCI wins. Its stepped puppets are why copy wins a quarter of the time there.

**4. Studio films have almost no holds.** In three films (720, 1,350 and 5,700 frames) no pair was bit-identical, and only 0.3-1.3% changed by 0.005 or less. 54-58% of pairs changed by 0.25 or less, but 70-80% of those kept moving over 10 frames: the continuous drift of the anti-laziness rule. A hold threshold of 0.25 would have copied about half the in-between frames on slow drifts and kept their judder. So `HOLD_EPS` is 0.02, and slow drift is blended (for a sub-pixel shift, a blend is almost exactly the shifted frame).

**5. Ground truth.** A 4 s synthetic scene was made at 60 fps: a hold, a textured slide at 150 px/s, a cut, a hold, a 1 s dissolve and a hold. It was decimated to 30 fps and lifted back. Mean error of the invented frames against the real 60 fps frames:

| Region | auto | copy | blend | mci |
| --- | --- | --- | --- | --- |
| slide | **0.220** | 0.952 | 0.979 | 0.220 |
| dissolve | **0.820** | 2.571 | 0.820 | 0.821 |
| holds | 0.013 | 0.013 | 0.013 | 0.013 |

The plan read the scene correctly: 1.97 s of holds (2.0 true), one cut at the right pair, the slide on MCI and the dissolve on blend. At 192×108 the probe briefly preferred MCI inside the dissolve. That led to the dissolve rule: when blend explains at least 75% of a change, there is no motion to compensate, so blend wins. `tests/test-frame-rate.py` repeats this test whenever FFmpeg is present.

**6. A real film.** `sample-engine-mix` (24 s portrait, two Blender plates, editorial diagrams, a counter):

- **Plan:** 21.97 s motion, 1.33 s hold, 0.63 s dissolve, no hard cuts (studio films cross-dissolve). In-between frames: blend 451, MCI 153, copy 116, so 84% synthesised.
- **Probe:** held-out error on moving frames was copy 0.555, blend 0.241, MCI 0.257.
- **Result:** 1,440 frames, 24.000 s, **52.7 distinct frames/s against 28.3 in the source (1.86x)**.
- **Inspection:** full-resolution crops of an MCI frame on the refraction diagram (thin ray, dashed normal, monospace labels) and of a blend frame on the counter showed no tearing, warping or ghosting.
- **Cost:** the probe took 29.6 s. Conversion ran at 3.5-3.8 output frames/s at 720×1280 (408 s), because `minterpolate` is single-threaded.

## Known limits

- **Stepped motion over a drifting camera** has no exact holds, so it is not recognised as stepped. The probe often still picks copy for it, but not always.
- **One method per pair for the whole frame.** A frame with a clean pan and a particle burst gets one method. Per-region choice would need our own motion estimation, which is not worth it while `minterpolate` is the only MCI engine.
- **No per-stretch override.** `--method` forces one method on every measured pair.
- **Content not supported:** alpha (WebM plates come out opaque), HDR and 10-bit (8-bit yuv420p out), odd frame sizes. A VFR input is made constant at its average rate.
- **A learned interpolator** (RIFE and similar) would beat `minterpolate` on hard content. It is a new binary with GPU and Vulkan needs, so it needs an owner decision and a `dependency-intake-check` first. Not proposed here.
