---
name: motion-director
description: Review and polish the motion design of a composition or render. Use after a build, or when a piece feels like a template: run motion QA, read the measured leads, look at contact sheets and seams, critique with evidence, fix, re-render (one scene at a time if possible) and record an honest creative review.
---

# Motion Director

Surfaces problems with numbers and leaves the verdict to a person or a model that has looked at the frames. A successful render proves only that the render succeeded.

## Loop

1. `python scripts/motion-qa.py composition <slug>` before rendering (needs the HyperFrames browser; runs under the render lock). Fix text collisions, undersized type, repeated layouts, card piles.
2. Render with `studio.py build`. Then `python scripts/motion-qa.py project <slug> --expect-audio` for the video checks and the critique pack (`qa/motion/scene-sheet.jpg`, `seams.jpg`, `critique.template.json`).
3. **Look.** Describe every sheet frame in one sentence (what is on screen, what is the hero, would it pass as a slide) before judging. Watch the seams. Listen if you can; the tool cannot (`audio-cut-alignment` is an explicit skipped check).
4. Fix in this order: broken or untrue, the idea, connections between beats, hierarchy and scale, timing, surface and finish. Re-render. Two or three passes.
5. Revise one scene: `python scripts/scene-revise.py <slug> --scene s3` re-renders the scene plus padding and splices it in.
6. Score `qa/creative-review.json` with evidence paths and the weaknesses you actually see. A column of identical scores is a sign of rubber-stamping.

## Reading the report (`specs/qa-report-spec.json`)

- **objective** (fail): the file is wrong: wrong size/fps/duration, true black frames, missing required audio, page JavaScript errors.
- **measured** (warn/note): a number against a stated threshold. A lead, not a verdict. Thresholds are starting values; those adopted from Motionmaxxing say so and are unreproduced here.
- **judgment** (question): artistic questions for the critic; never pass/fail.
- **waived**: a declared `intent` (`still`, `minimal`, `dark`) or capability (`frame-hud`, `progress-stepper`, `caption-band`) explains it. Waivers stay in the report with their source.
- `technical_pass` = no objective failure and every required check ran. It says nothing about quality.

## What the checks mean (and their limits)

Static hold = low per-frame change AND low change over 0.5 s (a slow drift is alive; calibration: frozen 0.06-0.10, drifting 0.9-1.9). Repeated composition = ink-map distance below 0.05 (a re-skin scores 0.02-0.07; real alternatives 0.15+). Contrast over images is not estimated. Occupancy ignores full-frame grounds. Hud-label/counter rules are heuristics: stepped tutorials and information tapes are legitimate; declare them.

## Motion vocabulary

`specs/motion-vocabulary.json`: 28 entries with GSAP ease, duration range, when to use and avoid, and an evidence class (`convention`, `adopted-unverified`, `workspace-measured`). Use as starting points; do not apply every effect to every scene; do not turn a rule from a launch-film corpus (never fade, always cut on motion) into a law for an explainer.
