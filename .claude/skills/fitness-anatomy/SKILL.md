---
name: fitness-anatomy
description: Tibi's body and how anatomy is shown in a Sinew film. Use when a film highlights a working muscle, opens an anatomical cutaway, isolates or ghosts a muscle, shows a skeleton, draws an EMG sensor, or when a muscle looks detached, raised or glued on. Covers the one-skin architecture, the four visualization modes, the muscle table, the windows, the visual language that keeps skin, activation, anatomy and data apart, and the acceptance tests.
version: 1.0.0
---

# Fitness anatomy: one body, four ways to look at it

**Muscles are part of the body, never stickers.** Since 2026-11-13 Tibi 3D is ONE continuous skin; a muscle is relief of that skin plus a region of its surface, never an object on it. The old rig (rigid ellipsoids parented to bones) is gone. Source: `src/studio/kits/fitness/anatomy3d.js` (read its header first); asset story: `references/character-guidelines.md`, `assets/fitness/STYLE.md`.

## Architecture (single source of truth: the muscle table `MUSCLES` in anatomy3d.js)
| Layer | What it is | Derived from the table |
|---|---|---|
| Skin | core limbs + trunk + every muscle volume smooth-unioned as signed-distance fields, meshed once (surface nets), A-pose bind, weights by region votes, shorts as a colour region with a hem step | muscle volumes give the relief |
| Surface activation | per-vertex weights of the 8 nearest muscles, diffused over the surface, so a highlight is a soft gradient on the skin that follows deformation; bulge = displacement along the normal | masks |
| Internal anatomy | muscles (layer 1 superficial, layer 2 deep), tendons, bones, every vertex pulled inside the skin by construction | the same spindles, lofted |
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
A new exercise never invents external objects: name the muscles it uses from the table (`acts`), add the role to `assets/fitness/data/exercises.json` (`fitness.py check` audits every highlight against the knowledge file). A new muscle is a row in `muscleTable` (bone-local centre, radii, rotation, taper `pw`, mask `[full, fade]`, layer); keep deep muscles `layer: 2`.

## Tests (run after ANY change to anatomy3d.js, then `studio.py upgrade --all`)
`node scripts/anatomy3d-check.js` (watertight skin, one component, nothing protrudes, layer order along each cut axis, mask coverage and soft edges, highlight registration in squat/curl/raise/thrust/calf-raise, deformation, state-colour separation) and `node scripts/rig3d-check.js`. Look at the frames too: `scripts/anatomy3d-bench.py` (front, rear, sides, three-quarter, close-ups, every mode, several poses). The tests catch geometry; only a human catches ugly.
