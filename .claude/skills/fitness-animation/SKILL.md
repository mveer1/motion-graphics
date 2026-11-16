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

New exercise: add it to `exercises3d.js` (key poses or a `m.path`, equipment from joints, `shots`, `phaseMap`, `acts`, `knowledge`), add the knowledge record, `fitness.py check`, `rig3d check`, stills from four angles, `studio.py upgrade --all`.
