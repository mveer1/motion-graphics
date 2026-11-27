---
name: fitness-anatomy
description: Tibi's body and how anatomy is shown in a Sinew film. Use when a film highlights a working muscle, opens an anatomical cutaway, isolates or ghosts a muscle, shows a skeleton, draws an EMG sensor, or when a muscle looks detached, raised or glued on. Covers the one-skin architecture, the four visualization modes, the muscle table, the windows, the visual language that keeps skin, activation, anatomy and data apart, and the acceptance tests.
version: 1.0.0
---

# Fitness anatomy: one body, four ways to look at it

**Muscles are part of the body, never stickers.** Since 2026-11-13 Tibi 3D is ONE continuous skin; a muscle is relief of that skin plus a region of its surface, never an object on it. The old rig (rigid ellipsoids parented to bones) is gone. Source: `src/studio/kits/fitness/anatomy3d.js` (read its header first); asset story: `references/character-guidelines.md`, `assets/fitness/STYLE.md`.

**A connected mesh can still look like glued-on anatomy.** Inspect normal and
neutral-clay region sheets. Exterior-looking lat lobes, disc-like pecs and
joint pads are failures even when topology/seek tests pass. Do not relabel an
observed defect as a benign known limit merely because a numeric gate missed it.

## Architecture (single source of truth: the muscle table `MUSCLES` in anatomy3d.js)

| Layer | What it is | Derived from the table |
| --- | --- | --- |
| Skin | core limbs + trunk + every muscle volume smooth-unioned as signed-distance fields, meshed once (surface nets), A-pose bind, weights by region votes, shorts as a colour region with a hem step | muscle volumes give the relief |
| Surface activation | per-vertex weights of the 8 nearest muscles, diffused over the surface, so a highlight is a soft gradient on the skin that follows deformation; bulge = displacement along the normal | masks |
| Internal anatomy | muscles (layer 1 superficial, layer 2 deep), tendons, bones, vertices fitted inside the resting skin envelope | the same profiled volumes, lofted |
| Windows | ellipsoids in BIND space evaluated per fragment, so they stay on the anatomy in any pose: open 0 to 1 skin out, 1 to 2 superficial layer out | `WINDOWS` |

## Modes (pose keys, so they animate like any track; film ids prefix them: `s.cut.calf@L`)

1. **Normal** (default): no keys. A convincing body with no highlight.
2. **Activation**: `act.<muscle>` + `fig.roles({muscle: 3|2|1})` (coral prime, marigold helper, pale cobalt stabiliser). Gradient on the skin or on the shorts.
3. **Cutaway**: `cut.<window>[@L|@R]` 0 to 1 to 2 (windows: calf, glute, quad, hams, arm, tri, chest); `hi.<muscle>` highlights one muscle inside (coral); `T3.scenes.cutaway(m, cfg)` registers the tracks. Open the window on the side the camera sees (calf, glute and hams open at the back: orbit behind first).
4. **Isolated / layers**: `view.ghost` fades the skin, `iso.<muscle>` floats one muscle beside its place, `view.layer` shows the whole muscle layer, `view.skel` shows bones only. Isolation is always intentional; never mix it into an ordinary demo.

## Visual language (one meaning per colour; do not break it)

- cobalt = the external body · coral/marigold/pale cobalt gradient ON the skin = effort by role · rosewood/ivory/cream-section-line = anatomy UNDER the skin · pale ghost = skin made transparent · a trace card with electrode discs = a measurement.
- An EMG electrode is drawn as an electrode (`FX.sensor`: discs on the skin, wire, trace card labelled illustrative), never as a muscle-shaped object. A graph is a graph. Label the cutaway ("Under the skin", `FX.chip`). Inside a cutaway colour follows `hi.*` only (opt in to effort with `view.effort`).

## Adding a muscle or an exercise

A new exercise never invents external objects: name the muscles it uses from the table (`acts`), add the role to `assets/fitness/data/exercises.json` (`fitness.py check` audits every highlight against the knowledge file). A new muscle is a row in `muscleTable` (bone-local centre, radii, rotation, taper `pw`, optional longitudinal width/thickness `profile`, mask `[full, fade]`, layer); keep deep muscles `layer: 2`. The surface, activation and internal loft must use the same profile. Cite shape/attachment references in the table comments and `assets/fitness/data/muscles.json`; rig dimensions are illustrative authoring choices.

## Tests (run after ANY change to anatomy3d.js, then `studio.py upgrade --all`)

