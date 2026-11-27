---
name: fitness-animation
description: Authoring and checking 3D exercise animation for Sinew films: the phase machine (setup, start, eccentric, end range, concentric, lockout, reset), exercise motion rules, camera plans, the instructional overlays (rep HUD, tempo bar, cue card, joint-angle arc, movement trail, muscle pins), the scene library and the numeric checks. Use for any curl, press, raise, squat, hip thrust or calf raise film, or when adding a new 3D exercise.
version: 1.0.0
---

# Fitness animation: movement that explains itself

Read `references/motion-3d.md` (rules 1-16, tools) first; this skill is the workflow on top of it.

1. **Plan from knowledge, not from taste.** `python scripts/fitness.py exercise <id> --goal technique|muscle|mistake|compare` prints the scenes, anatomy mode, cameras, must-show list, mistakes and corrections from `assets/fitness/data/exercises.json`. Add missing fields there first (schema `specs/fitness-exercise-spec.json`).
2. **Every exercise has a phase map** (`phaseMap` in exercises3d.js: fractions of the rep period). The HUD, the cue card, the 2D comparison rig and the sound all read it through `T3.phaseAt` / `T3.phaseTimes`; `rig3d-check` fails if the map does not describe the motion (hold phases must be still, lifting phases must move).
3. **Compose with the scene library**, do not rewrite a demo: `T3.scenes.demo(stage, m, ov, cfg)` = figure + one continuous camera orbit + rep HUD + cue card + role-coloured pins + angle arc + load trail; `T3.scenes.cutaway` for anatomy. Call `scene.finish()` after the motion is declared, `scene.update(t)` from `T3.bind`'s onFrame. Reference: `projects/lab-3d-motion/src/index.html`.
4. **Camera**: one move or one cut per spoken cue, never an orbit and a cut together; the exercise names its good shots (`shots`). Hide nothing the cue is about (raise: front to three-quarter, curl: three-quarter, press: foot-end three-quarter, calf and glute cutaways: orbit behind first).
5. **Every motion key carries the figure id prefix.** An unprefixed key in a `m.path` froze the dumbbell press in every film (found 2026-11-13); `rig3d-check` now builds figures WITH an id and fails on a range of motion under 90 units (heel raises: their own `minRom`).
6. **Pins, angle arcs and trails are pure functions of time** (positions come from `fig.world(muscle@side)`, a surface point that rides the skin, and `T3.jointAngle`). Label angles and kinematics "illustrative".
7. **Check, then look**: `node scripts/rig3d-check.js <ids>` (continuity, contact, reach, limits, colour steps, range of motion, phase fidelity), `hyperframes snapshot --at ...` on the composition under `session-guard`, then the render and `scripts/fitness-qa.py`.

Since runtime 1.9.1, `T3.bind` calls `onFrame` after camera preparation but
before drawing. Scene visibility and pins therefore belong to the current
frame. Read completed canvas pixels only after the seek returns. Use
`scripts/rig3d-seek.py` to check fresh/revisited parity, including split views.

Runtime 1.10.0 makes the corrected `profileSampling: 'distance'` body the
development default after the requested full-body correction. Explicit
`legacy` is a comparison path, not anatomical approval. Public pose keys and
exercise timing are unchanged. Test both profiles and the seek suite.
For 30 fps strips, `rig3d-stills.py --extra "profile=distance&id=audit&period=3.4"`
uses the same candidate, named-figure path and explicit repetition period.

Check the actual composited skin/cloth colour arrays, not only muscle ramp
records: the latter missed an overlapping-mask fade regression. Morph normals
must be recomputed from the current bulged surface and must not mutate another
figure's arrays. A proposed skinning replacement needs local joint evidence;
the first DQ trial increased overhead triangle stretch and was not adopted.

New exercise: add it to `exercises3d.js` (key poses or a `m.path`, equipment from joints, `shots`, `phaseMap`, `acts`, `knowledge`), add the knowledge record, `fitness.py check`, `rig3d check`, stills from four angles, `studio.py upgrade --all`.

## 3D exercise port checklist (standard: `scripts/prompts/04-pending-3d-exercise-library.md`)

Lived on the 2026-11-23/24 Windows port of 18 exercises. One solver family per version bump.

| Step | Command / rule | Trap seen |
| --- | --- | --- |
| 1 Knowledge | record in `assets/fitness/data/exercises.json` with `rig3d_status: "pending"`; every source checked on Europe PMC | no percentages ("40% 1RM" fails `test-fitness`) |
| 2 Solver | contacts/balance in `exercises3d.js`, prefixed keys, one `m.path` per coupled chain | pads and back contacts need their own gap gate |
| 3 Checks | exercise `checks` prove each cue; a mistake variant must FAIL the correct exercise's gate and print why | a variant that does not show the mistake is useless: gate it (`... the mistake is not visible; needs N`) |
| 4 Numeric | `node scripts/rig3d-check.js <id> [<id>-mistake]` then `--gender f` (full set: about 7 min m, 18 min f, under `session-guard.py run render --`) | a checker gate that never ran still exits 0: make it fail on purpose once |
| 5 Library | set `rig3d_status` off pending, `python scripts/fitness.py library`, `fitness.py check` | stale `library.js` |
| 6 Look | stills of every phase, both bodies, four angles + `shots`; normal and clay; write what you saw | barbell side view near plate hides the chest: tilt the camera down |
| 7 Tests | add a bite test in `tests/test-rig3d.py` (`patched_check`), run it alone first | anchor strings drift: re-read before patching |
| 8 Release | `kit-release` skill | |
