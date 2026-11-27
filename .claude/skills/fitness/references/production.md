# Sinew production: tools, pipeline, rendering and limits

## Tools on the render host (inspected 2026-11-08)

| Tool | State | Role for fitness films |
|---|---|---|
| HyperFrames 0.8.226 + GSAP 3.12.5 (vendored) | installed | the only renderer: HTML/SVG compositions, deterministic seek |
| `src/studio/` runtime 1.4.0 | canonical | adds `studio-rig.js` and `kits/fitness/*` (synced into every project) |
| FFmpeg | installed | mux, loudness, frame extraction for review |
| Kokoro 0.9.4 via `src/pipeline/tts.py` | installed | narration (`am_michael` 1.05, slow scenes 0.94) |
| Whisper small.en (hyperframes transcribe) | installed | word-timed captions |
| Earshot (`.venv/bin/earshot`) | installed | mix and sync listening (`timeline`, `measure`) |
| Python Playwright | **absent** | `frame-review.py` cannot run; use `hyperframes snapshot` and the sheet renderer |
| Blender | 5.2.4 LTS on the Windows design host (2026-11-24); not yet on the M2 | plates only, through `scripts/visual-director.py`; see the 3D decision below |
| Revideo / Motion Canvas | CLI installed globally, wired into nothing | not used: the workspace standard is HyperFrames (a prior report rejected Revideo) |

## 3D decision (revised 2026-11-12)

The 2D rig cannot give smooth press, curl or raise motion (art swaps at joint thresholds pop; views are separate drawings) and cannot move the camera: `references/motion-3d.md` has the diagnosis and measurements.

- **Chosen: Three.js r158 in HyperFrames' headless Chrome.** Verified on this host through `hyperframes snapshot` and `hyperframes render` (software WebGL, real pixels, labels tracked from 3D anchors). It keeps determinism (pose is a pure function of film time, see motion-3d.md), the render lock, captions, QA gates and HTML overlays. Library record: `catalogue/data/libraries/threejs.json`.
- **Blender: adopted 2026-11-24 as an experimental plate engine for the whole studio** (`docs/visual-engines.md`, `visual-director` skill), not for Tibi. Tibi stays in Three.js: the reasons below still hold for the character (no HTML overlay path for tracked labels, and toon materials already give the Cobalt Sculpt look). Blender plates suit fitness films for environments, light and physics behind Tibi (a lit gym set, chalk dust, a falling plate stack), composited as timed `<video>` layers; anatomy meshes must still come from cleared sources only (`source-registry.md`). The armature route (export `T3.DEFAULT_POSE`-keyed tracks to a Blender rig) remains unbuilt and needs a decision before sculpted anatomy plates.

## Rig workflow (2D)

1. Pose authoring: add a named pose to `exercises.js` (`F.poses.side`/`front`) with anatomical angles. Use `flat` for feet, `anchor` for planted contacts (a sole or a grip), and `ik` for a second planted limb.
2. Preview: add the pose or exercise to `assets/fitness/sheets/poses.html` or `exercises.html` and run `python scripts/fitness.py sheets --only poses`.
3. Check: contacts planted, no limb through the floor, joints within limits, props following (followers).
4. Register: metadata in `assets/fitness/data/exercises.json`, `fitness.py library`, manifest entry, `fitness.py check`, `python tests/test-fitness.py`.
5. Ship the runtime: bump `Studio.version` and run `python scripts/studio.py upgrade --all`.

## Export pipeline (brand sources and previews)

- Master sources are code: the Cobalt Sculpt Tibi's Python generator `src/fitness/tibi/` (exported to `sculpt-data.js` by `fitness.py sculpt`; painter `sculpt.js`), `brand.js` (palette), `graphics.js` (logo, cards), `anatomy.js` (plates), `exercises.js` (poses).
- `assets/fitness/sheets/*.html` lay them out as boards. `python scripts/fitness.py sheets` renders each to `assets/fitness/previews/<name>.png` and, where a sheet sets `data-export-svg`, writes an editable SVG to `assets/fitness/brand/` (logo board, model sheet, thumbnail template). It runs headless Chrome from the HyperFrames install under the host render lock.
- Sheet pages load Google Fonts copies of Outfit, Inter and JetBrains Mono for previews only; films use the HyperFrames-bundled fonts.

## Rendering a film

```bash
python scripts/fitness.py new <slug> --topic "..." --type mid --formats landscape
# brief, research.json, research/dossier.json, story, narration
python3.12 scripts/build-audio.py <slug> --voice am_michael --speed 1.05
python3.12 scripts/studio.py captions <slug> --timing words [--grouping phrase]
# src/index.html from the template; audio/generate_bed_and_sfx.py via sinew_sound.py
python3.12 scripts/studio.py validate <slug> && python3.12 scripts/fitness.py check
python3 scripts/session-guard.py run --slug <slug> --cwd "$PWD/projects/<slug>/src" render -- hyperframes snapshot . --at ... --output <dir> < /dev/null
python3.12 scripts/studio.py build <slug>
python3.12 scripts/fitness.py review <slug> --init   # then score it after watching
```
Measured on the demo: a 97.5 s 1280x720 film renders in about 2.5 minutes (low-memory mode, screenshot capture), and the whole build with mux, QA gates and poster takes about 3 minutes.

## Known limitations

- 2D rig: views are separate drawings (a turn is a cross-fade); foreshortening by a per-joint factor (back and front squats, running from behind, views from above), so deep front-view squats and lunges are limited by the fixed paint order; muscle and bone shapes are schematic. Arm art variants blend across their thresholds since sculpt kit 2.2.0 (a short cap or flexed-arm fade remains on fast reps) and moves are continuous: still use the 3D kit when a curl, press or raise is the subject of the shot (`motion-3d.md`).
- 3D rig: see `motion-3d.md`, Known limits (runtime 1.14.0): shoulder crush at cross-body and overhead reach, stylised hands, a band-style female top, toon shading that does not match the 2D crescent art (owner decision pending), a rigid ponytail tail; no cloth simulation.
- Kinematics are conceptual (authored angles), not motion capture. Measured kinematics would need a cited dataset and a "measured" label.
- The 2D leg press was rebuilt in sculpt kit 2.2.0 (`K.exercise(t, 'leg-press')`: reclined seat, rails, a sled that follows the soles); the old composition-level drawing is superseded. Look at `assets/fitness/previews/exercises-barbell.png` before featuring it.
- Anatomy plates cover muscle tissue, energy (mitochondrion, ATP), heart, lungs, a satellite cell and, since 2026-11-23, a vascular tree, an alveolus with gas exchange and knee, hip and shoulder joint sections (`A.vascularTree`, `A.alveolus`, `A.joint`; preview `assets/fitness/previews/anatomy-inside.png`).
- No 3D anatomy library: every open 3D source examined is share-alike, per-model or non-commercial (`source-registry.md`).
- Tibi lip-sync is word-level flaps, not phoneme visemes.
- Calibration: the rubric thresholds, the body-lab template rules and the pillar keywords are first guesses from one film.