`node scripts/anatomy3d-check.js` (zero open boundary edges, one component, separate non-manifold count, internal envelope/layer checks, mask coverage, registration, deformation and colour language) and `node scripts/rig3d-check.js`. Look at the frames too: `scripts/anatomy3d-bench.py`. A closed skin is not necessarily strictly manifold, and a passing gate is not an anatomy approval.

Windows stills: use `.venv\Scripts\python.exe`. The bench finds the Windows Puppeteer executable or honours `CHROME`; no browser install is attempted. Captures must reach the page's `ready` title and write a fresh, correctly sized image or the command fails. Keep the host lock. Setup and line-ending caveats: `docs/fitness-studio.md` section 6.

Seek parity (runtime 1.9.1): `python scripts/rig3d-seek.py --set all --out qa/rig3d-seek`
compares a fresh target with the same target after another state, for both bodies.
The numeric anatomy gate requires exact position/normal/colour recovery after a nearby
pose; never round the cache key. Ghost-to-normal resets must invalidate the
material's shader variant. A matching frame is not anatomical approval.

Current body (1.10.0, requested full-body correction): `distance` is now the
default on `stage.tibi`, `T3.scene` and the benches/checkers. It includes
physical profile sampling, embedded fans/bands, a deep upper-arm brachialis,
figure-local morph normals, bounded activation mixing and a torso-owned top.
Use explicit `profileSampling: 'legacy'` / `--profile legacy` only to compare
the old body. Legacy retains known anatomical design defects. Caches remain
separate; 2D art and palette tokens are unchanged.

The local gates must bite: lat relief/coverage and no elevation-only inflation,
biceps -> brachialis -> humerus layer order, exact morph normals and instance
isolation, all three role colours inside linear RGB bounds, actual skin/cloth
colour steps <= 0.12 per frame, and no top colour on arm-dominated vertices.
Tests run the actual checker against controlled in-memory defects.

`anatomy3d-bench.py --set regions --gender both` covers 29 views per body.
Repeat with `--shade clay` to separate geometry from paint. `--set review`
adds the original orbit/joint/window/exercise-phase/mode sets (316 situations).
The 20-case seek suite applies separately to current and legacy bodies.
Run `rig3d-seek.py --set locality` separately: cutaway interiors must not
change pixels outside the projected window bounds, and must visibly appear
inside. `--unclipped-control` must fail for off-window pixels. Depth occlusion
alone is not containment; internal and outer skin can deform differently.
Whole-layer, skeleton and isolation modes are deliberate exceptions.
Inspect first, then use `--report-only --review` to record evidence. Human G3,
precise joint mechanics and a fully manifold/clinical atlas remain separate.
See `docs/fitness-studio.md` section 9.

Shoulder follow-up (1.11.0): the owner rejected the 1.10 caps despite its tests.
Check the full posed silhouette, including `part` volumes: an unmasked joint
sphere and a broad flat arm root survived the muscle-only review. The current
body uses a sloping shoulder envelope and rounded-end tapered deltoids.
Show geometry at an identical old pose separately from the new neutral stance.
Static benches use `fig.defaultPose`; authored-motion defaults remain in
`T3.DEFAULT_POSE`. Actual contour/clearance gates and controlled old-orb,
flat-root and old-stance failures supplement looking at normal/clay frames.
Hands are still stylised, not an articulated finger rig. See section 10.

Flank and hip follow-up (1.12.0): a 10-unit lateral serratus slab, a horn at
the pec's lateral end, a glute-medius egg ending at the waistband and the flat
full-radius top of each leg tube all formed ledges in the front silhouette.
All four were in the pictures since 1.10 and passed every numeric gate.
`anatomy3d-check` now measures the projected torso half-width row by row
from under the armpit to the waistband and down the hip (neutral pose); a
step over 5 units per 5 fails. Thin sheets lie along the surface, never
along its normal. See `docs/fitness-studio.md` section 12.

Shoulder girdle (anatomy 1.6.0, Tibi 0.8.0, runtime 1.15.0): skin around each
shoulder is shared between chest, girdle (`gdS`) and soft-tissue (`axS`) bones
by `A.GIRDLE_WEIGHTS`; the field stops 70 under the joint and the lat below the
armpit stays on the chest. The anti-lat-bulge gate is now `latInflation` (morph
AND bone channels): a girdle that owns the back fails it. `shoulderCrush` and
`armpitLift` gate the raised arm; `A.GLIDE` is an experiment, off by default
(switching it on fails the inside-out gate). Remaining overhead wings, side
flap and female top corner: `motion-3d.md` "Shoulder girdle".
