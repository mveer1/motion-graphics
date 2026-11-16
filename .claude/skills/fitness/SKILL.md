---
name: fitness
description: Orchestrator for every fitness, exercise-science, running, gym, muscle or physiology video in the Sinew brand (mascot Tibi). Use when the user asks for a fitness topic as a short, mid or long film, for an exercise clip or comparison, or for anything about the Sinew brand, Tibi, the fitness asset library, exercise animation, anatomy visuals, the quality gates or publishing. Understands the task, picks the form and pillar, then loads ONLY the capability skills and assets the task needs and runs the studio pipeline with the fitness research protocol and review gates on top.
version: 2.0.0
---

# /fitness: the Sinew studio's entry point

Sinew is the workspace's fitness education brand: **"See what your body is doing."** Its mascot **Tibi** is one body (male and female, Cobalt Sculpt identity): cobalt skin, marigold spark, white shoes; working muscles light up on the skin by role (coral prime mover, marigold helper, pale cobalt stabiliser); what lies under the skin is shown in a different, warm language. This skill orchestrates; it does not replace the studio pipeline (`studio.py`, `build-audio.py`, captions, HyperFrames, the QA gates, the story-writer rules).

## Route the task, load only what it needs
| The task involves | Load | Key tools |
|---|---|---|
| any fitness film (always) | this skill + the form skill (`short-form`, `mid-form`, `long-form`) | `fitness.py plan/new/check` |
| claims, studies, "does X work", numbers | `references/research-protocol.md`, `source-registry.md`, `storytelling.md` | dossier, Europe PMC |
| an exercise demo, technique, mistake vs correct, a 3D lift | **`fitness-animation`** + `references/motion-3d.md` | `fitness.py exercise`, `T3.scenes.demo`, `rig3d-check` |
| muscle highlights, cutaway, isolated muscle, skeleton, EMG, "the muscle looks stuck on" | **`fitness-anatomy`** | `anatomy3d-check`, `anatomy3d-bench` |
| 2D mascot scenes, brand cards, charts, environments | `references/brand-guidelines.md`, `visual-systems.md`, `character-guidelines.md` | `K.sculpt`, `graphics.js` |
| voice, sound, captions | `references/production.md`, `scripts/sinew_sound.py`, `caption-designer` | `build-audio.py`, `studio.py captions` |
| review, gates, "is it done" | **`fitness-qa`** + `references/quality-rubric.md` | `fitness-gates.py`, `fitness-qa.py` |
| titles, description, thumbnail, clips, platforms | **`fitness-publish`** | `fitness-publish.py`, `fitness-clip.py` |
| the look, palette, type, camera language | `assets/fitness/STYLE.md` | |

## Invocation: `/fitness <topic> [short|mid|long] [portrait|landscape]`
1. **Classify and plan.** `python scripts/fitness.py plan "<topic>" [--type T]` (pillar, form, visual systems, kit assets). For an exercise: `fitness.py exercise <id> --goal technique|muscle|mistake|compare` gives the explanation plan. Say which pillar and goal you chose and why.
2. **Scaffold.** `fitness.py new <slug> --topic "..." --type <form>`; fill `brief.json` (1-3 directions).
3. **Research** (required unless the brief says it is a pure technique demo). Dossier with grades, `do_not_claim`; every source verified (Europe PMC); gate: `fitness.py dossier <slug>`. Never fabricate a citation, number or mechanism.
4. **Story and script.** Story-writer rulebook + form skill + `storytelling.md`. A script says what to SHOW, not only what to say. Sign-off `qa/story-review.json`.
5. **Storyboard and animatic.** `storyboard.json` shot by shot; `scripts/fitness-animatic.py <slug>` (real stills per scene, pacing lint). Fix pacing before audio.
6. **Audio.** `build-audio.py` (brand voice `am_michael`, speed 1.05 comes from the project's `research.json` acoustic guidance), `studio.py captions --timing words`, bed and SFX from `sinew_sound.py` with events taken from the phase map and the measured cues. Fix respellings in `captions.js`.
7. **Visuals.** Compose from the scene library (`fitness-animation`), anatomy per `fitness-anatomy`. Use 3D Tibi for lifts, loaded lower-body work and anything needing a free camera; 2D `K.sculpt` for static poses, running, brand cards. Never mix both in one frame. Keep something moving in every frame; frame 0 already carries the hook.
8. **Pre-render gate.** `studio.py validate`, `fitness.py check`, `rig3d-check` and `anatomy3d-check` (3D films), `hyperframes snapshot --at ...` contact sheets under `session-guard`. Look at every sheet.
9. **Render.** `studio.py build <slug>` (takes the host lock; one heavy job at a time).
10. **Review.** `scripts/fitness-qa.py <final.mp4> --expect-audio`, `scripts/fitness-gates.py <slug>`, `studio.py review`, `fitness.py review`; scientific, anatomical or biomechanical errors are critical. A human signs off G1 and G3.
11. **Fix, re-render, retro**, then `fitness-publish`. `qa/production-report.md`: what was used, timings, scores, open issues.

## Forms
short (20-60 s, portrait): Hook, Explanation, Payoff, one claim, one mechanism. mid (60-180 s): + Context, Demonstration, Conclusion; re-hook every 45-60 s. long (5-12 min, landscape): chapter cards, one mechanism per chapter, a "what we don't know" beat. Adapt, never trim: a short is built around the long film's single strongest insight with its own hook.

## Rules that never bend
- Claims: no fabricated citations or numbers, no activation percentages, no "isolates", no diagnosis or treatment; the general-education line on every film that suggests an action; a measurement is drawn as a measurement (electrode + graph), never as a muscle.
- Highlights are defensible: every muscle the 3D rig lights up is listed with that role in `assets/fitness/data/exercises.json` (`fitness.py check` audits it).
- Assets: original kit art or cleared sources only (`source-registry.md`). Brand: never copy existing characters or sequences (Yellow Dude, Kurzgesagt, 3Blue1Brown are studied for communication, not copied).
- Pipeline: one heavy job at a time; `--low-memory-mode` and `< /dev/null`; the runtime copy `src/_studio/` is never edited (change `src/studio/`, bump `Studio.version`, `studio.py upgrade --all`).
- A film is complete only after a rendered, reviewed, human-signed-off pass, not when rendering succeeds.

## Extending
New muscle or exercise: `fitness-anatomy` / `fitness-animation`. 2D art: `src/fitness/tibi/` generator (`HANDOVER.md`), `fitness.py sculpt`. New graphic: `graphics.js` + manifest entry + sheet. Always finish with `studio.py upgrade --all`, `python tests/test-fitness.py`, `python tests/test-rig3d.py`, `python tests/test-anatomy3d.py`, `python scripts/workspace-governance.py`. Architecture and decisions: `docs/fitness-studio.md`.
