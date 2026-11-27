# Smooth motion at 60 fps (native path)

What a native 60 fps render fixes, what it does not, and what to change in a composition so the motion reads as smooth and deliberate. The numbers are leads with stated thresholds, not verdicts. Calibration status is noted per rule.

## What 60 fps fixes on its own

- **Slow drift, pans and counters.** Most of a studio film moves slowly. In three workspace films, 54-58% of frame pairs changed by 0.25/255 or less, and 70-80% of those pairs kept moving over 10 frames (continuous drift, measured 2026-11-25, see [gap-filling.md](gap-filling.md)). At 30 fps a slow constant move steps visibly (judder) and sub-pixel edges shimmer. At 60 fps each step halves. This is the largest win for a typical film.
- **Sampling of fast eases.** A 0.3 s move gets 18 samples instead of 9, so the ease curve reads as a curve.
- **Dissolves.** A 0.4 s crossfade gets 24 steps instead of 12.

## What 60 fps does not fix

| Problem | Why it remains | Fix in the composition |
| --- | --- | --- |
| **Strobing** on fast moves | At 60 the peak travel per frame halves, but a hero card sliding 600 px in 0.3 s on `power3.out` still jumps 133 px per frame at its start. The eye sees separate copies, not a move. | Page motion blur (below), a longer move, or an ease with a lower peak (table below). |
| **Velocity jumps** | A linear move starts and stops at full speed. Smoother sampling makes the jerk easier to see. | Ease it, unless constant speed is the point (rotation, progress bars, tickers). |
| **Pops** | An opacity change of more than a third per frame is a cut, not a fade. | At least 3 frames at the target rate (0.05 s at 60). Entrances normally run 0.13-0.6 s anyway. |
| **30 fps layers** | A Blender plate or ingested clip at 30 fps shows each frame twice inside a 60 fps film. | Re-render plates at the project rate (`visual-director.py render`). `scripts/ingest-asset.sh` normalises clips to 30 fps, so ingest 60 fps footage separately. |
| **Stepped motion** | `M.stepped`, `boil`, `M.flicker` and `steps()` are time-based, so they stay stepped at any rate. | Nothing: it is a look. The audit only notes it. |

The audit's threshold for strobing is **2.5% of the frame's short side per frame at the target rate** (18 px on 720 px). It is a starting value: it matches the peak smear HyperFrames' own motion craft notes recommend for fast moves (6-12 px on text-sized elements, 15-20 px full-frame), so a move above it without blur shows gaps. It has not been calibrated against a viewer.

## Peak speed of an ease

Peak speed = slope × travel / duration. The slope is how many times faster than linear the fastest moment is, computed by `framerate.peak_slope`:

| Ease | Peak slope | Fastest at |
| --- | --- | --- |
| `none` | 1.00 | throughout |
| `sine.out`, `sine.inOut` | 1.57 | start, middle |
| `power1.out` (GSAP default) | 2.00 | start |
| `power2.out`, `power2.inOut` | 3.00 | start, middle |
| `power3.out` | 4.00 | start |
| `back.out(1.7)` | 4.70 | start |
| `power4.out` | 5.00 | start |
| `expo.out`, `expo.inOut` | 6.9 | start, middle |
| `elastic.out(1, 0.5)` | 9.2 | start |
| `circ.out` | unbounded at t = 0 | first frame |

Long-tailed arrivals (`expo.out`, `power4.out`) read as premium *because* they spend their speed in the first few frames. Those frames are the ones that strobe. So a long-tailed arrival needs motion blur on its fastest frames, or a longer duration. Do not swap it for a flat ease: that trades elegance for smoothness.

## Page motion blur (HyperFrames)

HyperFrames 0.8.226 smears fast movers along their path when the composition root opts in (docs: `hyperframes/dist/docs/motion-blur.md` in the global install):

```html
<div id="root" data-motion-blur="on" data-motion-blur-shutter="180" ...>
```

- `data-motion-blur-shutter`: shutter angle 0-720. The default is 240; 180 is the filmic standard; 360 is strong. The angle is relative to the frame, so at 60 fps a 180° shutter integrates 1/120 s, half the smear of 30 fps. Going to 60 does not double the blur.
- A translate-only mover gets a cheap SVG filter. A turn or zoom gets the truer capture tier. `data-motion-blur="off"` opts a subtree out, such as text that must stay crisp or a plate that carries its own blur.
- Run `hyperframes check`. It reports `motion_blur_filter_fallback`, `motion_blur_no_movers` and `motion_blur_unverified`. Then look at frame-review sheets at the fastest frames.
- **Status in this workspace: not yet verified in a studio build.** The attribute survives `studio.py formats`: `rewrite_root` rewrites only `data-format`/`-width`/`-height`/`-fps`/`-duration` and keeps every other root attribute (read in `scripts/studio.py`, 2026-11-25).

## Ease, timing and transitions that read as smooth

These are paraphrased from the HyperFrames motion craft notes (Apache-2.0, `dist/skills/hyperframes/references/motion.md`) and the workspace `motion-design` skill. Ideas only; no code was copied.

- **Ease by role:** arrivals land on a long tail (`.out`); camera moves and colour floods ease both ways (`.inOut`); exits and zoom-throughs accelerate (`.in`). Linear is only for constant speed that is the point.
- **Exits are 40-50% shorter than entrances.** The next element starts when the previous one is 30-50% done.
- **Cut at the fastest frame of a move**, with direction and speed matching on both sides. A slide or zoom-through transition is a full-frame fast move, so it strobes first. Give it blur.
- **Flash cut.** Reference `ref-1cbe55c987` is a 60 fps promo: its boundary frames 91, 645, 690 and 750 fall at 1.517, 10.75, 11.50 and 12.50 s, exactly 60 fps. Its three late cuts each carry a single neutral grey or white frame (10.76, 11.51, 12.51 s on its transitions sheet), and its titles arrive blurred and resolve to sharp in about 0.07-0.1 s. This is a technique to learn, not an asset to reuse (`ARCHITECTURE.md` section 0.8). At 60 fps one flash frame lasts 16.7 ms: a punctuation, not a fade.
- **Counters roll continuously.** `Studio.type.formatCount` updates every frame, so at 60 fps an odometer roll reads as motion rather than as flicker.
- **Keep the drift.** The anti-laziness drift (`Studio.space.drift`) is exactly what 60 fps smooths best. Do not remove it to "calm" a film; render it at 60.

## Checklist before `audit --apply`

1. `studio.py script <slug> --probe`, then `frame-rate.py audit <slug>`: no `strobe` lead left unaddressed (blur, duration or ease), and no `velocity-jump` lead without a reason.
2. Every video layer is either re-renderable at the new rate (a plate) or replaced by a 60 fps source.
3. Page motion blur: on with a shutter of 180-240 for films with fast moves. `hyperframes check` is clean, and the fastest frames have been looked at.
4. Fades and pops are at least 3 frames at the target rate.
