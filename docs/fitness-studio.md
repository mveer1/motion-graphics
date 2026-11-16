# The Sinew fitness studio: architecture, decisions, open items

Written 2026-11-13 after two assignments given together: upgrade the fitness workspace into a professional content studio (P1) and redesign the anatomy so muscles belong to the body (P2, mandatory and first). This is the map, the audit, the decisions and what is not done. The skill entry point is `/fitness` (`.claude/skills/fitness/SKILL.md`).

## 1. Architecture map (what exists, what talks to what)
```
brief + dossier (research)  ->  script/storyboard (story-writer)  ->  animatic + pacing lint
        |                                |                                   |
 assets/fitness/data/exercises.json  (knowledge: roles, phases, mistakes) -> fitness.py exercise (explanation plan)
        |                                |
 src/studio/kits/fitness/                |   one skin, one muscle table             -> scripts/anatomy3d-check.js, anatomy3d-bench.py
   anatomy3d.js  <- tibi3d.js (rig, stage, motion, bind) <- exercises3d.js (lifts, phaseMap, acts)
   film3d.js (HUD, pins, sensor, chip, angle, trail, cue)  <- scenes3d.js (demo, cutaway)
 2D: sculpt.js / exercises.js / graphics.js (mascot art, cards, charts)
        |
 composition (HTML, one paused GSAP timeline, pure functions of time)  -> hyperframes render (host lock)
        |
 audio: build-audio.py (Kokoro), captions (Whisper), sinew_sound.py (bed, SFX from phase map)  -> ffmpeg mux, loudnorm
        |
 QA: studio.py build gates (5) -> fitness-qa.py (diagnostics) -> fitness-gates.py (G1-G4, human sign-off) -> fitness-publish.py / fitness-clip.py
```
Retained unchanged: studio runtime and determinism rules, the render lock, the form system, the style template `body-lab`, the 2D Cobalt Sculpt generator (`src/fitness/tibi/`), the dossier protocol, the captions and sound stacks. Nothing was replaced for taste.

## 2. Audit findings (before any change)
| Finding | Evidence | Fixed by |
|---|---|---|
| Muscles were rigid ellipsoids parented to bones over a skinned loft body: raised stickers, no deformation, glute and calf "attached" | `tibi3d.js` 0.2 `ell()`/`M()`; the three lower-body films | `anatomy3d.js`: one skin (ADR-1) |
| The dumbbell press never moved in any composition | `m.path` returned unprefixed keys; figures with an id ignore them; stills bench used no id | prefix fix, `rig3d-check` builds figures with an id, range-of-motion and phase-fidelity checks |
| The supplied 2D-vs-3D clips began on a stale pose, had no audio, compared an incline curl with a standing curl, at different scale and out of phase | `fitness-qa.py` on the originals: frame 0 jumps 48.1 vs 0.4; no audio | `qa/regression/lab-3d-compare` (one phase clock, equal scale, same variant), narrated lab clips |
| `lat` lit on the lateral raise with no basis; nothing audited highlights against knowledge | exercises3d vs exercises.json | `fitness.py check` role audit; lat removed |
| No instructional layer (rep, phase, angle, path, cue) and no scene reuse | the lab and film compositions | `film3d.js` HUD/angle/trail/cue/sensor/chip, `scenes3d.js` |
| QA saw layout and loudness only | `run-qa-gates.sh`, `frame-review.py` (needs Playwright, absent here) | `fitness-qa.py`, `anatomy3d-check.js`, gates with human sign-off |
| `titleCard` always faded in: a bare first frame | `fitness-qa.py` start check on the calf film | frame-0 rule in `graphics.js` |
| Runtime code used `performance.now()` | `hyperframes lint` (non-deterministic) | removed; timing lives in the test scripts |

