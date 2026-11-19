# 02 · Analyse and perfect the 3D Tibi in every situation a film can put him in

> Read `prompts/00-shared-context.md` first. If you are also running `01-tibi-design-takeover-windows.md`, do its Phase 0 (honest machine) before this.

## The goal

Find every way the 3D Tibi looks wrong, weak or off-brand across the full range of situations a Sinew film can create, and fix as many as possible **at the source** (`anatomy3d.js`, `tibi3d.js`, `exercises3d.js`, `film3d.js`, `scenes3d.js`, the stage and lighting), so that any future film gets a body that holds up without per-film patching.

"Perfect" is the direction, not a claim. Your output must let the owner see, situation by situation, how good Tibi is now, how good he was before, and what is still not good enough and why.

## Why this is hard

Tibi was checked so far on a narrow path: the poses of eight exercises, the cameras those films used, and a portrait frame at 720 px. The anatomy is new (runtime 1.9.0, one SDF skin with linear-blend skinning from an A-pose) and has never had a human anatomy sign-off. Linear-blend skinning, ellipsoid muscle volumes and a toon ramp each have typical failure modes. Expect volume loss and "candy-wrapper" twisting at forearm and shoulder, pinching and interpenetration at deep knee, hip and elbow flexion, the armpit and groin collapsing, banding and aliasing on the toon ramp at grazing angles, and muscles that read as blobs rather than shapes. Some of these will only show from cameras or poses no film has used yet. Find them before a film does.

## Step 1: build the situation matrix

