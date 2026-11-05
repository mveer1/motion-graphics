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

### Detector behaviour seen on the Nov 2026 films (cloud, Korea, fridge)

- **`low-contrast` 1.0:1 on caption pills is a false positive.** In cloud, 10 of 11 contrast warnings are white caption text on a dark `rgba()` pill; the estimator reads the page background behind the pill. The frames show it clearly legible. Declare `caption-band` rather than changing the colours. Real contrast warnings in the same runs were 4.0:1 against 4.5:1 on small red labels ("Emergency power shutdown", "burned").
- **`text-echoes-narration` fires on captions by design** (cloud s1 100 %). Only act on it for headlines and labels.
- **`static-hold` is area-blind.** Korea's flagged 12 s stretch (1.6–13.7 s) does change every 2 s in the contact sheet (fire blooms, shrinks), but over a few tiles. Read the sheet before accepting or dismissing the number: the flag is right that the frame as a whole is idle, and wrong to call it frozen. Cloud's and fridge's 2–3 s "frozen" notes were frozen in the sheets too.
- **Not covered by any check, seen only by looking:** a kicker touched by the art above it (cloud 5 s), a leader line through a word (fridge 33 s), and a label sitting on its own node (cloud "DELHI"). Open the full-size frame at each scene's first beat and last beat.
- **Audio:** `earshot critique film.mp4 --fast` runs under `python scripts/session-guard.py run --slug <slug> analysis -- <abs path to earshot> critique <abs mp4> --fast < /dev/null` (the `audio` guard subcommand is for TTS only). `--fast` skips realness and music presence, so a "close" or "launch-grade" verdict from it is partial; run without `--fast` before shipping.

### Variety and conflict leads (`tweens.py`, added 2026-11-05)

`motion-qa composition` also dumps every GSAP tween from the paused timeline (`scripts/tween-probe.mjs`, a headless Chrome under the render lock) and `src/pipeline/tweens.py` reports measured leads. Thresholds are adopted from HyperFrames' motion principles and calibrated on three films only.

- **`tween-conflict` (warn):** two tweens animate the same property of one element at the same time (overlap over 0.12 s, four frames), so one overwrites the other. First real catch: in cloud, one `<g>` group enters on `scale` (0.35 to 1.4 s, `back.out(1.7)`) while a pulse tween on the same `scale` starts at 1.15 s, so the pulse takes over mid-entrance (a second pair of `scaleY` tweens overlaps at 10.8 to 11.1 s). Not yet confirmed in the rendered frames. Fix: put the second tween on a parent or child wrapper, or make them sequential. Overlaps under 0.12 s are fade hand-offs and are ignored.
- **`ease-monotony`, `ease-variety`, `duration-uniformity`, `scene-speed-uniformity`, `entrance-direction`:** one ease, one speed or one direction carrying the film. Ease is the adverb: `expo.out` is confident, `sine.inOut` dreamy, `elastic.out` playful. Speed carries weight (0.15 to 0.3 s urgent, 0.3 to 0.5 s professional, 0.5 to 0.8 s weighty, 0.8 s and up cinematic). On the three Nov 2026 films only Korea's s3 fired `ease-monotony` (a note: 3 of its 4 entrance recipes on `power1.out`); entrance medians were 0.35 to 0.5 s and each film used 5 to 8 distinct eases, so a firing is worth reading.
- **`entrance-ease-in` / `exit-ease-out` (note):** enter on `.out` (starts fast, settles), leave on `.in`. Fridge uses `power1.in` on a few path draws and cloud on one; both are minor.
- **`exit-slower-than-entrance`, `start-on-cut` (note):** things take longer to arrive than to leave; a 0.1 to 0.3 s offset after a scene cut reads less like a jump cut.
- **`tween-transform-overlap` (note, unverified):** an entrance `from()` and a different transform tween on one element together; the reference says this can hide the element. Not reproduced on this runtime.
- **`platform-ui-zone` (note):** text reaching the bands reel apps cover with their own interface (reference margins in `specs/format-presets.json`, uncertified). Cloud's captions end at 78.3% of the height against the 76.6% reference line and four right-hand labels reach 93.8% against 88%. The working safe area is unchanged; read this as a delivery hint.
- **Connector lines (judgment prompt):** when the storyboard uses `connector-draw`, `stroke-draw`, `hand-underline` or a similar capability, the critique pack asks you to name each line's start anchor, end anchor (real elements, not empty space) and job (revealing, routing, validating, emphasising). A line the frame can lose without losing meaning is decoration: cut it.

## Motion vocabulary

`specs/motion-vocabulary.json`: 28 entries with GSAP ease, duration range, when to use and avoid, and an evidence class (`convention`, `adopted-unverified`, `workspace-measured`). Use as starting points; do not apply every effect to every scene; do not turn a rule from a launch-film corpus (never fade, always cut on motion) into a law for an explainer.