## 3. Decisions (ADRs)
**ADR-1 Anatomy: one skin, one muscle table.** Rejected: (a) recolouring the old ellipsoids, (b) a transparent duplicate body over an opaque one, (c) baked sculpted mesh data. Chosen: signed-distance fields smooth-unioned from the cores and every muscle volume, meshed once at load (surface nets, ~300 ms, deterministic, no assets), A-pose bind, region-vote skin weights. Why: a muscle that is part of the surface cannot protrude or float; the same table yields relief, surface masks, internal lofts, windows and anchors, so a new exercise never invents objects. Cost: stylised (ellipsoid-like) muscles, no sliding-skin simulation, ~25k vertices per figure. Alternative left open: a sculpted GLB for photoreal anatomy (the vendored Three.js can load one; Blender is still not installed).
**ADR-2 Character: refine the blue Tibi, do not replace it.** The recognisable silhouette, palette and spark are the brand. Two bodies (m/f), four modes (normal, activation, anatomy, 2D storytelling) instead of four characters.
**ADR-3 Activation as colour deltas on the skin, computed on the CPU.** Per-vertex arrays (no uniform arrays), so the result is identical in node (tests) and in the browser; highlights are soft gradients (mask diffusion), cloth has its own variant so a glute glows through shorts without a pale flash.
**ADR-4 Cutaways are windows in bind space, evaluated per fragment.** They stay registered in any pose and open in two stages (skin, then the superficial layer). Inner geometry is pulled inside the skin by construction; nothing intersects.
**ADR-5 A visual language with one meaning per colour** (see `assets/fitness/STYLE.md`): skin, effort, anatomy, ghost, measurement never share a colour. Sensors are drawn as sensors.
**ADR-6 Animation: authored key poses plus solved contacts, hybrid.** Mocap and external libraries were not adopted: the lifts are few, the poses are solved from contacts and balance, and an authored curve is explainable and "illustrative" by honest label. Revisit with a measured-motion source if a film needs real kinematics.
**ADR-7 One phase machine per exercise**, in the kit, read by the HUD, the cue cards, the 2D comparison rig and the sound: picture, sound and teaching share one rhythm.
**ADR-8 Automation fails, humans approve.** G1 and G3 (accuracy) need a named human in `qa/fitness-signoff.json`.
**ADR-9 No new dependencies.** Three.js (vendored), Chrome, ffmpeg, node, numpy, Pillow were already present.

## 4. What was verified, and how
- `node scripts/anatomy3d-check.js`: watertight single-component skin, nothing protrudes, layers in anatomical order along each cut axis, soft mask edges, highlights registered through squat, curl, raise, hip thrust and calf raise, no collapsed triangles, colour language separated (both bodies).
- `node scripts/rig3d-check.js`: all 8 exercises x 2 bodies: continuity, contacts, reach, limits, colour steps, range of motion, phase fidelity.
- `scripts/anatomy3d-bench.py`: contact sheets (`qa/anatomy3d/`) looked at, not only measured.
- Nine regression videos re-rendered and run through `fitness-qa.py` (see `qa/fitness-render-qa/`); the three lower-body films before/after compared frame by frame.

## 5. Not done, or limited (be honest)
- No human creative review or accuracy sign-off was recorded: `qa/fitness-review.json` rubrics are unscored, `qa/fitness-signoff.json` does not exist; gates G1 and G3 are awaiting a human.
- The look is stylised: muscles are tapered ellipsoid volumes (deltoid and pec still read as soft ovals up close); no tendon/fascia detail, no skin sliding, 12-20 muscles per side, a simplified skeleton.
- The female body's crop top is a straight-edged colour band over a subtle bust relief (reads as a garment block, not a tailored top); the male body's shorts hem is a small step, not cloth simulation.
- Cutaway windows exist for calf, glute, quad, hams, upper arm (front and back) and chest; chest/arm/hams windows were built but only calf, glute and quad were composed into films.
- Deadlift, lunge, leg press, curls on machines, running are not ported to 3D. Kinematics remain authored.
- The Yellow Dude production page returned 404 and search did not surface it; the 3D reference-video study was not possible offline. No claims are made about their process.
- Text-outside-safe-area and label-overlap checks are visual (snapshots), not automated: `frame-review.py` needs Playwright, which this host lacks.
- The compare fixture is a regression asset (`qa/regression/lab-3d-compare`), not a publishable project.
- Peak render memory was not measured; builds ran one at a time under the host lock.