Design a matrix that covers what films will actually ask for, and render it as labelled contact sheets you **look at**. Extend `assets/fitness/lab3d/anatomy-bench.html`, `still.html`, `scripts/anatomy3d-bench.py` and `scripts/rig3d-stills.py`, or build a successor, but keep it one reproducible command with named presets. At minimum, cover these axes (prune combinations that don't matter, and say which you pruned and why):

| Axis | Values worth covering |
|---|---|
| Body | male, female |
| Camera azimuth | 0, 45, 90, 135, 180, 225, 270, 315 |
| Camera elevation | low (−10°), eye (10°), high (35°), above (65°) |
| Framing | full body portrait (the rule-13 limits: top ≥ y 330, floor ≤ y 895), full body landscape, square, mid shot (hip up), close-ups of shoulder girdle, chest, upper arm, forearm and hand, trunk and abs, hip and glute, thigh and knee, calf, ankle and shoe, head and spark |
| Pose | A-pose bind, relaxed stand, and every exercise at setup / mid-eccentric / end range / mid-concentric / lockout; **extremes**: elbow 150, knee 150, deep hip flexion, full overhead reach, max shoulder abduction, max trunk twist, supine and prone, seated, hinge; plus combinations no film has used yet (arms overhead while squatting, one-arm reach across the body) |
| Mode | normal; activation per role (prime, helper, stabiliser) singly and combined; every cutaway window on both sides at stages 0.5, 1, 1.5 and 2; `hi.*` inside; ghost; isolate; layer; skeleton; `view.effort` |
| Context | one figure; two figures in one world; split views (`stage.views`); with the film overlays (HUD, cue card, pins, angle arc, trail, sensor, chip) and the caption band and header plate in place |
| Equipment | dumbbells, barbell and plates, bench, board or block; grip and contact points |
| Size | thumbnail (~120 px tall figure), feed size, full frame, and a 2× supersample to separate geometry problems from aliasing |
| Time | mid-tween frames and ramps, not only key poses; camera orbits during a rep |

Also cover the motion over time, not only stills: short strips or GIF-like frame rows for each exercise at 30 fps around fast phases, so you can judge smoothness, bulge timing, highlight registration while the skin deforms, and colour ramps.

## Step 2: measure what can be measured

Pictures find problems. Numbers keep them fixed. For every defect class you find, ask whether a **numeric check** could catch it, and add one to `scripts/anatomy3d-check.js` or `scripts/rig3d-check.js` (or a new checker) when it can. Ideas, not orders:

- local volume or area preservation near joints across each exercise's range (catches candy-wrapper and collapse)
- skin self-intersection or interpenetration at deep flexion (triangle–triangle or SDF sampling)
- inverted or degenerate triangles and normal flips under deformation
- silhouette continuity from all eight azimuths (no notch or spike between neighbouring frames)
- activation-mask registration: the highlight centroid stays over the muscle's anatomical landmark through the range
- colour-language separation as a perceptual distance (ΔE) between skin, effort, anatomy, ghost and measurement colours, plus a colour-vision-deficiency simulation of the role colours
- minimum readable size of a highlighted muscle at feed size
- equipment contact: hand-to-handle and sole-to-floor error, and plate-to-head clearance from the film's cameras

**Prove each new check bites**: make a deliberately broken case, confirm it fails, then restore it. Record the threshold and why you chose it.

## Step 3: diagnose by cause, not by symptom

Group the findings into a **defect taxonomy** with a severity for each (critical: wrong anatomy, wrong teaching, or breaks the brand; major: visible in a normal film frame; minor: only in close-ups or extremes). For each class, name the root cause in the system (skinning method, bind pose, weights, muscle primitive shape, SDF blend radius, mesh resolution, shading ramp, light rig, camera defaults, overlay layout) and the fix options with their cost. Some likely directions to evaluate on evidence, not on faith:

- **Skinning**: dual-quaternion or other volume-preserving skinning, corrective shapes driven by joint angle (elbow, knee, shoulder, hip), better weights from geodesic or heat diffusion instead of region votes, a twist-bone split for the forearm and upper arm.
- **Muscle shape**: fan and multi-lobe primitives for deltoid (three heads) and pectoralis (clavicular and sternal), spline or capsule muscles for long muscles, tendon and aponeurosis flattening, and showing the muscle's direction of pull in the relief.
- **Mesh**: resolution where it matters (adaptive surface nets, local refinement), smoothing that doesn't eat relief, and seams at the shorts hem and the female top.
- **Shading**: band placement and anti-aliasing of the toon ramp, rim or crease lines that stay true to "a 24 % darkening, never an outline", and how close a camera-relative light and shade split can come to the 2D crescent planes (this links to the owner's pending look decision; see `05`).
- **Clothing and accessories**: a tailored female top, the shorts hem, a bending shoe sole with a foot roll, a ponytail with secondary motion that stays deterministic (a pure function of time, for example a damped response computed analytically from the trunk's motion history), and a spine curve on the bench.
- **Known open items** from `motion-3d.md`: the quad as a flat disc on a horizontal thigh, the hip-thrust glute facing the floor, deltoid and pec as soft ovals.

Anatomy claims need sources. When you change how a muscle is shaped or where it attaches, cite an anatomy reference in the muscle table comment and in `assets/fitness/data/muscles.json`, and never invent one. The anatomy is still **illustrative**. Don't let it imply precision it doesn't have.

## Step 4: fix in priority order, prove each fix

Use value per cost: critical defects first, then whatever appears in the most film frames. For each fix:

1. a before sheet (the same matrix slice);
2. the change, in the master source only;
3. all node checks and the Python tests, with the new check added if one applies;
4. an after sheet, side by side with the before, looked at and described in words;
5. performance: verts, build ms, frame ms, before vs after;
6. the docs updated in the same change (`fitness-anatomy` SKILL, `motion-3d.md` limits and rules, `docs/fitness-studio.md` §5, `STYLE.md` if the look changes);
7. `Studio.version` bumped with a changelog line, and `upgrade --all` where projects exist.

If a fix changes the look visibly (shading, proportions, the female body), **don't ship it as the default**. Put it behind an option, show both in `prompts/state/decisions-needed.md`, and wait for the owner.

## Step 5: an acceptance suite the owner can trust

Leave behind a **Tibi 3D acceptance suite**: the matrix presets, the numeric checks, and a one-page report generator that says, per situation, pass / known limit / fail with a thumbnail. Run it on the final state and on the state you started from, so the improvement is visible. This is what G3 reviewers will look at, so make it legible to a non-programmer (an HTML page in a scratch folder or `qa/` is fine; ask before committing generated images, and keep any committed images small).

## Deliverables

- the matrix tool and presets, and the new numeric checks (each shown to fail on a broken case)
- `prompts/state/tibi3d-findings.md`: the defect taxonomy with severity, root causes, fixes done (with before and after) and fixes not done (with why)
- the kit changes, tests, version bump and docs
- the acceptance report (start state vs end state)
- entries in `decisions-needed.md` for look-changing options, and in `render-queue.md` for the Mac: re-render `lab-3d-motion` and the three lower-body shorts, then run `fitness-qa.py` and a motion-only continuity pass on each
- a short closing note: the three things that most improved, the three biggest remaining weaknesses, and what it would take to fix them

## Out of scope here

New exercises (that's `04`), 2D art changes (`05`), and studio tooling outside the character (`06`). If you find something there, write it down and move on.
